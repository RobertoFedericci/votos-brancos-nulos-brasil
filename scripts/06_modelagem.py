#!/usr/bin/env python3
"""Modelagem multivariada da taxa de brancos + nulos.

Roda, nesta ordem:
  1. Diagnóstico de colinearidade (VIF) no conjunto completo de preditores
  2. Stepwise bidirecional por AIC — e um teste de estabilidade por bootstrap
     que mede quantas vezes cada variável sobrevive à reamostragem
  3. Mínimos quadrados ponderados no conjunto pré-especificado, com erros-padrão
     robustos (HC3)
  4. Elastic net com validação cruzada, como alternativa estável ao stepwise
  5. Gradient boosting com validação cruzada agrupada por estado, apenas como
     teste de não-linearidade
  6. I de Moran nos resíduos, para autocorrelação espacial

Desfecho: logito da taxa de brancos + nulos. A taxa é uma proporção limitada,
e o logito a leva para a reta real. A ponderação é n*p*(1-p), o inverso da
variância assintótica do logito: municípios pequenos são medidos com muito
mais ruído e não podem pesar igual.

Saída: site/dados/modelo.json e um relatório em texto no stdout.
"""
import json, os, sys, warnings
import numpy as np

warnings.filterwarnings("ignore")
np.random.seed(20260730)

AQUI = os.path.dirname(__file__)
PROC = os.path.join(AQUI, "..", "dados", "proc")
SITE = os.path.join(AQUI, "..", "site", "dados")
UFS = ["SP", "CE", "BA", "PE", "PA", "MA"]
NOMES_UF = {"SP": "São Paulo", "CE": "Ceará", "BA": "Bahia",
            "PE": "Pernambuco", "PA": "Pará", "MA": "Maranhão"}
CARGO, ANO = "Presidente", "2022"

# Conjunto completo, incluindo a composição de escolaridade. Só é usado no
# diagnóstico e na demonstração do stepwise.
TODAS = [
    ("alf", "Alfabetização (%)"),
    ("ea", "Eleitores com superior (%)"),
    ("eb", "Eleitores baixa escolaridade (%)"),
    ("em", "Eleitores escolaridade média (%)"),
    ("pib_log", "log PIB per capita"),
    ("sal", "Salário médio (SM)"),
    ("dens_log", "log Densidade"),
    ("i60", "Eleitores 60+ (%)"),
    ("jov", "Eleitores 16-24 (%)"),
    ("fem", "Eleitoras mulheres (%)"),
]
# Conjunto pré-especificado: descarta eb e em, que junto com ea somam 100 e
# tornam a matriz singular. Alfabetização vem do Censo, ea vem do TSE — medem
# coisas próximas mas não idênticas (r = 0,76, VIF tolerável).
PRE = ["alf", "ea", "pib_log", "sal", "dens_log", "i60", "jov", "fem"]

ROTULOS = dict(TODAS)


def carrega():
    cent = json.load(open(os.path.join(PROC, "centroides.json")))
    linhas = []
    for uf in UFS:
        d = json.load(open(os.path.join(SITE, f"{uf}.json")))
        for m in d["municipios"]:
            r = (m["d"].get(CARGO) or {}).get(ANO)
            if not r or not r[0]:
                continue
            votos, brancos, nulos, tec = r[0], r[1], r[2], r[3]
            p = (brancos + nulos + tec) / votos
            # O logito exige 0 < p < 1; nenhum município do recorte encosta
            # nos extremos, mas a guarda evita explodir em anos futuros.
            if not (1e-6 < p < 1 - 1e-6):
                continue
            campos = {"alf": m["alf"], "ea": m["ea"], "eb": m["eb"],
                      "em": m["em"], "sal": m["sal"], "i60": m["i60"],
                      "jov": m["jov"], "fem": m["fem"]}
            if any(v is None for v in campos.values()):
                continue
            if not m["pib"] or not m["dens"] or not m["el"]:
                continue
            if m["c"] not in cent:
                continue
            campos["pib_log"] = np.log(m["pib"])
            campos["dens_log"] = np.log(m["dens"])
            linhas.append({
                "uf": uf, "nome": m["n"], "cod": m["c"],
                "y": np.log(p / (1 - p)), "p": p,
                # Peso = inverso da variância assintótica do logito.
                "w": votos * p * (1 - p),
                "xy": cent[m["c"]], **campos,
            })
    return linhas


def matriz(linhas, vars_, com_ef_fixos=False):
    X = np.array([[l[v] for v in vars_] for l in linhas], float)
    y = np.array([l["y"] for l in linhas])
    w = np.array([l["w"] for l in linhas])
    nomes = list(vars_)
    if com_ef_fixos:
        # Efeitos fixos de estado: SP é a categoria de referência.
        for uf in UFS[1:]:
            X = np.c_[X, [1.0 if l["uf"] == uf else 0.0 for l in linhas]]
            nomes.append(f"UF={uf}")
    return X, y, w, nomes


def padroniza(X):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    return (X - mu) / sd, mu, sd


# ----------------------------------------------------------------- diagnóstico
def vif(X, nomes):
    Z, _, _ = padroniza(X)
    out = []
    for i in range(Z.shape[1]):
        o = [j for j in range(Z.shape[1]) if j != i]
        A = np.c_[Z[:, o], np.ones(len(Z))]
        b, *_ = np.linalg.lstsq(A, Z[:, i], rcond=None)
        res = Z[:, i] - A @ b
        r2 = 1 - res @ res / ((Z[:, i] - Z[:, i].mean()) ** 2).sum()
        out.append((nomes[i], 1 / max(1 - r2, 1e-15)))
    return out


# -------------------------------------------------------------------- stepwise
def wls(X, y, w):
    """MQP com intercepto. Devolve coeficientes, SSR e log-verossimilhança."""
    A = np.c_[np.ones(len(X)), X]
    sw = np.sqrt(w)
    b, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    res = y - A @ b
    ssr = float(w @ res ** 2)
    n = len(y)
    # Log-verossimilhança gaussiana ponderada, a menos de constantes.
    llf = -0.5 * n * (np.log(2 * np.pi * ssr / n) + 1) + 0.5 * np.log(w).sum()
    return b, ssr, llf


def aic(X, y, w):
    _, _, llf = wls(X, y, w)
    return 2 * (X.shape[1] + 2) - 2 * llf


def stepwise(X, y, w, nomes, verboso=False):
    """Seleção bidirecional por AIC, partindo do modelo vazio."""
    dentro = []
    fora = list(range(X.shape[1]))
    atual = aic(np.empty((len(y), 0)), y, w)
    passos = []
    while True:
        melhor, acao = None, None
        for j in fora:
            a = aic(X[:, dentro + [j]], y, w)
            if melhor is None or a < melhor:
                melhor, acao = a, ("entra", j)
        for j in list(dentro):
            resto = [k for k in dentro if k != j]
            a = aic(X[:, resto], y, w) if resto else aic(np.empty((len(y), 0)), y, w)
            if melhor is None or a < melhor:
                melhor, acao = a, ("sai", j)
        if melhor is None or melhor >= atual - 1e-8:
            break
        tipo, j = acao
        if tipo == "entra":
            dentro.append(j)
            fora.remove(j)
        else:
            dentro.remove(j)
            fora.append(j)
        passos.append((tipo, nomes[j], melhor))
        atual = melhor
        if verboso:
            print(f"    {tipo:5} {nomes[j]:32} AIC={melhor:12.2f}")
    return sorted(dentro), passos


def estabilidade(X, y, w, nomes, B=200):
    """Reamostra municípios com reposição e reexecuta o stepwise.

    A frequência com que cada variável é escolhida diz se a seleção é uma
    propriedade dos dados ou um acidente da amostra.
    """
    n = len(y)
    cont = np.zeros(X.shape[1])
    tamanhos, conjuntos = [], {}
    for _ in range(B):
        idx = np.random.randint(0, n, n)
        sel, _ = stepwise(X[idx], y[idx], w[idx], nomes)
        cont[sel] += 1
        tamanhos.append(len(sel))
        chave = tuple(sel)
        conjuntos[chave] = conjuntos.get(chave, 0) + 1
    return cont / B, tamanhos, conjuntos


# ------------------------------------------------------------- I de Moran
def moran(res, coords, w_reg, k=8, permutacoes=999):
    """I de Moran com pesos de k vizinhos mais próximos, normalizados por linha.

    Resíduos ponderados: a estatística é calculada sobre o resíduo padronizado
    pelo peso do município, senão o ruído dos municípios pequenos domina.
    """
    C = np.asarray(coords, float)
    n = len(C)
    d = ((C[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(d, np.inf)
    viz = np.argsort(d, axis=1)[:, :k]

    z = res * np.sqrt(w_reg)
    z = (z - z.mean()) / (z.std() or 1)
    lag = z[viz].mean(1)
    I = float(n / n * (z @ lag) / (z @ z)) * n / n
    I = float((z * lag).sum() / (z * z).sum())

    nulos = np.empty(permutacoes)
    for i in range(permutacoes):
        zp = np.random.permutation(z)
        nulos[i] = (zp * zp[viz].mean(1)).sum() / (zp * zp).sum()
    p = (1 + (np.abs(nulos) >= abs(I)).sum()) / (permutacoes + 1)
    return I, float(nulos.mean()), float(p)


# ------------------------------------------------------------------ principal
def r2_ponderado(y, pred, w):
    ybar = np.average(y, weights=w)
    return 1 - (w @ (y - pred) ** 2) / (w @ (y - ybar) ** 2)


def ajusta_e_reporta(linhas, rotulo, com_ef_fixos, saida, rodar_pesados=True):
    import statsmodels.api as sm
    from sklearn.linear_model import ElasticNetCV
    from sklearn.model_selection import GroupKFold, KFold

    print(f"\n{'='*74}\n{rotulo}   (n = {len(linhas)})\n{'='*74}")
    bloco = {"rotulo": rotulo, "n": len(linhas)}

    # --- 1. colinearidade no conjunto completo -----------------------------
    Xt, y, w, nt = matriz(linhas, [v for v, _ in TODAS])
    print("\n[1] Colinearidade — conjunto completo, com a composição de escolaridade")
    bloco["vif_todas"] = []
    for nome, v in vif(Xt, nt):
        flag = "  <-- inaceitável" if v > 10 else ""
        print(f"    VIF {ROTULOS.get(nome,nome):32} {v:14.1f}{flag}")
        bloco["vif_todas"].append({"var": ROTULOS.get(nome, nome), "vif": round(v, 2)})

    # --- 2. stepwise -------------------------------------------------------
    print("\n[2] Stepwise bidirecional por AIC — conjunto completo")
    sel, passos = stepwise(Xt, y, w, nt, verboso=True)
    escolhidas = [ROTULOS.get(nt[i], nt[i]) for i in sel]
    print(f"    selecionadas: {escolhidas}")
    bloco["stepwise_todas"] = escolhidas

    print("\n    Teste de estabilidade — 200 reamostragens bootstrap")
    freq, tam, conjuntos = estabilidade(Xt, y, w, nt, B=200)
    bloco["estabilidade"] = []
    for i in np.argsort(-freq):
        print(f"      {ROTULOS.get(nt[i],nt[i]):32} escolhida em {100*freq[i]:5.1f}% das amostras")
        bloco["estabilidade"].append(
            {"var": ROTULOS.get(nt[i], nt[i]), "freq": round(100 * float(freq[i]), 1)})
    mais_comum = max(conjuntos.values()) / sum(conjuntos.values())
    print(f"      conjuntos distintos escolhidos: {len(conjuntos)} em 200 amostras")
    print(f"      o conjunto mais frequente aparece em {100*mais_comum:.1f}% delas")
    bloco["estab_conjuntos"] = len(conjuntos)
    bloco["estab_moda"] = round(100 * mais_comum, 1)

    # --- 3. MQP no conjunto pré-especificado -------------------------------
    X, y, w, nomes = matriz(linhas, PRE, com_ef_fixos)
    Z, mu, sd = padroniza(X)
    print("\n[3] Mínimos quadrados ponderados — conjunto pré-especificado")
    print("    (coeficientes padronizados: efeito de 1 desvio-padrão do preditor)")
    mod = sm.WLS(y, sm.add_constant(Z), weights=w).fit(cov_type="HC3")
    bloco["ols"] = {"r2": round(float(mod.rsquared), 4),
                    "r2_aj": round(float(mod.rsquared_adj), 4), "coef": []}
    print(f"    R² = {mod.rsquared:.4f}   R² ajustado = {mod.rsquared_adj:.4f}")

    # Quanto do R² vem dos preditores municipais e quanto vem apenas de saber
    # em que estado o município fica. Sem esta separação, o R² agrupado é
    # facilmente lido como poder explicativo que os preditores não têm.
    if com_ef_fixos:
        k = len(PRE)
        r2_so_ef = float(sm.WLS(y, sm.add_constant(Z[:, k:]), weights=w).fit().rsquared)
        r2_so_pred = float(sm.WLS(y, sm.add_constant(Z[:, :k]), weights=w).fit().rsquared)
        print(f"      só efeitos fixos de estado : R² = {r2_so_ef:.4f}")
        print(f"      só preditores municipais   : R² = {r2_so_pred:.4f}")
        print(f"      ganho dos preditores sobre os efeitos fixos: "
              f"{mod.rsquared - r2_so_ef:+.4f}")
        bloco["ols"]["r2_so_ef"] = round(r2_so_ef, 4)
        bloco["ols"]["r2_so_pred"] = round(r2_so_pred, 4)

    # Concentração do peso: mostra o quanto uma única capital pesa.
    o = np.argsort(-w)
    bloco["peso_top1"] = round(100 * float(w[o[0]] / w.sum()), 1)
    print(f"      peso do maior município ({linhas[o[0]]['nome']}): "
          f"{bloco['peso_top1']:.1f}% do total")
    vifs = dict(vif(X, nomes))
    for i, nome in enumerate(nomes, start=1):
        b, se, p = mod.params[i], mod.bse[i], mod.pvalues[i]
        est = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""
        rot = ROTULOS.get(nome, nome)
        print(f"    {rot:32} {b:+8.4f}  (ep {se:.4f})  p={p:7.4f} {est:3}"
              f"  VIF={vifs.get(nome,float('nan')):5.1f}")
        bloco["ols"]["coef"].append({
            "var": rot, "beta": round(float(b), 4), "ep": round(float(se), 4),
            "p": float(p), "vif": round(float(vifs.get(nome, np.nan)), 2)})

    # --- 4. elastic net ----------------------------------------------------
    print("\n[4] Elastic net com validação cruzada — alternativa estável ao stepwise")
    en = ElasticNetCV(l1_ratio=[.1, .5, .7, .9, .95, .99, 1],
                      cv=KFold(10, shuffle=True, random_state=1),
                      max_iter=50000, random_state=1)
    sw = w / w.mean()
    en.fit(Z, y, sample_weight=sw)
    print(f"    alfa = {en.alpha_:.5f}   l1_ratio = {en.l1_ratio_}")
    bloco["enet"] = {"alpha": round(float(en.alpha_), 5),
                     "l1": float(en.l1_ratio_), "coef": []}
    ordem = np.argsort(-np.abs(en.coef_))
    for i in ordem:
        marca = "" if abs(en.coef_[i]) > 1e-8 else "   (zerado)"
        print(f"    {ROTULOS.get(nomes[i],nomes[i]):32} {en.coef_[i]:+8.4f}{marca}")
        bloco["enet"]["coef"].append({"var": ROTULOS.get(nomes[i], nomes[i]),
                                      "beta": round(float(en.coef_[i]), 4)})

    if rodar_pesados:
        # --- 5. gradient boosting -----------------------------------------
        import xgboost as xgb
        print("\n[5] Gradient boosting — teste de não-linearidade")

        def compara(Zc, div, desc):
            """Compara boosting e MQP na mesma partição, fora da amostra.

            O R² é reportado nas duas versões de propósito. A ponderada é
            coerente com a estimação, mas é dominada pelas capitais: em São
            Paulo o município da capital detém 29% do peso total, e o bloco
            que o contém sozinho define o resultado. A não ponderada trata
            todo município igual e mostra o desempenho típico.
            """
            gbw, olsw, gbu, olsu = [], [], [], []
            for tr, te in div:
                g = xgb.XGBRegressor(n_estimators=400, max_depth=3,
                                     learning_rate=.05, subsample=.8,
                                     colsample_bytree=.8, reg_lambda=2,
                                     random_state=1, verbosity=0)
                g.fit(Zc[tr], y[tr], sample_weight=w[tr])
                pg = g.predict(Zc[te])
                b, _, _ = wls(Zc[tr], y[tr], w[tr])
                po = np.c_[np.ones(len(te)), Zc[te]] @ b
                gbw.append(r2_ponderado(y[te], pg, w[te]))
                olsw.append(r2_ponderado(y[te], po, w[te]))
                gbu.append(r2_ponderado(y[te], pg, np.ones(len(te))))
                olsu.append(r2_ponderado(y[te], po, np.ones(len(te))))
            r = {k: round(float(np.mean(v)), 4) for k, v in
                 [("r2_gb", gbw), ("r2_ols", olsw),
                  ("r2_gb_np", gbu), ("r2_ols_np", olsu)]}
            print(f"    {desc}")
            print(f"      {'':22}{'ponderado':>12}{'não pond.':>12}")
            print(f"      {'boosting':22}{r['r2_gb']:+12.4f}{r['r2_gb_np']:+12.4f}")
            print(f"      {'MQP':22}{r['r2_ols']:+12.4f}{r['r2_ols_np']:+12.4f}")
            print(f"      {'ganho do boosting':22}"
                  f"{r['r2_gb']-r['r2_ols']:+12.4f}{r['r2_gb_np']-r['r2_ols_np']:+12.4f}")
            r["desc"] = desc
            return r

        # Não-linearidade: partição aleatória. Deixar um estado de fora não
        # serve aqui — o efeito fixo do estado retirado não é identificável no
        # treino, e o modelo linear seria punido por algo que não é forma
        # funcional.
        div = list(KFold(10, shuffle=True, random_state=1).split(Z, y))
        bloco["gb"] = compara(Z, div, "partição aleatória em 10 blocos")

        # Transferência entre estados: aí sim um estado inteiro é retirado, mas
        # sem efeitos fixos, para que a pergunta seja legítima — o que se
        # aprende em cinco estados prevê o sexto?
        grupos = np.array([l["uf"] for l in linhas])
        if com_ef_fixos and len(set(grupos)) > 1:
            Zs = Z[:, :len(PRE)]
            divg = list(GroupKFold(n_splits=len(set(grupos))).split(Zs, y, grupos))
            bloco["gb_transf"] = compara(
                Zs, divg, "um estado inteiro de fora, sem efeitos fixos")

        # --- 6. autocorrelação espacial ------------------------------------
        print("\n[6] I de Moran nos resíduos — autocorrelação espacial")
        res = y - mod.predict(sm.add_constant(Z))
        I, esp, p = moran(res, [l["xy"] for l in linhas], w)
        print(f"    I = {I:+.4f}   (esperado sob aleatoriedade ≈ {esp:+.4f})   p = {p:.4f}")
        if p < .05 and I > 0:
            print("    Resíduos agrupados no espaço: municípios vizinhos erram")
            print("    para o mesmo lado. Os erros-padrão de [3] são otimistas.")
        bloco["moran"] = {"I": round(I, 4), "p": round(p, 4)}

    saida.append(bloco)
    return bloco


def main():
    linhas = carrega()
    print(f"Municípios carregados: {len(linhas)}")
    print(f"Desfecho: logito da taxa de brancos + nulos — {CARGO}, {ANO}")

    saida = []
    ajusta_e_reporta(linhas, "MODELO AGRUPADO — seis estados, com efeitos fixos de estado",
                     True, saida)
    for uf in UFS:
        sub = [l for l in linhas if l["uf"] == uf]
        ajusta_e_reporta(sub, f"{NOMES_UF[uf]} ({uf})", False, saida,
                         rodar_pesados=len(sub) >= 180)

    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "modelo.json"), "w") as f:
        json.dump({"cargo": CARGO, "ano": ANO, "blocos": saida}, f,
                  ensure_ascii=False, separators=(",", ":"))
    print(f"\nGravado: site/dados/modelo.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Erros-padrão que sobrevivem à dependência espacial.

O I de Moran mostrou que os resíduos se agrupam no mapa: municípios vizinhos
erram para o mesmo lado. Isso não enviesa os coeficientes, mas invalida os
erros-padrão, que supõem observações independentes. Aqui há três respostas,
da mais barata à mais estrutural:

  1. Erros-padrão AGRUPADOS por microrregião e por região imediata. Admitem
     correlação arbitrária dentro de cada agrupamento.
  2. Erros-padrão de CONLEY (HAC espacial). Não exigem escolher fronteiras:
     a correlação decai com a distância, até um raio de corte.
  3. Absorver a região com EFEITOS FIXOS de região imediata, em vez de só
     corrigir a variância — e verificar, pelo I de Moran, se o agrupamento
     dos resíduos de fato desaparece.

O teste de heterogeneidade entre estados é refeito com variância agrupada,
para que a conclusão não dependa da suposição que sabemos ser falsa.

Saída: site/dados/espacial.json e relatório em texto.
"""
import json, os, importlib.util
import numpy as np

AQUI = os.path.dirname(__file__)
PROC = os.path.join(AQUI, "..", "dados", "proc")
SITE = os.path.join(AQUI, "..", "site", "dados")

spec = importlib.util.spec_from_file_location(
    "base", os.path.join(AQUI, "06_modelagem.py"))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
UFS, PRE, ROTULOS, NOMES_UF = base.UFS, base.PRE, base.ROTULOS, base.NOMES_UF

RAIO_TERRA_KM = 6371.0


def wls_beta(X, y, w):
    """Coeficientes de MQP e o 'pão' (X'WX)^-1 usado em toda variância."""
    XtW = X.T * w
    pao = np.linalg.inv(XtW @ X)
    b = pao @ (XtW @ y)
    return b, pao, y - X @ b


def var_hc0(X, w, u, pao):
    """Robusta sem correção de alavancagem. É a base de comparação honesta:
    o estimador agrupado e o de Conley também não corrigem alavancagem, então
    comparar qualquer um deles com HC3 confunde dois efeitos distintos."""
    s = (w * u)[:, None] * X
    return pao @ (s.T @ s) @ pao


def var_hc3(X, w, u, pao):
    h = np.einsum("ij,jk,ik->i", X, pao, X) * w
    s = (w * u / np.clip(1 - h, 1e-8, None))[:, None] * X
    return pao @ (s.T @ s) @ pao


def var_agrupada(X, w, u, pao, grupos):
    """Variância agrupada: correlação livre dentro de cada grupo."""
    s = (w * u)[:, None] * X
    carne = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(grupos):
        sg = s[grupos == g].sum(0)
        carne += np.outer(sg, sg)
    G, n, k = len(np.unique(grupos)), X.shape[0], X.shape[1]
    c = (G / (G - 1)) * ((n - 1) / (n - k))
    return c * (pao @ carne @ pao)


def var_conley(X, w, u, pao, dist, corte_km):
    """HAC espacial de Conley, com núcleo de Bartlett no raio de corte."""
    s = (w * u)[:, None] * X
    K = np.clip(1 - dist / corte_km, 0, None)
    carne = s.T @ K @ s
    return pao @ carne @ pao


def distancias_km(coords):
    """Haversine entre todos os pares. Graus decimais não servem: um grau de
    longitude vale coisas diferentes no Pará e em São Paulo."""
    lon = np.radians(coords[:, 0])
    lat = np.radians(coords[:, 1])
    dlon = lon[:, None] - lon[None, :]
    dlat = lat[:, None] - lat[None, :]
    a = (np.sin(dlat / 2) ** 2
         + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlon / 2) ** 2)
    return 2 * RAIO_TERRA_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def moran_knn(res, w, coords, k=8, permutacoes=999):
    d = distancias_km(coords).copy()
    np.fill_diagonal(d, np.inf)
    viz = np.argsort(d, axis=1)[:, :k]
    z = res * np.sqrt(w)
    z = (z - z.mean()) / (z.std() or 1)
    I = float((z * z[viz].mean(1)).sum() / (z * z).sum())
    nulos = np.array([((zp := np.random.permutation(z)) * zp[viz].mean(1)).sum()
                      / (zp * zp).sum() for _ in range(permutacoes)])
    p = (1 + (np.abs(nulos) >= abs(I)).sum()) / (permutacoes + 1)
    return I, float(p)


def main():
    np.random.seed(20260730)
    linhas = base.carrega()
    regioes = json.load(open(os.path.join(PROC, "regioes.json")))
    linhas = [l for l in linhas if l["cod"] in regioes]
    n = len(linhas)

    X0 = np.array([[l[v] for v in PRE] for l in linhas], float)
    y = np.array([l["y"] for l in linhas])
    w = np.array([l["w"] for l in linhas])
    Z = (X0 - X0.mean(0)) / X0.std(0)
    uf = np.array([l["uf"] for l in linhas])
    coords = np.array([l["xy"] for l in linhas], float)
    micro = np.array([regioes[l["cod"]]["micro"] for l in linhas])
    imed = np.array([regioes[l["cod"]]["imediata"] for l in linhas])

    D_uf = np.column_stack([(uf == u).astype(float) for u in UFS[1:]])
    X = np.c_[np.ones(n), Z, D_uf]
    nomes = ["intercepto"] + [ROTULOS[v] for v in PRE] + [f"UF={u}" for u in UFS[1:]]

    b, pao, u = wls_beta(X, y, w)
    dist = distancias_km(coords)

    print(f"Municípios: {n}   microrregiões: {len(set(micro))}   "
          f"regiões imediatas: {len(set(imed))}\n")

    variantes = {
        "HC0 (independência)": var_hc0(X, w, u, pao),
        "HC3 (independência)": var_hc3(X, w, u, pao),
        "Agrupado por microrregião": var_agrupada(X, w, u, pao, micro),
        "Agrupado por região imediata": var_agrupada(X, w, u, pao, imed),
        "Conley 100 km": var_conley(X, w, u, pao, dist, 100),
        "Conley 200 km": var_conley(X, w, u, pao, dist, 200),
    }

    print("=" * 88)
    print("ERROS-PADRÃO SOB CADA SUPOSIÇÃO  (modelo agrupado, efeitos fixos de estado)")
    print("=" * 88)
    cab = f"{'variável':<28}{'coef':>9}" + "".join(f"{k.split('(')[0][:13]:>14}"
                                                   for k in variantes)
    print(cab)
    saida = {"n": n, "n_micro": len(set(micro)), "n_imediata": len(set(imed)),
             "coef": []}
    from scipy import stats
    for i, nome in enumerate(nomes):
        if nome == "intercepto":
            continue
        linha = f"{nome:<28}{b[i]:>9.4f}"
        reg = {"var": nome, "beta": round(float(b[i]), 4), "ep": {}, "p": {}}
        for k, V in variantes.items():
            se = float(np.sqrt(V[i, i]))
            linha += f"{se:>14.4f}"
            reg["ep"][k] = round(se, 4)
            reg["p"][k] = float(2 * stats.norm.sf(abs(b[i] / se)))
        print(linha)
        saida["coef"].append(reg)

    print("\n" + "=" * 88)
    print("O QUE MUDA DE CONCLUSÃO")
    print("=" * 88)
    ref, alvo = "HC0 (independência)", "Agrupado por microrregião"
    perdeu = []
    for reg in saida["coef"]:
        infl = reg["ep"][alvo] / reg["ep"][ref]
        if reg["p"][ref] < .05 and reg["p"][alvo] >= .05:
            perdeu.append(reg["var"])
        print(f"  {reg['var']:<28} erro-padrão {infl:5.2f}x   "
              f"p: {reg['p'][ref]:.4f} -> {reg['p'][alvo]:.4f}"
              f"{'   PERDE significância' if reg['var'] in perdeu else ''}")
    saida["perdem_significancia"] = perdeu

    # --- absorver a região com efeitos fixos ---
    print("\n" + "=" * 88)
    print("ABSORVER A REGIÃO, EM VEZ DE SÓ CORRIGIR A VARIÂNCIA")
    print("=" * 88)
    I0, p0 = moran_knn(u, w, coords)
    print(f"  Efeitos fixos de estado      : I de Moran = {I0:+.4f}  (p = {p0:.4f})")

    cods = sorted(set(imed))
    D_im = np.column_stack([(imed == c).astype(float) for c in cods[1:]])
    X_im = np.c_[np.ones(n), Z, D_im]
    b_im, pao_im, u_im = wls_beta(X_im, y, w)
    I1, p1 = moran_knn(u_im, w, coords)
    print(f"  Efeitos fixos de região      : I de Moran = {I1:+.4f}  (p = {p1:.4f})")
    print(f"  redução do agrupamento espacial: {100*(1-I1/I0):.0f}%")
    r2_im = 1 - (w @ u_im ** 2) / (w @ (y - np.average(y, weights=w)) ** 2)
    r2_uf = 1 - (w @ u ** 2) / (w @ (y - np.average(y, weights=w)) ** 2)
    print(f"  R² com efeitos de estado {r2_uf:.4f}  ->  com efeitos de região {r2_im:.4f}")
    saida["moran"] = {"uf": round(I0, 4), "uf_p": round(p0, 4),
                      "regiao": round(I1, 4), "regiao_p": round(p1, 4),
                      "r2_uf": round(float(r2_uf), 4),
                      "r2_regiao": round(float(r2_im), 4),
                      "n_regioes": len(cods)}

    # --- heterogeneidade, agora com variância agrupada ---
    print("\n" + "=" * 88)
    print("HETEROGENEIDADE ENTRE ESTADOS, COM VARIÂNCIA AGRUPADA")
    print("=" * 88)
    inter = np.column_stack([Z[:, [i]] * D_uf[:, [j]]
                             for i in range(len(PRE)) for j in range(D_uf.shape[1])])
    Xc = np.c_[X, inter]
    bc, paoc, uc = wls_beta(Xc, y, w)
    Vc = var_agrupada(Xc, w, uc, paoc, micro)
    q = inter.shape[1]
    idx = np.arange(Xc.shape[1] - q, Xc.shape[1])
    Vq = Vc[np.ix_(idx, idx)]
    bq = bc[idx]
    Wald = float(bq @ np.linalg.solve(Vq, bq))
    G = len(set(micro))
    F_ag = Wald / q
    p_ag = float(stats.f.sf(F_ag, q, G - 1))
    print(f"  Wald agrupado = {Wald:.1f}   F({q}, {G-1}) = {F_ag:.2f}   p = {p_ag:.3e}")
    print(f"  (o teste F original, supondo independência, dava F = 8,91)")
    print(f"  conclusão: as inclinações {'CONTINUAM' if p_ag<.05 else 'NÃO'} "
          f"diferindo entre estados")
    saida["heterogeneidade_agrupada"] = {
        "wald": round(Wald, 1), "F": round(F_ag, 2), "gl1": q, "gl2": G - 1,
        "p": p_ag, "significativo": bool(p_ag < .05)}

    with open(os.path.join(SITE, "espacial.json"), "w") as f:
        json.dump(saida, f, ensure_ascii=False, separators=(",", ":"))
    print("\nGravado: site/dados/espacial.json")


if __name__ == "__main__":
    main()

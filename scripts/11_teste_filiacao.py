#!/usr/bin/env python3
"""A filiação partidária explica o resíduo regional?

A hipótese sob teste: onde a organização política local é densa, o eleitor
chega à urna acompanhado de uma estrutura que dá sentido ao voto, e a taxa de
branco e nulo cai. Se for verdade, a densidade de filiação deve (a) ter
coeficiente negativo ao entrar no modelo e (b) reduzir o agrupamento espacial
dos resíduos, que é a assinatura do fator regional não captado.

Três indicadores entram: densidade de filiação por mil eleitores, número de
partidos com filiados no município, e concentração da filiação (Herfindahl).

Saída: site/dados/filiacao.json e relatório em texto.
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

espec = importlib.util.spec_from_file_location(
    "esp", os.path.join(AQUI, "09_espacial.py"))
esp = importlib.util.module_from_spec(espec)
espec.loader.exec_module(esp)

NOVOS = [("fil_log", "log Filiados por mil eleitores"),
         ("n_part", "Partidos com filiados"),
         ("hhi", "Concentração da filiação (HHI)")]


def carrega():
    """Junta o painel do modelo com a filiação, pelo código TSE do município."""
    linhas = base.carrega()
    fil = json.load(open(os.path.join(PROC, "filiacao.json")))
    regioes = json.load(open(os.path.join(PROC, "regioes.json")))
    # A votação é indexada por código IBGE; a filiação, por código TSE.
    mapa_tse = {}
    import csv
    with open(os.path.join(AQUI, "..", "dados", "raw",
                           "municipios_tse_ibge.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mapa_tse[r["codigo_ibge"]] = r["codigo_tse"].lstrip("0")

    saida, sem = [], 0
    for l in linhas:
        cd_tse = mapa_tse.get(l["cod"])
        f = fil["municipios"].get(cd_tse)
        if not f or l["cod"] not in regioes:
            sem += 1
            continue
        # Eleitorado reconstruído do peso: w = n*p*(1-p).
        eleitores = l["w"] / max(l["p"] * (1 - l["p"]), 1e-9)
        por_mil = 1000 * f["filiados"] / max(eleitores, 1)
        l = dict(l)
        l["fil_log"] = float(np.log(max(por_mil, 0.5)))
        l["por_mil"] = por_mil
        l["n_part"] = float(f["n_partidos"])
        l["hhi"] = float(f["hhi"])
        l["imed"] = regioes[l["cod"]]["imediata"]
        l["micro"] = regioes[l["cod"]]["micro"]
        saida.append(l)
    if sem:
        print(f"  {sem} municípios sem filiação pareada (excluídos)")
    return saida


def ajusta(linhas, vars_, com_uf=True):
    X = np.array([[l[v] for v in vars_] for l in linhas], float)
    y = np.array([l["y"] for l in linhas])
    w = np.array([l["w"] for l in linhas])
    Z = (X - X.mean(0)) / X.std(0)
    if com_uf:
        uf = np.array([l["uf"] for l in linhas])
        Z = np.c_[Z, np.column_stack([(uf == u).astype(float) for u in UFS[1:]])]
    A = np.c_[np.ones(len(Z)), Z]
    b, pao, u = esp.wls_beta(A, y, w)
    ybar = np.average(y, weights=w)
    r2 = 1 - (w @ u ** 2) / (w @ (y - ybar) ** 2)
    return b, pao, u, float(r2), A, y, w


def main():
    np.random.seed(20260730)
    linhas = carrega()
    n = len(linhas)
    coords = np.array([l["xy"] for l in linhas], float)
    micro = np.array([l["micro"] for l in linhas])
    print(f"Municípios pareados: {n}\n")

    dens = np.array([l["por_mil"] for l in linhas])
    print("Densidade de filiação (filiados por mil eleitores)")
    for uf in UFS:
        d = dens[np.array([l["uf"] for l in linhas]) == uf]
        print(f"  {uf}: mediana {np.median(d):6.1f}   "
              f"p10 {np.percentile(d,10):6.1f}   p90 {np.percentile(d,90):6.1f}")
    print(f"  Todos: mediana {np.median(dens):.1f}\n")

    print("=" * 76)
    print("A FILIAÇÃO ACRESCENTA ALGO AO MODELO?")
    print("=" * 76)
    b0, pao0, u0, r2_0, *_ = ajusta(linhas, PRE)
    vars1 = PRE + [v for v, _ in NOVOS]
    b1, pao1, u1, r2_1, A1, y1, w1 = ajusta(linhas, vars1)
    print(f"  R² sem filiação : {r2_0:.4f}")
    print(f"  R² com filiação : {r2_1:.4f}   ganho {r2_1-r2_0:+.4f}")

    V = esp.var_agrupada(A1, w1, u1, pao1, micro)
    from scipy import stats
    print("\n  Coeficientes padronizados, erro-padrão agrupado por microrregião:")
    nomes1 = ["intercepto"] + [ROTULOS[v] for v in PRE] + \
             [r for _, r in NOVOS] + [f"UF={u}" for u in UFS[1:]]
    resultado = []
    for i, nm in enumerate(nomes1):
        if nm == "intercepto":
            continue
        se = float(np.sqrt(V[i, i]))
        p = float(2 * stats.norm.sf(abs(b1[i] / se)))
        est = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""
        marca = "  <-- filiação" if nm in [r for _, r in NOVOS] else ""
        print(f"    {nm:32} {b1[i]:+8.4f} (ep {se:.4f}) p={p:7.4f} {est:3}{marca}")
        resultado.append({"var": nm, "beta": round(float(b1[i]), 4),
                          "ep": round(se, 4), "p": p,
                          "filiacao": nm in [r for _, r in NOVOS]})

    print("\n" + "=" * 76)
    print("A FILIAÇÃO EXPLICA O AGRUPAMENTO ESPACIAL?")
    print("=" * 76)
    I0, p0 = esp.moran_knn(u0, w1, coords)
    I1, p1 = esp.moran_knn(u1, w1, coords)
    print(f"  I de Moran sem filiação : {I0:+.4f} (p={p0:.4f})")
    print(f"  I de Moran com filiação : {I1:+.4f} (p={p1:.4f})")
    print(f"  redução: {100*(1-I1/I0):.1f}%")
    print("  (para comparação, efeitos fixos de região imediata reduzem 75%)")

    print("\n" + "=" * 76)
    print("CORRELAÇÃO SIMPLES COM O RESÍDUO REGIONAL")
    print("=" * 76)
    print("  Resíduo do modelo socioeconômico contra cada indicador de filiação,")
    print("  agregados por região imediata (é nessa escala que o fenômeno vive).")
    imed = np.array([l["imed"] for l in linhas])
    agg_r, agg_f, agg_np_, agg_h = [], [], [], []
    for g in np.unique(imed):
        m = imed == g
        if m.sum() < 4:
            continue
        ww = w1[m]
        agg_r.append(np.average(u0[m], weights=ww))
        agg_f.append(np.average([linhas[i]["fil_log"] for i in np.where(m)[0]], weights=ww))
        agg_np_.append(np.average([linhas[i]["n_part"] for i in np.where(m)[0]], weights=ww))
        agg_h.append(np.average([linhas[i]["hhi"] for i in np.where(m)[0]], weights=ww))
    for rot, v in [("log filiados/mil", agg_f), ("nº de partidos", agg_np_),
                   ("concentração (HHI)", agg_h)]:
        r = np.corrcoef(agg_r, v)[0, 1]
        print(f"    {rot:22} r = {r:+.3f}   ({len(agg_r)} regiões)")

    saida = {"n": n, "competencia": json.load(
                 open(os.path.join(PROC, "filiacao.json")))["competencia"],
             "r2_sem": round(r2_0, 4), "r2_com": round(r2_1, 4),
             "coef": resultado,
             "moran_sem": round(I0, 4), "moran_com": round(I1, 4),
             "mediana_por_mil": round(float(np.median(dens)), 1)}
    with open(os.path.join(SITE, "filiacao.json"), "w") as f:
        json.dump(saida, f, ensure_ascii=False, separators=(",", ":"))
    print("\nGravado: site/dados/filiacao.json")


if __name__ == "__main__":
    main()

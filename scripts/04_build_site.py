#!/usr/bin/env python3
"""Monta os arquivos de dados consumidos pela página.

Une as três bases já processadas (votação TSE, perfil do eleitorado TSE e
indicadores municipais IBGE) e gera:

  site/dados/<UF>.json      um arquivo por estado, carregado sob demanda
  site/dados/resumo.json    agregados estaduais + comparação entre os seis
  site/dados/mapa_uf.json   contornos das 27 UFs já projetados em SVG

Chaves curtas nos municípios são deliberadas: reduzem o JSON o suficiente
para o GitHub Pages servir cada estado numa única requisição leve.
"""
import json, os
from collections import defaultdict

AQUI = os.path.dirname(__file__)
PROC = os.path.join(AQUI, "..", "dados", "proc")
RAW = os.path.join(AQUI, "..", "dados", "raw")
SITE = os.path.join(AQUI, "..", "site", "dados")
MALHA = os.path.join(RAW, "malha_uf_br.geojson")

UFS = {"SP": "São Paulo", "CE": "Ceará", "BA": "Bahia",
       "PE": "Pernambuco", "PA": "Pará", "MA": "Maranhão"}
COD_UF = {"SP": "35", "CE": "23", "BA": "29", "PE": "26", "PA": "15", "MA": "21"}
CARGOS = ["Presidente", "Governador", "Senador",
          "Deputado Federal", "Deputado Estadual"]
ANOS = [2018, 2022]


def pct(num, den):
    return round(100 * num / den, 3) if den else None


def constroi_uf(uf, ibge):
    votacao = json.load(open(os.path.join(PROC, f"votacao_{uf}.json")))
    perfil = json.load(open(os.path.join(PROC, f"perfil_{uf}.json")))

    # Totais estaduais por cargo e ano.
    tot = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    # Município -> cargo -> ano -> números.
    mun = defaultdict(lambda: defaultdict(dict))
    meta = {}

    for r in votacao:
        if r["cargo"] not in CARGOS:
            continue
        c, a = r["cargo"], str(r["ano"])
        for k in ("aptos", "comparecimento", "abstencoes", "votos",
                  "brancos", "nulos", "nulos_tecnicos", "validos"):
            tot[c][a][k] += r[k]
        mun[r["cd_tse"]][c][a] = [
            r["votos"], r["brancos"], r["nulos"], r["nulos_tecnicos"],
            r["abstencoes"], r["aptos"], r["comparecimento"],
        ]
        meta[r["cd_tse"]] = (r["municipio"], r["cd_ibge"])

    municipios = []
    for cd_tse, dados in mun.items():
        nome, cd_ibge = meta[cd_tse]
        p = perfil.get(cd_tse, {})
        ib = ibge.get(cd_ibge, {})
        municipios.append({
            "c": cd_ibge, "n": nome,
            # Contexto socioeconômico (IBGE) — None quando indisponível.
            "pop": ib.get("populacao"), "dens": ib.get("densidade"),
            "alf": ib.get("alfabetizacao"), "pib": ib.get("pib_per_capita"),
            "sal": ib.get("salario_medio_sm"),
            # Perfil do eleitorado (TSE 2022).
            "el": p.get("eleitores"), "fem": p.get("pct_feminino"),
            "jov": p.get("pct_jovem_16_24"), "i60": p.get("pct_60_mais"),
            "eb": p.get("pct_esc_baixa"), "em": p.get("pct_esc_media"),
            "ea": p.get("pct_esc_alta"),
            "d": {c: {a: v for a, v in anos.items()}
                  for c, anos in dados.items()},
        })
    municipios.sort(key=lambda m: -(m["el"] or 0))

    return {
        "uf": uf, "nome": UFS[uf], "cargos": CARGOS, "anos": ANOS,
        "totais": {c: dict(a) for c, a in tot.items()},
        "municipios": municipios,
    }


def constroi_mapa():
    """Projeta as 27 UFs num viewBox SVG único (equirretangular simples)."""
    gj = json.load(open(MALHA))
    # Extremos continentais do país, para a escala.
    xs, ys = [], []
    for f in gj["features"]:
        for poly in coords(f["geometry"]):
            for x, y in poly:
                xs.append(x)
                ys.append(y)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = 1000.0, 1000.0 * (y1 - y0) / (x1 - x0)

    def proj(x, y):
        return (round((x - x0) / (x1 - x0) * W, 1),
                round((y1 - y) / (y1 - y0) * H, 1))

    paths = {}
    for f in gj["features"]:
        d = []
        for poly in coords(f["geometry"]):
            pontos = simplifica([proj(x, y) for x, y in poly], 1.4)
            # Ilhas minúsculas viram ruído neste tamanho de tela.
            if len(pontos) < 4:
                continue
            d.append("M" + "L".join(f"{a} {b}" for a, b in pontos) + "Z")
        paths[f["properties"]["codarea"]] = "".join(d)
    return {"w": round(W), "h": round(H), "paths": paths}


def simplifica(pontos, tol):
    """Douglas-Peucker iterativo. O mapa é só um seletor de estado, então
    a tolerância pode ser generosa: o contorno precisa ser reconhecível,
    não preciso."""
    if len(pontos) < 3:
        return pontos
    manter = [False] * len(pontos)
    manter[0] = manter[-1] = True
    pilha = [(0, len(pontos) - 1)]
    while pilha:
        ini, fim = pilha.pop()
        if fim <= ini + 1:
            continue
        (x0, y0), (x1, y1) = pontos[ini], pontos[fim]
        dx, dy = x1 - x0, y1 - y0
        norma = (dx * dx + dy * dy) ** 0.5
        pior, idx = 0.0, -1
        for i in range(ini + 1, fim):
            x, y = pontos[i]
            # Distância perpendicular; se o segmento degenera, usa a euclidiana.
            dist = (abs(dy * x - dx * y + x1 * y0 - y1 * x0) / norma
                    if norma else ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5)
            if dist > pior:
                pior, idx = dist, i
        if pior > tol:
            manter[idx] = True
            pilha += [(ini, idx), (idx, fim)]
    return [p for p, m in zip(pontos, manter) if m]


def coords(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [ring for poly in geom["coordinates"] for ring in poly]


def main():
    os.makedirs(SITE, exist_ok=True)
    ibge = json.load(open(os.path.join(PROC, "ibge_municipios.json")))

    resumo = {"ufs": {}, "cod_uf": COD_UF, "cargos": CARGOS, "anos": ANOS}
    for uf in UFS:
        d = constroi_uf(uf, ibge)
        caminho = os.path.join(SITE, f"{uf}.json")
        with open(caminho, "w") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
        resumo["ufs"][uf] = {
            "nome": UFS[uf], "cod": COD_UF[uf],
            "municipios": len(d["municipios"]),
            "totais": d["totais"],
        }
        kb = os.path.getsize(caminho) // 1024
        print(f"{uf}: {len(d['municipios'])} municípios, {kb} KB")

    with open(os.path.join(SITE, "resumo.json"), "w") as f:
        json.dump(resumo, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(SITE, "mapa_uf.json"), "w") as f:
        json.dump(constroi_mapa(), f, separators=(",", ":"))
    mapa_kb = os.path.getsize(os.path.join(SITE, "mapa_uf.json")) // 1024
    print(f"mapa_uf.json: {mapa_kb} KB")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Centroides municipais — insumo do teste de autocorrelação espacial.

Fonte: IBGE, API de malhas territoriais (malha de cada UF dividida por
município). O centroide é calculado pela fórmula da área assinalada, sobre o
maior anel de cada município, o que evita que ilhas puxem o ponto para o mar.

Saída: dados/proc/centroides.json  {codigo_ibge: [lon, lat]}
"""
import gzip, json, os, urllib.request

PROC = os.path.join(os.path.dirname(__file__), "..", "dados", "proc")
UFS = {"SP": 35, "CE": 23, "BA": 29, "PE": 26, "PA": 15, "MA": 21}
API = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/{}"
       "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=municipio")


def baixa(cod):
    req = urllib.request.Request(API.format(cod),
                                 headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=300) as r:
        bruto = r.read()
    if r.headers.get("Content-Encoding") == "gzip" or bruto[:2] == b"\x1f\x8b":
        bruto = gzip.decompress(bruto)
    return json.loads(bruto)


def aneis(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    return [anel for poly in geom["coordinates"] for anel in poly]


def centroide(geom):
    """Centroide do maior anel, pela fórmula da área assinalada."""
    maior, area_maior = None, -1.0
    for anel in aneis(geom):
        a = 0.0
        for i in range(len(anel) - 1):
            x0, y0 = anel[i][:2]
            x1, y1 = anel[i + 1][:2]
            a += x0 * y1 - x1 * y0
        if abs(a) > area_maior:
            maior, area_maior = anel, abs(a)

    a = cx = cy = 0.0
    for i in range(len(maior) - 1):
        x0, y0 = maior[i][:2]
        x1, y1 = maior[i + 1][:2]
        f = x0 * y1 - x1 * y0
        a += f
        cx += (x0 + x1) * f
        cy += (y0 + y1) * f
    if abs(a) < 1e-12:
        # Polígono degenerado: cai para a média simples dos vértices.
        return [sum(p[0] for p in maior) / len(maior),
                sum(p[1] for p in maior) / len(maior)]
    return [cx / (3 * a), cy / (3 * a)]


def main():
    os.makedirs(PROC, exist_ok=True)
    out = {}
    for uf, cod in UFS.items():
        gj = baixa(cod)
        n = 0
        for f in gj["features"]:
            cd = str(f["properties"]["codarea"])
            out[cd] = [round(v, 5) for v in centroide(f["geometry"])]
            n += 1
        print(f"{uf}: {n} municípios")
    with open(os.path.join(PROC, "centroides.json"), "w") as f:
        json.dump(out, f)
    print(f"total: {len(out)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Agrupamentos regionais do IBGE — insumo dos erros-padrão agrupados.

Fonte: IBGE, API de localidades. Traz para cada município a microrregião
(divisão de 1990) e a região geográfica imediata (divisão de 2017, que a
substituiu). As duas são guardadas porque servem de agrupamento alternativo:
se a correção dos erros-padrão depender de qual delas se usa, isso é sinal
de fragilidade e precisa aparecer.

Saída: dados/proc/regioes.json  {codigo_ibge: {"micro":…, "imediata":…}}
"""
import gzip, json, os, urllib.request

PROC = os.path.join(os.path.dirname(__file__), "..", "dados", "proc")
UFS = {"SP": 35, "CE": 23, "BA": 29, "PE": 26, "PA": 15, "MA": 21}
API = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{}/municipios"


def baixa(cod):
    req = urllib.request.Request(API.format(cod),
                                 headers={"Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=180) as r:
        bruto = r.read()
    if r.headers.get("Content-Encoding") == "gzip" or bruto[:2] == b"\x1f\x8b":
        bruto = gzip.decompress(bruto)
    return json.loads(bruto)


def main():
    os.makedirs(PROC, exist_ok=True)
    out = {}
    for uf, cod in UFS.items():
        dados = baixa(cod)
        for m in dados:
            micro = (m.get("microrregiao") or {}).get("id")
            imed = (m.get("regiao-imediata") or {}).get("id")
            out[str(m["id"])] = {"micro": str(micro) if micro else None,
                                 "imediata": str(imed) if imed else None}
        n_micro = len({out[str(m['id'])]["micro"] for m in dados})
        n_imed = len({out[str(m['id'])]["imediata"] for m in dados})
        print(f"{uf}: {len(dados)} municípios, "
              f"{n_micro} microrregiões, {n_imed} regiões imediatas")

    faltando = [k for k, v in out.items() if not v["micro"] or not v["imediata"]]
    if faltando:
        print(f"AVISO: {len(faltando)} municípios sem agrupamento: {faltando[:5]}")
    with open(os.path.join(PROC, "regioes.json"), "w") as f:
        json.dump(out, f)
    print(f"total: {len(out)}")


if __name__ == "__main__":
    main()

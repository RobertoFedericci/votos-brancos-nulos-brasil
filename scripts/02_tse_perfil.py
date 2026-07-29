#!/usr/bin/env python3
"""Perfil do eleitorado por município — insumo do construto de tipo de eleitor.

Fonte: TSE / Dados Abertos — perfil_eleitorado_2022.
Vantagem sobre indicadores censitários: mede exatamente a população que
deposita o voto, na mesma unidade de análise do dado eleitoral.

Saída: dados/proc/perfil_<UF>.json
"""
import csv, io, json, os, zipfile
from collections import defaultdict

RAW = os.path.join(os.path.dirname(__file__), "..", "dados", "raw")
PROC = os.path.join(os.path.dirname(__file__), "..", "dados", "proc")
UFS = ["SP", "CE", "BA", "PE", "PA", "MA"]

# Mesma normalização de 01_tse_votacao.py (os módulos começam com dígito e
# por isso não se importam entre si).
MINUSCULAS = {"da", "das", "de", "di", "do", "dos", "e", "d'"}


def nome_proprio(s):
    palavras = s.title().split()
    return " ".join(p if i == 0 or p.lower() not in MINUSCULAS else p.lower()
                    for i, p in enumerate(palavras))


# Faixas etárias agrupadas a partir de CD_FAIXA_ETARIA (formato AAAB = ini/fim).
def faixa(cd):
    try:
        ini = int(cd[:2]) if len(cd) == 4 else int(cd)
    except ValueError:
        return None
    if ini < 16:
        return None
    if ini <= 24:
        return "jovem_16_24"
    if ini <= 34:
        return "adulto_25_34"
    if ini <= 44:
        return "adulto_35_44"
    if ini <= 59:
        return "maduro_45_59"
    return "idoso_60_mais"

# Escolaridade agrupada em três degraus comparáveis.
ESCOL = {
    "ANALFABETO": "baixa", "LÊ E ESCREVE": "baixa",
    "ENSINO FUNDAMENTAL INCOMPLETO": "baixa",
    "ENSINO FUNDAMENTAL COMPLETO": "media",
    "ENSINO MÉDIO INCOMPLETO": "media", "ENSINO MÉDIO COMPLETO": "media",
    "SUPERIOR INCOMPLETO": "alta", "SUPERIOR COMPLETO": "alta",
}


def processa(uf):
    z = zipfile.ZipFile(os.path.join(RAW, "perfil_eleitorado_2022.zip"))
    acc = defaultdict(lambda: defaultdict(int))
    nomes = {}
    with z.open(f"perfil_eleitorado_2022_{uf}.csv") as fh:
        rd = csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1", newline=""),
                            delimiter=";")
        for row in rd:
            cd = row["CD_MUNICIPIO"].lstrip("0")
            q = int(row["QT_ELEITORES"] or 0)
            a = acc[cd]
            a["total"] += q
            nomes[cd] = row["NM_MUNICIPIO"]
            f = faixa(row["CD_FAIXA_ETARIA"])
            if f:
                a[f] += q
            e = ESCOL.get(row["DS_GRAU_ESCOLARIDADE"].strip())
            if e:
                a["esc_" + e] += q
            if row["DS_GENERO"].strip() == "FEMININO":
                a["feminino"] += q
            # DS_RACA_COR foi deliberadamente descartado: em 2022 a cobertura
            # medida nos seis estados é de 0% (tudo "NÃO INFORMADO"), porque a
            # autodeclaração só é coletada em alistamentos e revisões novas.

    out = {}
    for cd, a in acc.items():
        tot = a["total"] or 1
        out[cd] = {
            "municipio": nome_proprio(nomes[cd]), "eleitores": a["total"],
            "pct_feminino": round(100 * a["feminino"] / tot, 2),
            "pct_jovem_16_24": round(100 * a["jovem_16_24"] / tot, 2),
            "pct_25_34": round(100 * a["adulto_25_34"] / tot, 2),
            "pct_35_44": round(100 * a["adulto_35_44"] / tot, 2),
            "pct_45_59": round(100 * a["maduro_45_59"] / tot, 2),
            "pct_60_mais": round(100 * a["idoso_60_mais"] / tot, 2),
            "pct_esc_baixa": round(100 * a["esc_baixa"] / tot, 2),
            "pct_esc_media": round(100 * a["esc_media"] / tot, 2),
            "pct_esc_alta": round(100 * a["esc_alta"] / tot, 2),
        }
    return out


def main():
    os.makedirs(PROC, exist_ok=True)
    for uf in UFS:
        d = processa(uf)
        with open(os.path.join(PROC, f"perfil_{uf}.json"), "w") as f:
            json.dump(d, f, ensure_ascii=False)
        print(f"{uf}: {len(d)} municípios, "
              f"{sum(v['eleitores'] for v in d.values()):,} eleitores")


if __name__ == "__main__":
    main()

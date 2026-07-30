#!/usr/bin/env python3
"""Filiação partidária por município — teste da hipótese de organização local.

Fonte: TSE / Dados Abertos, "Perfil Filiação Partidária". O arquivo já vem
agregado por município, zona, partido e características demográficas: são
contagens (QT_FILIADO), sem dado pessoal identificável.

RESSALVA DE DATA: o TSE publica um retrato do estado atual do cadastro, não
uma série histórica. O arquivo usado aqui é de junho de 2026, e o desfecho é
a eleição de 2022. Filiação partidária é um estoque de mudança lenta, então o
retrato de 2026 é uma aproximação razoável do de 2022 — mas é aproximação, e
qualquer efeito estimado herda essa imprecisão. Em especial, filiações feitas
depois de 2022 entram na medida.

Três indicadores por município:
  filiados_por_mil  densidade de filiação sobre o eleitorado
  n_partidos        quantos partidos têm ao menos um filiado (capilaridade)
  hhi_partidos      concentração da filiação num único partido (0 a 1)

Saída: dados/proc/filiacao.json
"""
import csv, io, json, os, sys, zipfile
from collections import defaultdict

AQUI = os.path.dirname(__file__)
RAW = os.path.join(AQUI, "..", "dados", "raw")
PROC = os.path.join(AQUI, "..", "dados", "proc")
UFS = {"SP", "CE", "BA", "PE", "PA", "MA"}

# Posições fixas: DictReader é lento demais para 3,5 GB.
I_UF, I_MUN, I_PARTIDO, I_QT = 6, 7, 4, 28


def main():
    z = zipfile.ZipFile(os.path.join(RAW, "perfil_filiacao_partidaria.zip"))
    acc = defaultdict(lambda: defaultdict(int))
    nomes, competencia = {}, None
    lidas = 0

    with z.open("perfil_filiacao_partidaria.csv") as fh:
        t = io.TextIOWrapper(fh, encoding="latin-1", newline="")
        rd = csv.reader(t, delimiter=";")
        next(rd)
        for row in rd:
            lidas += 1
            if lidas % 5_000_000 == 0:
                print(f"  {lidas:,} linhas…", flush=True)
            if row[I_UF] not in UFS:
                continue
            if competencia is None:
                competencia = row[2]
            cd = row[I_MUN].lstrip("0")
            try:
                qt = int(row[I_QT] or 0)
            except ValueError:
                continue
            acc[cd][row[I_PARTIDO]] += qt
            nomes[cd] = row[8]

    print(f"  {lidas:,} linhas lidas; competência {competencia}")

    out = {}
    for cd, partidos in acc.items():
        total = sum(partidos.values())
        if total <= 0:
            continue
        # Herfindahl: 1 = toda a filiação num partido só.
        hhi = sum((v / total) ** 2 for v in partidos.values())
        out[cd] = {"municipio": nomes[cd].title(), "filiados": total,
                   "n_partidos": len(partidos), "hhi": round(hhi, 4)}

    os.makedirs(PROC, exist_ok=True)
    with open(os.path.join(PROC, "filiacao.json"), "w") as f:
        json.dump({"competencia": competencia, "municipios": out}, f,
                  ensure_ascii=False)
    print(f"{len(out)} municípios com filiação registrada")
    tot = sum(v["filiados"] for v in out.values())
    print(f"{tot:,} filiados nos seis estados")


if __name__ == "__main__":
    main()

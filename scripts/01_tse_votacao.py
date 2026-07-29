#!/usr/bin/env python3
"""Agrega os votos brancos, nulos e nulos técnicos por município.

Fonte: TSE / Dados Abertos — detalhe_votacao_munzona 2018 e 2022.
A base vem em granularidade município x zona x cargo; aqui ela é somada
para município x cargo, mantendo 1º turno apenas.

Saída: dados/proc/votacao_<UF>.json
"""
import csv, json, os, sys, zipfile, io
from collections import defaultdict

RAW = os.path.join(os.path.dirname(__file__), "..", "dados", "raw")
PROC = os.path.join(os.path.dirname(__file__), "..", "dados", "proc")
UFS = ["SP", "CE", "BA", "PE", "PA", "MA"]
ANOS = [2018, 2022]

# Campos somados a partir da base município x zona.
CAMPOS = [
    "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES",
    "QT_VOTOS_BRANCOS", "QT_VOTOS_NULOS", "QT_VOTOS_NULOS_TECNICOS",
    "QT_TOTAL_VOTOS_NULOS", "QT_TOTAL_VOTOS_VALIDOS", "QT_VOTOS",
]

# Cargos majoritários e proporcionais das eleições gerais.
CARGOS = {1: "Presidente", 3: "Governador", 5: "Senador",
          6: "Deputado Federal", 7: "Deputado Estadual", 8: "Deputado Distrital"}


# O TSE grafa tudo em caixa alta. str.title() capitalizaria as preposições
# ("Salto De Pirapora"), então elas são rebaixadas — exceto em início de nome.
MINUSCULAS = {"da", "das", "de", "di", "do", "dos", "e", "d'"}


def nome_proprio(s):
    palavras = s.title().split()
    return " ".join(p if i == 0 or p.lower() not in MINUSCULAS else p.lower()
                    for i, p in enumerate(palavras))


def carrega_mapa_ibge():
    """codigo TSE -> (codigo IBGE, nome, uf)"""
    mapa = {}
    with open(os.path.join(RAW, "municipios_tse_ibge.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mapa[r["codigo_tse"].lstrip("0")] = (
                r["codigo_ibge"], r["nome_municipio"], r["uf"])
    return mapa


def le_arquivo(ano, sufixo, filtro_uf=None):
    """Lê um CSV de dentro do zip do ano, sem descompactar em disco."""
    zpath = os.path.join(RAW, f"detalhe_votacao_munzona_{ano}.zip")
    nome = f"detalhe_votacao_munzona_{ano}_{sufixo}.csv"
    with zipfile.ZipFile(zpath) as z:
        with z.open(nome) as fh:
            # O TSE publica em latin-1, separador ';', tudo entre aspas.
            txt = io.TextIOWrapper(fh, encoding="latin-1", newline="")
            for row in csv.DictReader(txt, delimiter=";"):
                if filtro_uf and row["SG_UF"] != filtro_uf:
                    continue
                yield row


def le_uf(ano, uf):
    """Todos os cargos de um estado.

    Os arquivos por UF trazem só as disputas de abrangência estadual
    (governador, senador, deputados). A eleição presidencial tem abrangência
    federal e está apenas no arquivo _BR, de onde ela é filtrada por SG_UF.
    """
    yield from le_arquivo(ano, uf)
    yield from le_arquivo(ano, "BR", filtro_uf=uf)


def agrega(ano, uf, mapa):
    """Soma zonas -> município, para cada cargo. Só 1º turno."""
    acc = defaultdict(lambda: defaultdict(int))
    nomes, sem_ibge = {}, set()
    for row in le_uf(ano, uf):
        if row["NR_TURNO"] != "1":
            continue
        cargo = int(row["CD_CARGO"])
        if cargo not in CARGOS:
            continue
        cd_tse = row["CD_MUNICIPIO"].lstrip("0")
        chave = (cd_tse, cargo)
        for c in CAMPOS:
            # Campos ausentes em algum ano viram 0 em vez de quebrar.
            v = row.get(c, "") or "0"
            acc[chave][c] += int(v)
        nomes[cd_tse] = row["NM_MUNICIPIO"]
        if cd_tse not in mapa:
            sem_ibge.add((cd_tse, row["NM_MUNICIPIO"]))

    out = []
    for (cd_tse, cargo), v in acc.items():
        ibge = mapa.get(cd_tse, ("", nomes[cd_tse], uf))
        # Votos efetivamente depositados na urna para aquele cargo.
        # É o denominador correto: em 2018 o Senado teve 2 votos por eleitor,
        # e QT_VOTOS já reflete isso.
        depositados = v["QT_VOTOS"]
        out.append({
            "cd_tse": cd_tse, "cd_ibge": ibge[0],
            "municipio": nome_proprio(nomes[cd_tse]), "uf": uf,
            "cargo": CARGOS[cargo], "ano": ano,
            "aptos": v["QT_APTOS"], "comparecimento": v["QT_COMPARECIMENTO"],
            "abstencoes": v["QT_ABSTENCOES"], "votos": depositados,
            "brancos": v["QT_VOTOS_BRANCOS"], "nulos": v["QT_VOTOS_NULOS"],
            "nulos_tecnicos": v["QT_VOTOS_NULOS_TECNICOS"],
            "total_nulos": v["QT_TOTAL_VOTOS_NULOS"],
            "validos": v["QT_TOTAL_VOTOS_VALIDOS"],
        })
    return out, sem_ibge


def main():
    os.makedirs(PROC, exist_ok=True)
    mapa = carrega_mapa_ibge()
    problemas = set()
    for uf in UFS:
        registros = []
        for ano in ANOS:
            r, s = agrega(ano, uf, mapa)
            registros += r
            problemas |= s
        with open(os.path.join(PROC, f"votacao_{uf}.json"), "w") as f:
            json.dump(registros, f, ensure_ascii=False)
        muns = len({r["cd_tse"] for r in registros})
        print(f"{uf}: {len(registros)} registros, {muns} municípios")
    if problemas:
        print(f"AVISO: {len(problemas)} códigos TSE sem par IBGE: "
              f"{sorted(problemas)[:10]}")
    else:
        print("Todos os códigos TSE pareados com o IBGE.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Baixa as bases brutas. Rode antes dos demais scripts.

Os arquivos do TSE somam cerca de 32 MB e ficam fora do controle de versão
(ver .gitignore): este script os recompõe do zero a partir das fontes oficiais.
"""
import gzip, os, urllib.request

RAW = os.path.join(os.path.dirname(__file__), "..", "dados", "raw")
TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele"

ARQUIVOS = [
    (f"{TSE}/detalhe_votacao_munzona/detalhe_votacao_munzona_2018.zip",
     "detalhe_votacao_munzona_2018.zip"),
    (f"{TSE}/detalhe_votacao_munzona/detalhe_votacao_munzona_2022.zip",
     "detalhe_votacao_munzona_2022.zip"),
    (f"{TSE}/perfil_eleitorado/perfil_eleitorado_2022.zip",
     "perfil_eleitorado_2022.zip"),
    # Correspondência entre o código de município do TSE e o do IBGE.
    ("https://raw.githubusercontent.com/betafcc/Municipios-Brasileiros-TSE/"
     "master/municipios_brasileiros_tse.csv", "municipios_tse_ibge.csv"),
    # Malha territorial do Brasil dividida por UF, para o mapa seletor.
    ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
     "?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=UF",
     "malha_uf_br.geojson"),
]


def main():
    os.makedirs(RAW, exist_ok=True)
    for url, nome in ARQUIVOS:
        destino = os.path.join(RAW, nome)
        if os.path.exists(destino):
            print(f"já existe: {nome}")
            continue
        print(f"baixando {nome}…")
        with urllib.request.urlopen(url, timeout=300) as r:
            dados = r.read()
        # A API do IBGE responde comprimida mesmo sem negociação explícita.
        # Os .zip do TSE não são tocados: só o gzip de transporte é desfeito.
        if not nome.endswith(".zip") and dados[:2] == b"\x1f\x8b":
            dados = gzip.decompress(dados)
        with open(destino, "wb") as f:
            f.write(dados)
        print(f"  {os.path.getsize(destino) // 1024} KB")


if __name__ == "__main__":
    main()

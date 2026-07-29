#!/usr/bin/env python3
"""Indicadores municipais do IBGE — contexto socioeconômico dos municípios.

Fontes (API SIDRA / servicodados.ibge.gov.br):
  - tabela 4714  Censo 2022: população residente e densidade demográfica
  - tabela 9543  Censo 2022: taxa de alfabetização (15 anos ou mais)
  - tabela 5938  PIB dos Municípios 2021: PIB a preços correntes
  - tabela 1685  CEMPRE 2021: salário médio mensal (em salários mínimos)

Renda domiciliar per capita do Censo 2022 (tabelas 10315 e 10301) não é
publicada em nível municipal — só Brasil e UF —, por isso a renda entra
aqui via PIB per capita e salário médio formal.

Saída: dados/proc/ibge_municipios.json (chave = código IBGE)
"""
import gzip, json, os, time, urllib.request

PROC = os.path.join(os.path.dirname(__file__), "..", "dados", "proc")
UFS = {"SP": 35, "CE": 23, "BA": 29, "PE": 26, "PA": 15, "MA": 21}
BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"


def busca(tabela, periodo, variavel, uf_cod, classificacao=None):
    url = (f"{BASE}/{tabela}/periodos/{periodo}/variaveis/{variavel}"
           f"?localidades=N6[N3[{uf_cod}]]")
    if classificacao:
        url += f"&classificacao={classificacao}"
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                bruto = r.read()
                # O SIDRA responde comprimido mesmo sem negociação explícita.
                if r.headers.get("Content-Encoding") == "gzip" or bruto[:2] == b"\x1f\x8b":
                    bruto = gzip.decompress(bruto)
                return json.loads(bruto)
        except Exception as e:
            if tentativa == 3:
                raise
            print(f"    retry {tentativa+1} ({e})")
            time.sleep(4 * (tentativa + 1))


def extrai(payload, destino, campo):
    """Achata a resposta do SIDRA em {cod_ibge: valor}."""
    if not payload:
        return
    for res in payload[0].get("resultados", []):
        for s in res.get("series", []):
            cod = s["localidade"]["id"]
            for _, v in s["serie"].items():
                # SIDRA usa '-' e '...' para vazio/não aplicável.
                if v in ("-", "...", "..", "X", None, ""):
                    continue
                destino.setdefault(cod, {})[campo] = float(v)


def main():
    dados = {}
    for uf, cod in UFS.items():
        print(f"{uf}...")
        # População e densidade (Censo 2022)
        extrai(busca(4714, 2022, 93, cod), dados, "populacao")
        extrai(busca(4714, 2022, 614, cod), dados, "densidade")
        # Alfabetização (15 anos ou mais). Sem o parâmetro classificacao a API
        # já devolve Total/Total/Total das três classificações da tabela
        # (sexo, cor ou raça, idade), que é o recorte desejado.
        extrai(busca(9543, 2022, 2513, cod), dados, "alfabetizacao")
        # PIB a preços correntes (mil reais) — 2021
        extrai(busca(5938, 2021, 37, cod), dados, "pib_mil")
        # Salário médio mensal em salários mínimos — CEMPRE 2021
        extrai(busca(1685, 2021, 1606, cod), dados, "salario_medio_sm")

    # PIB per capita derivado: PIB vem em mil reais, população em pessoas.
    for cod, d in dados.items():
        if d.get("pib_mil") and d.get("populacao"):
            d["pib_per_capita"] = round(d["pib_mil"] * 1000 / d["populacao"], 2)
        d.pop("pib_mil", None)

    os.makedirs(PROC, exist_ok=True)
    with open(os.path.join(PROC, "ibge_municipios.json"), "w") as f:
        json.dump(dados, f, ensure_ascii=False)

    print(f"\n{len(dados)} municípios")
    for campo in ("populacao", "densidade", "alfabetizacao",
                  "pib_per_capita", "salario_medio_sm"):
        n = sum(1 for d in dados.values() if campo in d)
        print(f"  {campo}: {n} ({100*n//len(dados)}%)")


if __name__ == "__main__":
    main()

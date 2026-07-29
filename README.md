# Votos brancos, nulos e nulos técnicos — seis estados brasileiros

Estudo municipal do não-voto manifesto em **São Paulo, Ceará, Bahia,
Pernambuco, Pará e Maranhão**, nas eleições gerais de **2018 e 2022**.
1.792 municípios, dois pleitos, dados oficiais do TSE e do IBGE.

**Página:** https://robertofedericci.github.io/votos-brancos-nulos-brasil/

Estudo de Roberto Federicci. Trabalho independente, sem vínculo com partido,
campanha ou candidatura.

## O que é medido

O objeto é a parcela do comparecimento que **não se converteu em voto válido**:

| Categoria | Campo do TSE | O que é |
|---|---|---|
| Branco | `QT_VOTOS_BRANCOS` | O eleitor confirma sem indicar candidato |
| Nulo | `QT_VOTOS_NULOS` | O eleitor digita número inexistente ou anula deliberadamente |
| Nulo técnico | `QT_VOTOS_NULOS_TECNICOS` | Voto anulado por decisão da Justiça Eleitoral (candidatura indeferida ou sub judice) — não expressa intenção de quem votou |

A abstenção entra como medida de apoio. Não há análise de candidaturas,
partidos ou resultados de disputa.

## Denominadores

- Brancos, nulos e nulos técnicos: sobre os **votos depositados na urna para o
  cargo** (`QT_VOTOS`).
- Abstenção: sobre o **eleitorado apto** (`QT_APTOS`), porque quem se abstém
  não deposita voto algum.

São denominadores diferentes, e por isso as duas medidas nunca aparecem no
mesmo gráfico.

## Por que o cargo é um filtro, e não um tema

Cada eleitor deposita cinco votos numa eleição geral. Somar as categorias entre
cargos contaria o mesmo eleitor várias vezes. O cargo funciona como recorte: os
percentuais só são comparáveis dentro do mesmo cargo. A visão padrão é
**Presidente**, o único cargo com exatamente um voto por eleitor nos dois anos.

## Ressalvas que mudam a leitura

- **Nulo técnico não existe em 2018.** A base do TSE daquele ano não destaca a
  categoria: o campo vem zerado em todos os municípios dos seis estados — o que
  foi verificado, não presumido. O que hoje seria nulo técnico está embutido no
  nulo comum de 2018. Essa série não é comparável entre os dois pleitos.
- **Senado em 2018** teve duas vagas e dois votos por eleitor; em 2022, uma vaga
  e um voto. Os volumes absolutos de 2018 são cerca de duas vezes maiores por
  construção; o percentual corrige isso.
- **Raça e cor foram descartadas.** O perfil do eleitorado do TSE traz o campo,
  mas nos seis estados a cobertura medida em 2022 é de 0% — praticamente todo o
  eleitorado consta como "não informado", já que a autodeclaração só é coletada
  em alistamentos e revisões recentes.
- **Renda municipal é aproximada.** O rendimento domiciliar per capita do Censo
  2022 não é publicado em nível municipal (apenas Brasil e UF). A renda entra
  por dois substitutos imperfeitos: PIB per capita, que mede produção e não
  renda das famílias, e salário médio do emprego formal, que ignora a economia
  informal — relevante justamente nos municípios mais pobres do recorte.
- **Correlação não é causa.** A aba de perfil cruza agregados municipais e está
  sujeita à falácia ecológica: uma associação entre municípios não descreve
  eleitores individuais. Não há controle por confundidores.

## Fontes

| Fonte | Uso |
|---|---|
| [TSE — Detalhe da votação por município e zona](https://dadosabertos.tse.jus.br/dataset/resultados-2022) | Brancos, nulos, nulos técnicos, abstenção e comparecimento, 2018 e 2022, 1º turno |
| [TSE — Perfil do eleitorado 2022](https://dadosabertos.tse.jus.br/dataset/eleitorado-2022) | Sexo, faixa etária e grau de instrução do eleitorado, por município |
| [IBGE — Censo Demográfico 2022](https://sidra.ibge.gov.br/) | População e densidade (tab. 4714); taxa de alfabetização de 15 anos ou mais (tab. 9543) |
| [IBGE — PIB dos Municípios 2021](https://sidra.ibge.gov.br/tabela/5938) | PIB per capita municipal |
| [IBGE — CEMPRE 2021](https://sidra.ibge.gov.br/tabela/1685) | Salário médio mensal, em salários mínimos |
| [IBGE — Malha territorial](https://servicodados.ibge.gov.br/api/docs/malhas) | Contornos das unidades da federação |
| [Municípios Brasileiros TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE) | Correspondência entre código de município do TSE e do IBGE |

## Reproduzir

Requer apenas Python 3 — sem dependências externas.

```bash
python3 scripts/00_baixa_dados.py    # baixa TSE + tabela de correspondência (~32 MB)
python3 scripts/01_tse_votacao.py    # agrega município x cargo, 1º turno
python3 scripts/02_tse_perfil.py     # perfil do eleitorado por município
python3 scripts/03_ibge.py           # indicadores municipais via API SIDRA
python3 scripts/04_build_site.py     # monta os JSON que a página consome
python3 -m http.server -d site 8000  # abre em http://localhost:8000
```

Os scripts são idempotentes e numerados na ordem de execução. Rodá-los do zero
reconstrói integralmente os arquivos em `site/dados/`.

### Conferência

Os totais estaduais de 2022 para o Senado foram conferidos, um a um, contra os
valores publicados pelo TSE, nos seis estados. O pareamento entre o código de
município do TSE e o do IBGE cobre os 1.792 municípios sem exceção — o script
falha ruidosamente se algum ficar de fora.

## Estrutura

```
scripts/       pipeline, na ordem de execução
dados/raw/     bases brutas baixadas (fora do controle de versão)
dados/proc/    intermediários (fora do controle de versão)
site/          a página publicada — HTML único, sem dependências
site/dados/    JSON por estado, carregados sob demanda
```

## Licença

Código sob licença MIT. Os dados são públicos e pertencem ao TSE e ao IBGE;
cite as fontes originais ao reutilizá-los.

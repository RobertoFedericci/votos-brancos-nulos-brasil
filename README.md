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

## O não-voto absoluto

Em **número absoluto** o problema dos denominadores desaparece, e existe uma
medida que soma tudo:

> **Não-voto** = abstenções + brancos + nulos + nulos técnicos
> = eleitores aptos que **não produziram voto válido**

A soma é legítima porque quem se absteve e quem votou em branco são **conjuntos
disjuntos de pessoas**. A identidade contábil confirma: o resultado é
exatamente igual a `aptos − votos válidos`, verificado em todos os recortes de
um voto por eleitor.

Exemplo — São Paulo, Presidente 2022: **9.028.593 eleitores**, 26,0% dos
34.684.927 aptos.

**Exceção: Senado de 2018.** Com duas vagas e dois votos por eleitor, brancos e
nulos são contados por voto e não por pessoa; somá-los à abstenção contaria
duas vezes quem anulou apenas uma das cédulas. Nesse recorte o valor aparece
como indisponível, não como número errado.

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
  eleitores individuais. Isso continua valendo na aba de modelo — um
  coeficiente estimado sobre municípios não vira efeito sobre pessoas.

## A modelagem

Desfecho: **logito** da taxa de brancos + nulos (Presidente, 2022). Estimação
por **mínimos quadrados ponderados**, peso `n·p·(1−p)` — o inverso da variância
assintótica do logito, porque a taxa de um município com 800 eleitores é muito
mais ruidosa que a de uma capital.

### Por que não há stepwise no resultado final

O stepwise foi rodado e está reportado na página. Foi descartado pelo teste de
estabilidade, não por preferência:

| Recorte | Conjuntos distintos em 200 reamostragens | Frequência do "vencedor" |
|---|---|---|
| Agrupado (n=1.792) | 44 | 12,5% |
| São Paulo (n=645) | 99 | 7,5% |
| Bahia (n=417) | 92 | 5,0% |
| Ceará (n=184) | 109 | 8,5% |

A causa é estrutural: as três variáveis de escolaridade **somam 100 por
construção** (VIF de 79.420, 359.760 e 149.625). Qual delas o algoritmo mantém é
decidido por ruído numérico. O modelo final usa um conjunto pré-especificado,
com a composição reduzida a uma variável, e **elastic net** quando se quer
encolhimento — estável sob colinearidade, ao contrário da busca.

### Um modelo por estado, e por quê

Três especificações aninhadas, comparadas por teste F:

| | Especificação | Parâmetros | SQR |
|---|---|---|---|
| A | Intercepto e inclinações comuns | 9 | 124.620 |
| B | Um intercepto por estado (*estado como variável categórica*) | 14 | 56.448 |
| C | Um intercepto e uma inclinação por estado (*seis modelos separados*) | 54 | 46.841 |

- **B contra A** — os patamares diferem entre estados: F(5, 1778) = 429, p ≈ 1e−302
- **C contra B** — as inclinações **também** diferem: F(40, 1738) = 8,9, p ≈ 8e−47

As duas restrições são rejeitadas. Estado como variável categórica dá a cada
estado o seu próprio patamar, mas impõe **a mesma inclinação a todos** — e os
dados recusam isso. Seis das oito inclinações variam de forma significativa:

| Indicador | F | p | |
|---|---|---|---|
| Eleitoras mulheres | 6,65 | < 0,0001 | varia |
| log PIB per capita | 6,54 | < 0,0001 | varia |
| Eleitores com superior | 4,30 | 0,0007 | varia |
| Eleitores 16-24 | 3,60 | 0,0031 | varia |
| Alfabetização | 3,27 | 0,0061 | varia |
| log Densidade | 2,75 | 0,0176 | varia |
| Salário médio | 1,93 | 0,0859 | estável |
| Eleitores 60+ | 0,90 | 0,4789 | estável |

O caso mais nítido é a **alfabetização**, cuja inclinação padronizada é
**+0,058 em São Paulo** e negativa nos outros cinco (−0,101 a −0,181). Não é
diferença de intensidade: é troca de sinal. Uma inclinação comum produziria uma
média que não descreve nenhum dos seis estados.

Por isso o estudo publica as duas visões, e o modelo agrupado deve ser lido como
resumo — não como o modelo correto.

*O teste F acima supõe observações independentes, e o I de Moran mostrou que
elas não são. Ele foi refeito com variância agrupada por microrregião —
F(40, 189) = 11,5, mais forte que o original. Ver "A correção espacial".*

### Achados

- **O estado pesa mais que o município.** No modelo agrupado, os efeitos fixos
  de estado sozinhos explicam **65,2%** da variância; os oito indicadores
  municipais somam **6,9 pontos** sobre isso (R² total 0,721).
- **O modelo não transfere entre estados.** Retirando um estado inteiro, sem
  efeitos fixos, boosting e mínimos quadrados ficam com R² negativo — pior que
  chutar a média.
- **Dentro de um estado, o poder preditivo é baixo ou nulo.** São Paulo tem R²
  de 0,22 dentro da amostra e negativo fora dela: sobreajuste.
- **Boosting não bate a regressão linear** no modelo agrupado. A relação é
  essencialmente linear, e o modelo simples é o adequado. O boosting não é usado
  para importâncias de variáveis — com 144 municípios no Pará, isso seria ruído.
- **Os resíduos se agrupam no espaço.** I de Moran de +0,29 (p < 0,001, oito
  vizinhos mais próximos) no modelo agrupado, positivo e significativo em quase
  todos os recortes. Há um fator regional não captado, e os erros-padrão usuais
  são otimistas — municípios não são observações independentes.

### A correção espacial

Os erros-padrão foram recalculados sob quatro alternativas à independência:
agrupados por **190 microrregiões**, agrupados por **166 regiões imediatas**, e
de **Conley** (correlação decaindo com a distância) a 100 e a 200 km.

A base de comparação é **HC0, e não HC3** — HC3 corrige alavancagem e os demais
não, então compará-los mistura dois efeitos distintos. Contra HC3, os erros
agrupados pareciam *menores*, o que sugeriria ausência de dependência espacial;
contra HC0 eles são maiores, como esperado. A comparação errada quase inverteu
a leitura.

- Agrupar altera os erros-padrão por fatores de **0,92× a 1,28×**, inflando a
  maioria. **Nenhum coeficiente muda de conclusão.** A dependência espacial é
  real, mas não sustentava nenhum dos resultados relatados.
- O teste de heterogeneidade entre estados, refeito com variância agrupada, dá
  **F(40, 189) = 11,5** contra os 8,9 originais — a conclusão não dependia da
  suposição de independência, e o teste corrigido é mais forte.

### Absorver a região, em vez de só corrigir a variância

Trocando os efeitos fixos de estado pelos das **166 regiões imediatas**:

| Especificação | I de Moran dos resíduos | R² |
|---|---|---|
| Efeitos fixos de estado (6) | 0,294 | 0,721 |
| Efeitos fixos de região imediata (166) | **0,075** | **0,865** |

O agrupamento espacial cai **75%** e o R² sobe 14 pontos. O "fator regional não
captado" tinha nome: é a região imediata. Isso reforça o achado central — o que
governa a taxa de branco e nulo de um município é o lugar onde ele está, numa
escala ainda mais fina que a do estado. Resta alguma estrutura espacial
(I = 0,075), então a região imediata explica a maior parte do fenômeno, não a
totalidade.

### Uma hipótese testada e rejeitada: filiação partidária

O fator regional sugeria uma explicação: onde a organização política local é
densa, o eleitor teria uma estrutura que dá sentido ao voto. Testada com a base
de **filiação partidária do TSE** (6,3 milhões de filiados nos seis estados,
mediana de 150 por mil eleitores):

| Indicador | Coef. | Erro-padrão | p |
|---|---|---|---|
| log Filiados por mil eleitores | −0,0423 | 0,0134 | **0,0016** |
| Partidos com filiados | −0,0198 | 0,0149 | 0,184 |
| Concentração da filiação (HHI) | −0,0018 | 0,0096 | 0,853 |

**O sinal é o previsto; o tamanho não.** A densidade de filiação é significativa
e negativa — mais filiação, menos não-voto — mas:

- acrescenta **+0,8 ponto** de R² (0,721 → 0,729);
- reduz o agrupamento espacial dos resíduos em **2%** (I de Moran 0,294 → 0,288),
  contra os 75% que os efeitos fixos de região produzem;
- correlaciona-se com o resíduo regional a **r = −0,06** (163 regiões).

No agregado por estado o padrão chega a **contrariar** a hipótese: São Paulo tem
a maior densidade de filiação do recorte (184 por mil, contra 118 em Pernambuco)
e a maior taxa de branco e nulo.

**Hipótese descartada** como explicação do fenômeno regional. O efeito municipal
existe, é pequeno, e o fator regional continua sem nome.

*Ressalva de data:* o TSE publica o cadastro de filiação como retrato do
momento, não como série histórica. O arquivo é de junho de 2026 e o desfecho é
de 2022; filiações posteriores a 2022 entram na medida.

### Sobre o R²

É reportado nas versões ponderada e não ponderada. A ponderação é correta para
estimar, mas concentra peso demais: a capital paulista detém **29% do peso** do
estado, e um único bloco de validação cruzada passa a definir a métrica.

## Fontes

| Fonte | Uso |
|---|---|
| [TSE — Detalhe da votação por município e zona](https://dadosabertos.tse.jus.br/dataset/resultados-2022) | Brancos, nulos, nulos técnicos, abstenção e comparecimento, 2018 e 2022, 1º turno |
| [TSE — Perfil do eleitorado 2022](https://dadosabertos.tse.jus.br/dataset/eleitorado-2022) | Sexo, faixa etária e grau de instrução do eleitorado, por município |
| [IBGE — Censo Demográfico 2022](https://sidra.ibge.gov.br/) | População e densidade (tab. 4714); taxa de alfabetização de 15 anos ou mais (tab. 9543) |
| [IBGE — PIB dos Municípios 2021](https://sidra.ibge.gov.br/tabela/5938) | PIB per capita municipal |
| [IBGE — CEMPRE 2021](https://sidra.ibge.gov.br/tabela/1685) | Salário médio mensal, em salários mínimos |
| [IBGE — Malha territorial](https://servicodados.ibge.gov.br/api/docs/malhas) | Contornos das UFs e centroides municipais |
| [IBGE — Localidades](https://servicodados.ibge.gov.br/api/docs/localidades) | Microrregiões e regiões imediatas, para os erros-padrão agrupados |
| [TSE — Perfil Filiação Partidária](https://dadosabertos.tse.jus.br/dataset/delegados-partidarios) | Filiados por município e partido (retrato de junho de 2026) |
| [Municípios Brasileiros TSE](https://github.com/betafcc/Municipios-Brasileiros-TSE) | Correspondência entre código de município do TSE e do IBGE |

## Reproduzir

Requer apenas Python 3 — sem dependências externas.

Os scripts `00` a `05` rodam só com a biblioteca padrão do Python 3.

```bash
python3 scripts/00_baixa_dados.py    # baixa TSE + malha IBGE + correspondência (~32 MB)
python3 scripts/01_tse_votacao.py    # agrega município x cargo, 1º turno
python3 scripts/02_tse_perfil.py     # perfil do eleitorado por município
python3 scripts/03_ibge.py           # indicadores municipais via API SIDRA
python3 scripts/04_build_site.py     # monta os JSON que a página consome
python3 scripts/05_centroides.py     # centroides municipais (autocorrelação espacial)
python3 -m http.server -d site 8000  # abre em http://localhost:8000
```

O passo de modelagem é o único com dependências externas:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/06_modelagem.py       # relatório + modelo.json
.venv/bin/python scripts/07_heterogeneidade.py # testes F entre estados
python3 scripts/08_regioes.py                 # microrregiões e regiões imediatas
.venv/bin/python scripts/09_espacial.py       # erros-padrão espaciais
python3 scripts/10_filiacao.py                # agrega filiação (3,5 GB, ~5 min)
.venv/bin/python scripts/11_teste_filiacao.py # testa a hipótese de filiação
```

Os scripts são idempotentes e numerados na ordem de execução. Rodá-los do zero
reconstrói integralmente os arquivos em `site/dados/`. A semente aleatória é
fixa, então o bootstrap do stepwise e as permutações do I de Moran reproduzem
os mesmos números.

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

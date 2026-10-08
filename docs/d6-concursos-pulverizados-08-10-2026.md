# D6 — concursos com muitos ganhadores (08/10/2026)

> Este estudo só mede. Pedido do usuário em 07/10/2026: estudar os concursos que fogem da média em ganhadores, para ver se algo é perceptível. Método em `stats/estudo_d6.py`.

**838 concursos** com arrecadação registrada e os 14 jogos previstos sem olhar o futuro; **92 pulverizados** (os 10% com mais ganhadores de 14 por milhão arrecadado dentro do mesmo ano).

## Antes do prazo: o que já se sabia
| Sinal | Pulverizados (média) | Outros (média) | Diferença | q | Leitura |
|---|---:|---:|---:|---:|---|
| Dificuldade prevista (soma de −ln da chance do favorito) | 9,47 | 9,76 | -0,29 | 0,007 | diferença real |
| Favoritos com 60% ou mais | 2,98 | 2,49 | +0,49 | 0,015 | diferença real |
| Jogos equilibrados (favorito abaixo de 45%) | 4,18 | 4,65 | -0,47 | 0,035 | diferença real |
| Favorito é o mandante | 11,17 | 11,71 | -0,54 | 0,007 | diferença real |
| Jogos entre seleções | 1,17 | 0,42 | +0,76 | 0,007 | diferença real |
| Jogos entre clubes brasileiros | 10,87 | 11,96 | -1,09 | 0,007 | diferença real |
| Jogos com clube estrangeiro | 1,95 | 1,61 | +0,33 | 0,359 | dentro do acaso |
| Concurso anterior acumulou (0 ou 1) | 0,39 | 0,50 | -0,11 | 0,070 | dentro do acaso |
| Número terminado em 0 ou 5 (0 ou 1) | 0,23 | 0,20 | +0,03 | 0,488 | dentro do acaso |

## Teste fora da amostra
Logística com os sinais de antes do prazo, treinada só nos anos anteriores, em 717 concursos (79 pulverizados): área sob a curva ROC **0,585** (IC 95%: 0,517 a 0,649). 0,5 é o acaso; 1,0 seria acertar sempre.

**Leitura:** há um sinal perceptível antes do prazo, mas fraco: o perfil ajuda a dizer que um concurso tende a ter mais ganhadores, sem dizer quais concursos serão pulverizados.

## Depois do resultado: o que aconteceu
| Sinal | Pulverizados (média) | Outros (média) | Diferença | q | Leitura |
|---|---:|---:|---:|---:|---|
| Favoritos que confirmaram | 9,02 | 6,68 | +2,35 | <0,001 | diferença real |
| Zebras (resultado com menos de 25%) | 1,37 | 2,72 | -1,35 | <0,001 | diferença real |
| Empates | 2,67 | 3,92 | -1,25 | <0,001 | diferença real |
| Vitórias do mandante | 7,78 | 6,35 | +1,43 | <0,001 | diferença real |
| Surpresa total (soma de −ln da chance do resultado) | 12,30 | 14,56 | -2,27 | <0,001 | diferença real |

## Os 15 concursos mais pulverizados (posição no próprio ano)
| Concurso | Ano | Ganhadores de 14 | Por milhão | Favoritos confirmados | Zebras | Dificuldade prevista | Favoritos fortes |
|---|---|---:|---:|---:|---:|---:|---:|
| 563 | 2013 | 4780 | 2284,2 | 10 | 1 | 9,37 | 4 |
| 689 | 2016 | 5453 | 2098,0 | 10 | 1 | 8,39 | 4 |
| 549 | 2013 | 3274 | 1993,7 | 12 | 1 | 8,33 | 4 |
| 992 | 2022 | 1339 | 1173,8 | 8 | 1 | 8,91 | 5 |
| 1048 | 2023 | 1327 | 1062,6 | 12 | 2 | 7,86 | 4 |
| 407 | 2010 | 1005 | 1038,9 | 8 | 3 | 9,52 | 5 |
| 427 | 2010 | 1063 | 620,6 | 10 | 1 | 9,97 | 3 |
| 1225 | 2025 | 710 | 245,6 | 9 | 1 | 10,52 | 2 |
| 645 | 2015 | 487 | 200,2 | 8 | 1 | 10,36 | 3 |
| 534 | 2012 | 376 | 199,6 | 10 | 1 | 9,38 | 4 |
| 442 | 2010 | 413 | 233,1 | 7 | 3 | 9,33 | 3 |
| 1154 | 2024 | 159 | 151,9 | 10 | 0 | 8,99 | 4 |
| 831 | 2018 | 316 | 138,3 | 7 | 1 | 11,12 | 0 |
| 1215 | 2025 | 846 | 146,3 | 12 | 2 | 5,75 | 8 |
| 722 | 2016 | 298 | 132,1 | 11 | 0 | 9,67 | 3 |

## Como ler
- Previsões da época: Elo de clubes nos jogos entre clubes, Elo das seleções e modelo histórico no resto.
- O app nunca estima prêmio em reais; o estudo fala de ganhadores por milhão arrecadado, não de valor.

# B2 nos jogos da Loteca (01/10/2026)

> Este teste só mede. Nenhum percentual exibido no app foi alterado, e trocar o modelo exige decisão do usuário.

## Pergunta
O teste B2 anterior usou os jogos da CBF. Aqui o mesmo método é aplicado aos jogos que de fato entram nos concursos da Loteca: os modelos que usam a temporada da CBF superam o modelo atual do app e a frequência simples de 1/X/2?

## Base e método
- Quatro modelos sobre **exatamente os mesmos jogos**: frequência simples de 1/X/2 da Loteca (referência do B3); modelo atual do app (Poisson sobre o histórico da Loteca, versão incremental do B3); retrospecto dos dois times na temporada da CBF (logística treinada só nos jogos da CBF de anos anteriores); Poisson da temporada da CBF, refeito só com jogos disputados antes do dia.
- Só entra jogo entre dois clubes das Séries A ou B da CBF **na mesma série** no ano, com pelo menos 5 jogos de cada time já disputados antes do dia do jogo (o jogo do próprio dia não conta). Seleções, estaduais, copas e times de outras divisões ficam de fora: o modelo da temporada não tem base para eles.
- Comparação pareada jogo a jogo; intervalo de 95% e valor p unilateral por reamostragem de concursos (2000 repetições); valor q de Benjamini-Hochberg entre as seis comparações (critério: perda logarítmica, como no B3).

## Cobertura (funil)

| Etapa | Jogos |
|---|---:|
| Jogos apurados da Loteca (sem os decididos por sorteio) | 17679 |
| Com data, em ano com treino anterior da CBF | 5441 |
| Os dois times pareados com a CBF | 2648 |
| Os dois na mesma série da CBF no ano | 1938 |
| Cada time com jogos suficientes antes do dia | 1516 |
| Com previsão do modelo atual (depois do aquecimento do B3) | 1516 |

O resultado vale para esses **1516** jogos, não para o concurso inteiro.

## Desempenho de cada modelo

| Modelo | Jogos | Acerto do favorito | Brier | Perda logarítmica |
|---|---:|---:|---:|---:|
| Frequência simples de 1/X/2 da Loteca | 1516 | 48,4% | 0,6331 | 1,0512 |
| Modelo atual do app (Poisson sobre o histórico da Loteca) | 1516 | 48,0% | 0,6365 | 1,0554 |
| Retrospecto dos dois times na temporada da CBF (logística) | 1516 | 49,7% | 0,6168 | 1,0270 |
| Poisson da temporada da CBF | 1516 | 48,5% | 0,6205 | 1,0329 |

## Comparações pareadas (ganho positivo = o primeiro modelo é melhor)

| Comparação | Ganho em perda logarítmica | IC 95% | p | q | Ganho em Brier | IC 95% | Conclusão |
|---|---:|---|---:|---:|---:|---|---|
| Modelo atual do app (Poisson sobre o histórico da Loteca) contra frequência simples de 1/X/2 da Loteca | -0,0041 | -0,0202 a +0,0097 | 0,712 | 0,854 | -0,0033 | -0,0129 a +0,0060 | sem diferença perceptível |
| Retrospecto dos dois times na temporada da CBF (logística) contra frequência simples de 1/X/2 da Loteca | +0,0242 | +0,0148 a +0,0341 | <0,001 | 0,003 | +0,0163 | +0,0102 a +0,0228 | melhor |
| Poisson da temporada da CBF contra frequência simples de 1/X/2 da Loteca | +0,0183 | +0,0041 a +0,0329 | 0,007 | 0,015 | +0,0126 | +0,0027 a +0,0226 | melhor |
| Retrospecto dos dois times na temporada da CBF (logística) contra modelo atual do app (Poisson sobre o histórico da Loteca) | +0,0284 | +0,0112 a +0,0458 | 0,002 | 0,006 | +0,0197 | +0,0080 a +0,0313 | melhor |
| Poisson da temporada da CBF contra modelo atual do app (Poisson sobre o histórico da Loteca) | +0,0225 | +0,0034 a +0,0414 | 0,010 | 0,015 | +0,0160 | +0,0030 a +0,0286 | melhor |
| Poisson da temporada da CBF contra retrospecto dos dois times na temporada da CBF (logística) | -0,0059 | -0,0146 a +0,0025 | 0,907 | 0,907 | -0,0037 | -0,0097 a +0,0023 | sem diferença perceptível |

## Perda logarítmica por ano (só descritivo)

| Ano | Jogos | Frequência simples de 1/X/2 da Loteca | Modelo atual do app (Poisson sobre o histórico da Loteca) | Retrospecto dos dois times na temporada da CBF (logística) | Poisson da temporada da CBF |
|---|---:|---:|---:|---:|---:|
| 2020 | 64 | 1,0527 | 1,0699 | 1,0706 | 1,0711 |
| 2021 | 99 | 1,0923 | 1,1038 | 1,0898 | 1,0869 |
| 2022 | 182 | 1,0723 | 1,0656 | 1,0484 | 1,0379 |
| 2023 | 273 | 1,0503 | 1,0660 | 1,0212 | 1,0463 |
| 2024 | 349 | 1,0508 | 1,0505 | 1,0269 | 1,0267 |
| 2025 | 306 | 1,0276 | 1,0243 | 0,9886 | 0,9854 |
| 2026 | 243 | 1,0498 | 1,0583 | 1,0289 | 1,0508 |

## Como ler
- "Melhor" significa mais probabilidade dada ao que de fato aconteceu, fora da amostra, com q < 0,05. "Sem diferença perceptível" não prova igualdade: a amostra pode não detectar ganho pequeno.
- O acerto do favorito não é o critério: o que importa é a qualidade das probabilidades (perda logarítmica e Brier).
- Os jogos de um mesmo concurso compartilham contexto, por isso o intervalo reamostra concursos. Times se repetem entre concursos, o que o intervalo não corrige por completo.
- O resultado descreve os jogos entre clubes das Séries A e B com dados suficientes da temporada. Não cobre seleções, estaduais, copas nem times de outras divisões, que são grande parte dos concursos.
- Mudar o percentual exibido no app seria uma decisão separada, com aprovação do usuário.

## Reprodução
`.venv\Scripts\python scripts\backtest_loteca.py` (só lê `loteca.db`; semente em `config.B2_SEMENTE`).

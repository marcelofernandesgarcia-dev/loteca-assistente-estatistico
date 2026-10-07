# B2 nos jogos da Loteca (07/10/2026)

> Este teste só mede. Desde 07/10/2026 o app usa o retrospecto da CBF nos jogos entre clubes da mesma série A ou B (decisão do usuário, com este teste como base); `LOTECA_MODELO_CLUBES=historico` volta ao modelo anterior.
>
> Refeito em 07/10/2026 com o pareamento CBF x Loteca corrigido (1.676 jogos, antes 1.516). Conferências feitas no mesmo dia: a função usada na tela (`stats/modelo_cbf.py`) reproduz este teste nos 1.676 jogos com diferença zero; e a correção de calibração, aplicada ano a ano ao retrospecto, piorou a perda logarítmica (1,0264 sem correção, 1,0287 com), por isso o modelo novo entra sem correção.

## Pergunta
O teste B2 anterior usou os jogos da CBF. Aqui o mesmo método é aplicado aos jogos que de fato entram nos concursos da Loteca: os modelos que usam a temporada da CBF superam o modelo atual do app e a frequência simples de 1/X/2?

## Base e método
- Quatro modelos sobre **exatamente os mesmos jogos**: frequência simples de 1/X/2 da Loteca (referência do B3); modelo atual do app (Poisson sobre o histórico da Loteca, versão incremental do B3); retrospecto dos dois times na temporada da CBF (logística treinada só nos jogos da CBF de anos anteriores); Poisson da temporada da CBF, refeito só com jogos disputados antes do dia.
- Só entra jogo entre dois clubes das Séries A ou B da CBF **na mesma série** no ano, com pelo menos 5 jogos de cada time já disputados antes do dia do jogo (o jogo do próprio dia não conta). Seleções, estaduais, copas e times de outras divisões ficam de fora: o modelo da temporada não tem base para eles.
- Comparação pareada jogo a jogo; intervalo de 95% e valor p unilateral por reamostragem de concursos (2000 repetições); valor q de Benjamini-Hochberg entre as seis comparações (critério: perda logarítmica, como no B3).

## Cobertura (funil)

| Etapa | Jogos |
|---|---:|
| Jogos apurados da Loteca (sem os decididos por sorteio) | 17693 |
| Com data, em ano com treino anterior da CBF | 5455 |
| Os dois times pareados com a CBF | 3248 |
| Os dois na mesma série da CBF no ano | 2156 |
| Cada time com jogos suficientes antes do dia | 1676 |
| Com previsão do modelo atual (depois do aquecimento do B3) | 1676 |

O resultado vale para esses **1676** jogos, não para o concurso inteiro.

## Desempenho de cada modelo

| Modelo | Jogos | Acerto do favorito | Brier | Perda logarítmica |
|---|---:|---:|---:|---:|
| Frequência simples de 1/X/2 da Loteca | 1676 | 47,7% | 0,6360 | 1,0552 |
| Modelo atual do app (Poisson sobre o histórico da Loteca) | 1676 | 47,4% | 0,6394 | 1,0593 |
| Retrospecto dos dois times na temporada da CBF (logística) | 1676 | 48,9% | 0,6203 | 1,0323 |
| Poisson da temporada da CBF | 1676 | 48,1% | 0,6220 | 1,0354 |

## Comparações pareadas (ganho positivo = o primeiro modelo é melhor)

| Comparação | Ganho em perda logarítmica | IC 95% | p | q | Ganho em Brier | IC 95% | Conclusão |
|---|---:|---|---:|---:|---:|---|---|
| Modelo atual do app (Poisson sobre o histórico da Loteca) contra frequência simples de 1/X/2 da Loteca | -0,0041 | -0,0181 a +0,0090 | 0,728 | 0,767 | -0,0034 | -0,0129 a +0,0053 | sem diferença perceptível |
| Retrospecto dos dois times na temporada da CBF (logística) contra frequência simples de 1/X/2 da Loteca | +0,0229 | +0,0135 a +0,0327 | <0,001 | 0,001 | +0,0157 | +0,0092 a +0,0218 | melhor |
| Poisson da temporada da CBF contra frequência simples de 1/X/2 da Loteca | +0,0198 | +0,0051 a +0,0338 | 0,006 | 0,010 | +0,0140 | +0,0040 a +0,0231 | melhor |
| Retrospecto dos dois times na temporada da CBF (logística) contra modelo atual do app (Poisson sobre o histórico da Loteca) | +0,0271 | +0,0110 a +0,0431 | <0,001 | 0,001 | +0,0191 | +0,0073 a +0,0299 | melhor |
| Poisson da temporada da CBF contra modelo atual do app (Poisson sobre o histórico da Loteca) | +0,0239 | +0,0059 a +0,0425 | 0,005 | 0,010 | +0,0174 | +0,0047 a +0,0305 | melhor |
| Poisson da temporada da CBF contra retrospecto dos dois times na temporada da CBF (logística) | -0,0032 | -0,0112 a +0,0047 | 0,767 | 0,767 | -0,0017 | -0,0070 a +0,0040 | sem diferença perceptível |

## Perda logarítmica por ano (só descritivo)

| Ano | Jogos | Frequência simples de 1/X/2 da Loteca | Modelo atual do app (Poisson sobre o histórico da Loteca) | Retrospecto dos dois times na temporada da CBF (logística) | Poisson da temporada da CBF |
|---|---:|---:|---:|---:|---:|
| 2020 | 81 | 1,0308 | 1,0252 | 1,0700 | 1,0526 |
| 2021 | 108 | 1,0913 | 1,0997 | 1,0845 | 1,0881 |
| 2022 | 202 | 1,0783 | 1,0705 | 1,0513 | 1,0387 |
| 2023 | 303 | 1,0591 | 1,0771 | 1,0296 | 1,0542 |
| 2024 | 391 | 1,0527 | 1,0533 | 1,0288 | 1,0224 |
| 2025 | 344 | 1,0411 | 1,0436 | 1,0082 | 1,0051 |
| 2026 | 247 | 1,0473 | 1,0534 | 1,0236 | 1,0439 |

## Como ler
- "Melhor" significa mais probabilidade dada ao que de fato aconteceu, fora da amostra, com q < 0,05. "Sem diferença perceptível" não prova igualdade: a amostra pode não detectar ganho pequeno.
- O acerto do favorito não é o critério: o que importa é a qualidade das probabilidades (perda logarítmica e Brier).
- Os jogos de um mesmo concurso compartilham contexto, por isso o intervalo reamostra concursos. Times se repetem entre concursos, o que o intervalo não corrige por completo.
- O resultado descreve os jogos entre clubes das Séries A e B com dados suficientes da temporada. Não cobre seleções, estaduais, copas nem times de outras divisões, que são grande parte dos concursos.
- Mudar o percentual exibido no app seria uma decisão separada, com aprovação do usuário.

## Reprodução
`.venv\Scripts\python scripts\backtest_loteca.py` (só lê `loteca.db`; semente em `config.B2_SEMENTE`).

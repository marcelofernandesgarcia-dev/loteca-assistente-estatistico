# Série C: modelo da temporada e fase decisiva (07/10/2026)

> Este estudo só mede. Nenhum percentual do app foi alterado por ele.

## Dados (páginas públicas da CBF, coletadas em 07/10/2026)
| Ano | Jogos | Com placar | Fases | Jogos sem fase |
|---|---:|---:|---:|---:|
| 2019 | 194 | 194 | 4 | 0 |
| 2020 | 206 | 206 | 3 | 0 |
| 2021 | 206 | 206 | 3 | 0 |
| 2022 | 216 | 216 | 3 | 0 |
| 2023 | 216 | 216 | 3 | 0 |
| 2024 | 216 | 216 | 3 | 0 |
| 2025 | 216 | 216 | 3 | 0 |
| 2026 | 210 | 210 | 2 | 0 |

Jogo sem fase: a sequência de rodadas da temporada não fechou com as fases da CBF; esses jogos ficam fora do item C2.

## B3 — modelo da temporada nos jogos da CBF (Série C)
| Modelo | Jogos | Perda logarítmica | Acerto do favorito |
|---|---:|---:|---:|
| Frequência simples de 1/X/2 | 1114 | 1,0612 | 45,6% |
| Retrospecto dos dois times (logística) | 1114 | 1,0601 | 43,3% |
| Poisson da temporada (modelo_temporada) | 1114 | 1,0793 | 42,5% |

| Comparação | Ganho em perda log | IC 95% | q | Conclusão |
|---|---:|---|---:|---|
| Retrospecto dos dois times (logística) contra frequência simples de 1/X/2 | +0,0011 | -0,0083 a +0,0098 | 0,997 | sem diferença perceptível |
| Poisson da temporada (modelo_temporada) contra frequência simples de 1/X/2 | -0,0181 | -0,0355 a -0,0007 | 0,997 | pior |
| Poisson da temporada (modelo_temporada) contra retrospecto dos dois times (logística) | -0,0192 | -0,0347 a -0,0049 | 0,997 | pior |

## B3 — nos jogos da Loteca entre dois clubes da Série C (o critério da decisão)
| Etapa | Jogos |
|---|---:|
| Jogos apurados da Loteca (sem os decididos por sorteio) | 17693 |
| Com data, em ano com treino anterior da CBF | 5455 |
| Os dois times pareados com a CBF | 3248 |
| Os dois na mesma série da CBF no ano | 90 |
| Cada time com jogos suficientes antes do dia | 70 |
| Com previsão do modelo atual (depois do aquecimento do B3) | 70 |

| Modelo | Perda logarítmica | Acerto do favorito |
|---|---:|---:|
| Frequência simples de 1/X/2 da Loteca | 1,1028 | 40,0% |
| Modelo atual do app (Poisson sobre o histórico da Loteca) | 1,1710 | 38,6% |
| Retrospecto dos dois times na temporada da CBF (logística) | 1,0810 | 41,4% |
| Poisson da temporada da CBF | 1,0805 | 35,7% |

| Comparação | Ganho em perda log | IC 95% | q | Conclusão |
|---|---:|---|---:|---|
| Modelo atual do app (Poisson sobre o histórico da Loteca) contra frequência simples de 1/X/2 da Loteca | -0,0682 | -0,1655 a +0,0106 | 0,948 | sem diferença perceptível |
| Retrospecto dos dois times na temporada da CBF (logística) contra frequência simples de 1/X/2 da Loteca | +0,0218 | -0,0260 a +0,0668 | 0,273 | sem diferença perceptível |
| Poisson da temporada da CBF contra frequência simples de 1/X/2 da Loteca | +0,0223 | -0,0212 a +0,0666 | 0,273 | sem diferença perceptível |
| Retrospecto dos dois times na temporada da CBF (logística) contra modelo atual do app (Poisson sobre o histórico da Loteca) | +0,0900 | -0,0007 a +0,1908 | 0,079 | sem diferença perceptível |
| Poisson da temporada da CBF contra modelo atual do app (Poisson sobre o histórico da Loteca) | +0,0905 | +0,0086 a +0,1843 | 0,079 | sem diferença perceptível |
| Poisson da temporada da CBF contra retrospecto dos dois times na temporada da CBF (logística) | +0,0005 | -0,0507 a +0,0513 | 0,578 | sem diferença perceptível |

**Critério não atingido (q 0,079, precisa ser menor que 0,05): a Série C segue com o modelo anterior e o aviso de cobertura parcial. Refazer quando houver mais jogos da Série C na Loteca.**

## C2 — a fase decisiva empata mais?
| Fase | Jogos | Empates | Taxa | IC 95% |
|---|---:|---:|---:|---|
| 1ª fase | 1490 | 458 | 30,7% | 28,4% a 33,1% |
| 2ª fase em diante | 190 | 63 | 33,2% | 26,9% a 40,1% |

Diferença (decisivas menos 1ª fase): +2,4 pontos percentuais (IC 95%: -4,7 a +9,5).

Critério: acrescentar "fase decisiva" ao retrospecto, treinado em anos anteriores, em 1114 jogos testados: ganho médio -0,0064 na perda logarítmica (IC 95%: -0,0128 a -0,0009; q 0,989). **Não há melhora comprovada: a fase fica só como contexto na tela.**

## Como ler
- Perda logarítmica: quanto menor, mais chance o modelo deu ao que aconteceu. É o critério de troca de modelo.
- Treino só com temporadas anteriores da Série C; os jogos de uma rodada compartilham contexto, por isso o intervalo reamostra rodadas (CBF) ou concursos (Loteca).
- Taxa de empate é descritiva; só o teste fora da amostra diz se a fase ajuda a prever.

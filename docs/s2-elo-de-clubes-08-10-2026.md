# S2 — Elo de clubes com os jogos da Loteca (08/10/2026)

> Este estudo só mede. Critério fixado antes (regra do usuário): o modelo novo só entra se a perda logarítmica fora da amostra for menor com q < 0,05.

## Método
- Rating Elo de cada participante com todos os jogos apurados da Loteca (inicial 1500, K = 20, vantagem de mando de 65 pontos; valores de convenção, não ajustados).
- A diferença de rating vira 1/X/2 pela curva do Elo das seleções (logística ordenada), ajustada só com jogos de anos anteriores.
- Jogos entre dois clubes de 2020 em diante, cada concurso previsto só com os anteriores. Intervalos e valor p por reamostragem de concursos; valor q de Benjamini-Hochberg entre as três comparações.
- Base: Hvattum e Arntzen (2010), International Journal of Forecasting 26, p. 460–470.

## Resultados
### Jogos "demais" (clubes fora do modelo da temporada da CBF)
| Modelo | Jogos | Perda logarítmica | RPS | Acerto do favorito |
|---|---:|---:|---:|---:|
| Frequência simples de 1/X/2 | 3496 | 1,0751 | 0,2232 | 44,3% |
| Modelo atual (Poisson histórico, calibrado) | 3496 | 1,0601 | 0,2179 | 45,0% |
| Elo de clubes | 3496 | 1,0318 | 0,2084 | 48,1% |
| Elo de clubes com a calibração do app | 3496 | 1,0320 | 0,2086 | 48,1% |
| Só jogos sem base própria: modelo atual | 1018 | 1,0774 | 0,2251 | 43,4% |
| Só jogos sem base própria: Elo de clubes | 1018 | 1,0447 | 0,2138 | 47,1% |

### Séries A e B (clubes na mesma série)
| Modelo | Jogos | Perda logarítmica | RPS | Acerto do favorito |
|---|---:|---:|---:|---:|
| Temporada da CBF (em uso desde 07/10/2026) | 1676 | 1,0323 | 0,2095 | 48,9% |
| Média: temporada da CBF + Elo de clubes | 1676 | 1,0250 | 0,2071 | 49,3% |

### Comparações (ganho positivo = o primeiro é melhor)
| Comparação | Ganho em perda log | IC 95% | q | Conclusão |
|---|---:|---|---:|---|
| Elo de clubes contra o modelo atual, nos demais | +0,0283 | +0,0182 a +0,0378 | 0,001 | melhor |
| Elo calibrado contra o Elo sem calibração, nos demais | -0,0002 | -0,0027 a +0,0026 | 0,559 | sem diferença perceptível |
| Média temporada + Elo contra a temporada, nas Séries A e B | +0,0072 | +0,0027 a +0,0120 | 0,002 | melhor |

## Decisão
- Demais: **critério atingido** — o Elo de clubes passa a dar o percentual desses jogos.
- Calibração do Elo: não ajuda — o Elo entra sem correção.
- Séries A e B: **critério atingido** — o percentual passa a ser a média entre a temporada da CBF e o Elo.

Interruptor: `LOTECA_ELO_CLUBES=0` volta ao cálculo anterior em todos os jogos.

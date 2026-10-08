# S3 e S4 — variações do Elo de clubes (08/10/2026)

> Este estudo só mede. Critério do usuário: a variação só substitui o Elo em uso com perda logarítmica menor fora da amostra e q < 0,05. Método em `stats/estudo_s3_s4.py`.

**5172 jogos entre clubes** de 2020 em diante, todos previstos andando no tempo, os mesmos para todas as variações.

Base (Elo em uso no início do estudo, K 20, sem margem): perda 1,0304, acerto do favorito 48,3%.

| Variação | Perda log | Acerto do favorito | Ganho sobre a base | IC 95% | q | Conclusão |
|---|---:|---:|---:|---|---:|---|
| V1 margem de gols | 1,0290 | 48,5% | +0,0014 | +0,0004 a +0,0024 | 0,014 | melhor |
| V2 K ajustado (15) | 1,0307 | 48,3% | -0,0004 | -0,0012 a +0,0004 | 0,804 | sem diferença perceptível |
| V3 pi-ratings | 1,0294 | 48,6% | +0,0009 | -0,0021 a +0,0039 | 0,371 | sem diferença perceptível |
| V4 com os jogos da CBF | 1,0289 | 48,7% | +0,0014 | -0,0010 a +0,0038 | 0,257 | sem diferença perceptível |

Escolha do K (perda nos jogos de 2015 a 2019; nada de 2020 em diante entra na escolha): K 10: 1,0279; K 15: 1,0273; K 20: 1,0274; K 30: 1,0284; K 40: 1,0297.

## Decisão
- Aprovadas pelo critério: V1 margem de gols.
- As demais não entram: o ganho não se distinguiu do acaso.

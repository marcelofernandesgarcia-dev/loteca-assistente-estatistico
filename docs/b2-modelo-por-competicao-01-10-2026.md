# B2 — Teste dos modelos de 1/X/2 por competição (01/10/2026)

> Este teste só mede. Nenhum percentual exibido no app foi alterado, e trocar o modelo exige decisão do usuário.

## Pergunta
Um modelo que usa os jogos da temporada (CBF) prevê o resultado melhor do que a frequência simples de 1, X e 2? Esta é a condição que o roteiro (B2) impôs antes de qualquer mudança no modelo.

## Base e método
- **4370** jogos das Séries A e B da CBF, testados de 2020 a 2026; cada ano é testado com treino só nos anos anteriores. Cada time precisa ter pelo menos 5 jogos já conhecidos na temporada; todos os modelos usam exatamente os mesmos jogos.
- Sem olhar o futuro: para cada rodada, só contam jogos de rodada anterior **e** disputados antes do primeiro jogo da rodada (jogo adiado não conta antes de acontecer).
- **Frequência simples:** frequência de 1, X e 2 nos anos anteriores. **Retrospecto:** regressão logística multinomial com os pontos por jogo dos dois times na temporada. **Poisson da temporada:** `modelo_temporada` (ataque e defesa de cada time, com prior), refeito a cada rodada.
- Métricas (menor é melhor): perda logarítmica e Brier. Acerto do favorito também é mostrado. Comparação pareada jogo a jogo; intervalo de 95% e valor p unilateral por reamostragem de rodadas (2000 repetições); valor q de Benjamini-Hochberg entre as três comparações (critério: perda logarítmica, como no B3).

## Desempenho de cada modelo

| Modelo | Jogos | Acerto do favorito | Brier | Perda logarítmica |
|---|---:|---:|---:|---:|
| Frequência simples de 1/X/2 | 4370 | 47,0% | 0,6389 | 1,0589 |
| Retrospecto dos dois times (logística) | 4370 | 47,6% | 0,6260 | 1,0403 |
| Poisson da temporada (modelo_temporada) | 4370 | 46,5% | 0,6271 | 1,0429 |

## Comparações pareadas (ganho positivo = o primeiro modelo é melhor)

| Comparação | Ganho em perda logarítmica | IC 95% | p | q | Ganho em Brier | IC 95% | Conclusão |
|---|---:|---|---:|---:|---:|---|---|
| Retrospecto dos dois times (logística) contra frequência simples de 1/X/2 | +0,0186 | +0,0126 a +0,0246 | <0,001 | 0,001 | +0,0129 | +0,0090 a +0,0168 | melhor |
| Poisson da temporada (modelo_temporada) contra frequência simples de 1/X/2 | +0,0160 | +0,0068 a +0,0250 | <0,001 | 0,001 | +0,0118 | +0,0057 a +0,0178 | melhor |
| Poisson da temporada (modelo_temporada) contra retrospecto dos dois times (logística) | -0,0026 | -0,0081 a +0,0029 | 0,809 | 0,809 | -0,0011 | -0,0047 a +0,0028 | sem diferença perceptível |

## Por série (mesmo método, só descritivo)

| Série | Jogos | Modelo | Acerto | Brier | Perda logarítmica |
|---|---:|---|---:|---:|---:|
| serie-a | 2163 | Frequência simples de 1/X/2 | 46,9% | 0,6396 | 1,0601 |
| serie-a | 2163 | Retrospecto dos dois times (logística) | 48,2% | 0,6221 | 1,0350 |
| serie-a | 2163 | Poisson da temporada (modelo_temporada) | 47,3% | 0,6250 | 1,0392 |
| serie-b | 2207 | Frequência simples de 1/X/2 | 47,1% | 0,6383 | 1,0578 |
| serie-b | 2207 | Retrospecto dos dois times (logística) | 46,9% | 0,6298 | 1,0456 |
| serie-b | 2207 | Poisson da temporada (modelo_temporada) | 45,8% | 0,6291 | 1,0465 |

## Como ler
- "Melhor" significa mais probabilidade dada ao que de fato aconteceu, fora da amostra, com q < 0,05. "Sem diferença perceptível" não prova igualdade: a amostra pode não detectar ganho pequeno.
- O acerto do favorito não é o critério: o que importa é a qualidade das probabilidades (perda logarítmica e Brier).
- Os jogos de uma mesma rodada compartilham contexto; por isso o intervalo reamostra rodadas, não jogos. Times se repetem entre rodadas, o que o intervalo não corrige por completo.
- Isto vale para os jogos da CBF. O percentual da Loteca também depende de seleções e de times fora das Séries A e B, que este teste não cobre.

## Reprodução
`.venv\Scripts\python scripts\backtest_competicao.py` (só lê `loteca.db`; semente em `config.B2_SEMENTE`).

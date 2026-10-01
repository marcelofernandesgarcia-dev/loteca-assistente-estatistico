# Calibração dos percentuais — Fase 1 (01/10/2026)

> Estudo só de leitura. Nenhum percentual do app foi alterado. A integração (Fase 2) depende da validação do usuário.

## Pergunta
Os percentuais do app são confiantes demais (o estudo de 30/09 viu a chance de 13 ou mais cerca de 7 vezes acima do que aconteceu). Uma correção simples, ajustada só com o passado, aproxima a chance do bilhete do que de fato acontece?

## Base e método
- **15740** jogos em **1171** concursos, com a previsão que o app daria na época (sem olhar o futuro): Elo nos jogos entre seleções depois de 2010, força histórica dos clubes nos demais, frequência simples quando faltam jogos.
- Por origem: Seleções: Elo 239; Frequência simples (poucos jogos) 2617; Clubes: força histórica (Poisson) 12884.
- Correção: o percentual é elevado a um **expoente** (abaixo de 1 achata percentuais confiantes demais) e **misturado** com a frequência simples. Expoente 1 e mistura 1 significam sem correção.
- Os parâmetros de cada bloco de 25 concursos são ajustados só com os concursos anteriores, por origem. Só entram na avaliação jogos cuja origem já tinha treino suficiente.
- Método principal definido antes do resultado: expoente e mistura juntos. Os dois isolados aparecem só para comparação.
- Comparação pareada jogo a jogo com a versão sem correção; intervalo e valor p por reamostragem de concursos (2000 repetições); valor q de Benjamini-Hochberg entre as três correções.

## Parâmetros que o app usaria hoje (ajustados com todos os concursos)

| Origem | Jogos | Expoente | Mistura | Leitura |
|---|---:|---:|---:|---|
| Seleções: Elo | 420 | 1,00 | 1,00 | mantém o formato; 0% de peso para a frequência simples |
| Frequência simples (poucos jogos) | 3179 | 0,80 | 0,95 | achata os percentuais; 5% de peso para a frequência simples |
| Clubes: força histórica (Poisson) | 13388 | 0,60 | 0,95 | achata os percentuais; 5% de peso para a frequência simples |

## Qualidade dos percentuais (menor é melhor)

| Versão | Perda logarítmica | Brier |
|---|---:|---:|
| Sem correção (percentuais de hoje) | 1,0679 | 0,6427 |
| Só expoente | 1,0416 | 0,6263 |
| Só mistura com a frequência | 1,0478 | 0,6312 |
| Expoente e mistura (principal) | 1,0418 | 0,6265 |
| Frequência simples (referência) | 1,0591 | 0,6388 |

| Correção contra sem correção | Ganho em perda logarítmica | IC 95% | q | Conclusão |
|---|---:|---|---:|---|
| Só expoente | +0,0262 | +0,0224 a +0,0301 | <0,001 | melhor que sem correção |
| Só mistura com a frequência | +0,0200 | +0,0165 a +0,0240 | <0,001 | melhor que sem correção |
| Expoente e mistura (principal) | +0,0261 | +0,0223 a +0,0299 | <0,001 | melhor que sem correção |

### Por origem (perda logarítmica)

| Origem | Jogos | Sem correção | Principal | Frequência simples |
|---|---:|---:|---:|---:|
| Seleções: Elo | 239 | 0,8656 | 0,8717 | 1,0685 |
| Frequência simples (poucos jogos) | 2617 | 1,0731 | 1,0712 | 1,0731 |
| Clubes: força histórica (Poisson) | 12884 | 1,0705 | 1,0390 | 1,0560 |

## Curva de calibração (quando o app diz X%, quanto acontece)

Entre parênteses, quantos percentuais caíram na faixa em cada versão.

| Faixa prevista | Sem correção: previsto → observado | Corrigida: previsto → observado |
|---|---|---|
| 0% a 10% | 7,2% → 15,2% (1548) | 6,8% → 12,5% (96) |
| 10% a 20% | 16,0% → 22,6% (10211) | 17,5% → 16,5% (2137) |
| 20% a 30% | 24,3% → 28,4% (18237) | 26,0% → 26,2% (26654) |
| 30% a 40% | 34,2% → 34,6% (1976) | 33,7% → 34,2% (3686) |
| 40% a 50% | 46,9% → 41,2% (4181) | 45,8% → 44,5% (9422) |
| 50% a 60% | 54,9% → 45,0% (4869) | 53,7% → 54,7% (4585) |
| 60% a 70% | 64,5% → 52,5% (4061) | 63,3% → 63,2% (524) |
| 70% a 80% | 74,0% → 58,6% (1702) | 73,2% → 77,6% (85) |
| 80% a 90% | 83,9% → 67,7% (381) | 84,0% → 80,0% (25) |
| 90% a 100% | 93,2% → 72,2% (54) | 94,9% → 100,0% (6) |

## O que importa: a chance do bilhete contra o que aconteceu

Mesmos bilhetes nas duas contas; só a chance muda. Valores somados nos concursos avaliados. O intervalo é a faixa de 95% em que o número de concursos premiados deveria cair se a conta estivesse certa.

| Bilhete | Concursos | Fez 13 ou mais | Conta sem correção | Conta corrigida | Fez 14 | Sem correção | Corrigida |
|---|---:|---:|---|---|---:|---|---|
| 1 duplo, pela regra (2 apostas) | 982 | **0** | 8,6 (2,9 a 14,3) | 1,1 (0,0 a 3,1) | **0** | 0,9 (0,0 a 2,7) | 0,1 (0,0 a 0,6) |
| 1 triplo, pela regra (3 apostas) | 982 | **1** | 11,1 (4,6 a 17,6) | 1,5 (0,0 a 3,8) | **0** | 1,2 (0,0 a 3,3) | 0,1 (0,0 a 0,7) |
| 3 duplos, pela regra (8 apostas) | 982 | **1** | 17,7 (9,6 a 25,9) | 2,6 (0,0 a 5,8) | **0** | 2,1 (0,0 a 4,9) | 0,2 (0,0 a 1,1) |
| 2 duplos e 1 triplo, pela regra (12 apostas) | 982 | **2** | 22,9 (13,7 a 32,1) | 3,6 (0,0 a 7,2) | **0** | 2,8 (0,0 a 6,1) | 0,3 (0,0 a 1,4) |
| 5 duplos e 3 triplos, pela regra (864 apostas) | 982 | **44** | 143,7 (122,4 a 165,1) | 41,6 (29,3 a 54,0) | **8** | 28,4 (18,2 a 38,6) | 5,4 (0,9 a 10,0) |
| 1 duplo, sorteado (2 apostas) | 982 | **0** | 0,0 (0,0 a 0,2) | 0,0 (0,0 a 0,2) | **0** | 0,0 (0,0 a 0,0) | 0,0 (0,0 a 0,0) |
| 3 duplos, sorteado (8 apostas) | 982 | **0** | 0,0 (0,0 a 0,4) | 0,0 (0,0 a 0,4) | **0** | 0,0 (0,0 a 0,1) | 0,0 (0,0 a 0,1) |
| 2 duplos e 1 triplo, sorteado (12 apostas) | 982 | **0** | 0,1 (0,0 a 0,6) | 0,1 (0,0 a 0,5) | **0** | 0,0 (0,0 a 0,1) | 0,0 (0,0 a 0,1) |

## Conferência da suposição de jogos independentes

Com o bilhete de um duplo pela regra: número de concursos com pelo menos k acertos, esperado pela conta e observado.

| k acertos ou mais | Esperado sem correção | Esperado corrigido | Observado |
|---:|---:|---:|---:|
| 10 | 272,9 | 95,5 | **93** |
| 11 | 123,6 | 31,4 | **29** |
| 12 | 40,6 | 7,3 | **6** |
| 13 | 8,6 | 1,1 | **0** |
| 14 | 0,9 | 0,1 | **0** |

## Como ler
- A conta do bilhete está certa quando o número de concursos premiados cai dentro do intervalo. Fora dele, a chance mostrada engana.
- Expoente abaixo de 1 com mistura perto de 1 significa que os percentuais daquela origem têm informação, mas exagerada: a correção achata, quase sem recorrer à frequência simples. Mistura perto de 0 significaria o contrário: percentual sem informação além da frequência.
- Compare, na tabela por origem, a coluna Principal com a Frequência simples: é ali que se vê se a origem, depois de corrigida, supera a frequência.
- O ajuste de notícias não entra aqui (não há histórico); ele continua aplicado por cima do percentual, limitado a 8 pontos.
- Jogos entre seleções antes de 2010 e os não casados com a base aberta seguem o modelo histórico, como no teste do Elo.

## Reprodução
`.venv\Scripts\python scripts\estudo_calibracao.py` (só lê `loteca.db` e a base aberta das seleções; parâmetros em `config.CALIBRACAO_*`).

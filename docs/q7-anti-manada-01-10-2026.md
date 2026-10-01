# Q7 — Estudo anti-manada (01/10/2026)

> Descreve o passado. Não diz o que vai acontecer em um concurso futuro e não recomenda marcar zebra. Loteria é jogo de azar regulado; nenhum padrão aqui garante prêmio.

## Pergunta
Quando o resultado do concurso se afasta do que a maioria marca (mais jogos fora da coluna 1), há menos ganhadores de 14 acertos, e portanto prêmio menos dividido? A conta anterior do projeto (correlação de -0,13) não descontava a arrecadação nem a época.

## Base e método
- **837** concursos úteis, de 2009 a 2026. Ficaram de fora: 11 sem os 14 jogos apurados (formato antigo de 13 jogos ou concurso ainda aberto); 92 com jogo decidido por sorteio (o resultado não saiu do jogo); 333 sem arrecadação informada (a CAIXA só informa de 2009 em diante).
- Desfecho: ganhadores de 14 acertos por R$ 1 milhão arrecadado (desconta o tamanho do concurso).
- Correlação de Spearman **estratificada por ano**: os postos são calculados dentro de cada ano, para que mudanças de época (arrecadação, hábito dos apostadores) não fabriquem correlação. Anos com menos de 10 concursos úteis ficam fora.
- Valor p por permutação dentro do ano (5000 sorteios); intervalo de 95% por reamostragem de concursos (2000 repetições, com os postos fixos); valor q de Benjamini-Hochberg entre as 3 exposições.

## Resultado

| Exposição | Concursos | Correlação | IC 95% | p | q | Conclusão |
|---|---:|---:|---|---:|---:|---|
| Jogos fora da coluna 1 (empate ou vitória do visitante) | 837 | -0,41 | -0,47 a -0,35 | <0,001 | <0,001 | associação detectada (negativa) |
| Empates | 837 | -0,32 | -0,39 a -0,25 | <0,001 | <0,001 | associação detectada (negativa) |
| Vitórias do visitante | 837 | -0,16 | -0,24 a -0,09 | <0,001 | <0,001 | associação detectada (negativa) |

## Conferência com a conta anterior do projeto
- A conta anterior (**-0,13**) foi reproduzida em 1262 concursos: é a correlação de **Pearson** entre jogos fora da coluna 1 e o número bruto de ganhadores de 14, que pesa muito os poucos concursos com centenas de ganhadores: -0,13. Com os mesmos concursos e a correlação de postos (Spearman), o valor é -0,48. O -0,13 subestimava a relação por causa dos valores extremos, não porque ela fosse fraca.
- Nos 837 concursos úteis, sem estratificar por ano: -0,44 contra o número bruto de ganhadores e -0,44 contra ganhadores por milhão arrecadado. A resposta estratificada da tabela acima fica próxima: a época e o tamanho do concurso explicam pouco da relação.

## Descritivo por faixa de jogos fora da coluna 1

| Jogos fora da coluna 1 | Concursos | Ganhadores de 14 por milhão arrecadado (média) | Sem ganhador de 14 | Prêmio mediano de 14 (onde houve) |
|---|---:|---:|---:|---:|
| 0 a 4 | 43 | 34,35 | 7% | R$ 25.458,15 |
| 5 a 6 | 218 | 34,05 | 27% | R$ 81.639,04 |
| 7 a 8 | 340 | 11,05 | 49% | R$ 220.529,20 |
| 9 a 14 | 236 | 12,52 | 71% | R$ 250.723,70 |

## Como ler
- **Correlação negativa** significa: nos concursos com mais jogos fora da coluna 1, houve menos ganhadores de 14 por milhão arrecadado, comparando concursos do mesmo ano. É associação, não causa.
- **Sem diferença perceptível** não prova que não existe relação: a amostra pode não detectar efeito pequeno. O intervalo mostra o que a amostra ainda admite.
- Mais zebras também aumentam a chance de ninguém acertar os 14, o que acumula o prêmio e não é o mesmo que "prêmio maior para quem acerta". O prêmio de 14 acertos depende da arrecadação, do rateio do manual e dos acúmulos; ver `docs/valores-dos-concursos-30-09-2026.md`.
- A chance de acertar 14 jogos continua muito pequena em qualquer estratégia; este estudo não a altera.

## Reprodução
`.venv\Scripts\python scripts\estudo_anti_manada.py` (só lê `loteca.db`; semente em `config.Q7_SEMENTE`).

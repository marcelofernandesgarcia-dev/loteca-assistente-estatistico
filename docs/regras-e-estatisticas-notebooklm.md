# Regras oficiais e estatísticas da Loteca — achados do NotebookLM

Fonte: notebook NotebookLM do usuário, "Guia Estatístico do Brasileirão Série B e Regras da Loteca" (8 fontes web), lido em 27/09/2026. Estado vivo desta nota fica no cofre Obsidian Cerebro Pessoal (`Loteca/Notas/Regras oficiais e estatísticas (NotebookLM).md`). Cópia de trabalho abaixo.

Conteúdo **gerado por IA (Gemini) a partir de fontes web** escolhidas pelo usuário — entra como pesquisa dele ("informado"), mas não substitui a verificação contra o regulamento oficial da CAIXA e contra os dados reais da API. Números de desempenho de clube são o retrato de uma rodada específica de 2026 — não são constantes, o app precisa calculá-los dinamicamente a partir do histórico, nunca fixá-los no código.

## Fontes do notebook (8)
1. Brasileirão Série B 2026: Raio-X Completo Após a 24ª Rodada — FutDados
2. Como Funciona a Loteca: 14 Jogos, Duplos e Prorrogação — ValorFinal
3. Copa da Loteca 2026: como funciona e como participar — Loteria Aldeota
4. ESTATÍSTICA DO CAMPEONATO BRASILEIRO 2026 — SóEsporte
5. Loteca – Wikipédia, a enciclopédia livre
6. Loterias online Caixa (duas entradas de fonte)
7. Máfia da Loteria Esportiva – Wikipédia, a enciclopédia livre

## Regras oficiais confirmadas (importantes para o cálculo do 1/X/2)
- **Apuração considera só os 90 minutos regulamentares + acréscimos.** Gols de prorrogação ou pênaltis não contam. Mata-mata empatado no tempo normal → coluna vencedora é **X (empate)**, mesmo que um time avance nos pênaltis.
  - **Ação para o importador:** confirmar se `nuGolEquipeUm`/`nuGolEquipeDois` da API da CAIXA já é só tempo regulamentar, ou se em mata-mata pode incluir prorrogação — testar com um concurso conhecido antes de calcular o 1/X/2 automaticamente.
- **Jogo adiado/antecipado/cancelado para fora do período do concurso:** resultado definido por **sorteio público** da CAIXA, não pelo placar real (que pode sair semanas depois e não altera a apuração já feita).
  - **Ação:** aceitar que uma fração do histórico não reflete resultado real de campo — não é erro de dado, é regra do jogo.
- 14 jogos por concurso, 3 colunas por jogo (1 = mandante, X = empate, 2 = visitante).

## Estrutura de premiação (rateio)
| Faixa | Pontos | % do rateio | Probabilidade (aposta mínima) |
|---|---|---|---|
| 1ª | 14 acertos | 70% | 1 em 2.391.485 |
| 2ª | 13 acertos | 10% | 1 em 85.410 |

**Copa da Loteca 2026** (edição especial, concursos 1255 a 1258, 4 sorteios em 13 dias de junho/2026): prêmio estimado de R$ 10 milhões; sem acertador de 14 pontos, o valor migra para a faixa de 13 pontos (sem acumular entre faixas nessa edição).

## Tabela de custos oficiais (aposta mínima R$ 2,00/combinação)
| Marcação | Combinações | Preço oficial |
|---|---|---|
| 14 jogos secos + 1 duplo | 2 | R$ 4,00 (mínimo) |
| 1 triplo | 3 | R$ 6,00 |
| 2 duplos | 4 | R$ 8,00 |
| 1 duplo + 1 triplo | 6 | R$ 12,00 |
| 3 duplos | 8 | R$ 16,00 |
| 2 duplos + 1 triplo | 12 | R$ 24,00 |
| 5 duplos + 3 triplos (máximo) | 864 | R$ 1.728,00 |

A aposta mínima já inclui um duplo grátis (não é 14 jogos secos puro) — útil para validar a calculadora de fechamento de bolão.

## Benchmarks estatísticos citados (Séries A/B, 2026 — ponto no tempo, recalcular sempre)
- Série B: mandante vence 42%, empate 30%, visitante vence 29%. "Ambos marcam" 47%, "Over 2,5 gols" 40%.
- Série A: placar mais repetido foi 2x1 (59 vezes na amostra); médias de 2,67 gols/jogo (Série A) vs 2,27 (Série B).
- Exemplos de "forma" citados (retrato da rodada, não fixar no código): Palmeiras (melhor defesa Série A), Flamengo (melhor ataque), Criciúma (líder Série B), Juventude (74% clean sheets), Ponte Preta (pior defesa), América-MG (crise defensiva), CRB (momentum positivo).

## Contexto histórico/institucional
Loteca existe desde 1970 (antigo nome "Loteria Esportiva"); há registro de escândalo passado ("Máfia da Loteria Esportiva") relevante só para eventual copy institucional do app.

## Nota de responsabilidade
O guia já registra: participação restrita a maiores de 18 anos, capital de recursos não essenciais, sem garantia matemática de retorno — alinhado com o aviso já definido em `README.md`/`CLAUDE.md` deste projeto.

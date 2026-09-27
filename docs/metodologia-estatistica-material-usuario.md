# Metodologia estatística proposta — material do usuário (27/09/2026)

Estado vivo desta nota fica no cofre Obsidian Cerebro Pessoal (`Loteca/Notas/Metodologia estatística proposta (material do usuário).md`). Cópia de trabalho abaixo.

Síntese de um texto colado pelo usuário sobre análise avançada da Loteca. É material externo — entra como "informado", mas com **duas contradições internas** e **um trecho corrompido no que foi colado**, sinalizados abaixo em vez de resolvidos por suposição.

## 1. Combinatória — validado por conta própria
- Total de resultados possíveis para 14 jogos: 3¹⁴ = **4.782.969** (conferido: 3⁷=2.187 → 2.187²=4.782.969).
- Combinações de uma aposta com `d` duplos e `t` triplos: **2^d × 3^t**. Custo = combinações × R$ 2,00.
- Cruza com o achado do NotebookLM: "1 em 2.391.485" para 14 pontos na aposta mínima ≈ 4.782.969 ÷ 2 (aposta mínima já cobre 2 combinações). As duas fontes se confirmam.

## 2. Modelo de "Score" ponderado por time (proposto no texto)
| Fator | Peso |
|---|---|
| Forma recente | 30% |
| Mandante/Visitante | 25% |
| Ataque | 15% |
| Defesa | 15% |
| Confronto direto | 10% |
| Lesões | 5% |

`Score = F×0,30 + M×0,25 + A×0,15 + D×0,15 + C×0,10 + L×0,05`.

## 3. Filtros seco/duplo/triplo — contradição no material colado
- Seção 6 do texto: seco >65%; **duplo 40–55%**; triplo se diferença entre resultados <10%.
- Seção 12 do texto: seco >65%; **duplo 45–65%**; triplo <45%.
Não escolhemos uma das duas — pendência de decisão antes de implementar qualquer filtro automático.

## 4. Modelos de indústria citados (padrão de mercado, não exclusivos deste texto)
- **Poisson:** λ por time a partir de gols marcados/sofridos, usado para estimar chance de vitória/empate/derrota.
- **Elo Rating:** `E = 1 / (1 + 10^((Rb-Ra)/400))` para comparar força relativa entre times.

## 5. Taxa histórica de empates
25–30% dos jogos profissionais terminam empatados — consistente com o benchmark da Série B 2026 (30% de empates) já registrado em `docs/regras-e-estatisticas-notebooklm.md`.

## 6. Fatores citados (ajudam / prejudicam)
Ajudam: mando de campo, forma recente, lesões, suspensões, motivação, odds de mercado, xG. Prejudicam: aposta emocional, seguir só a tabela, ignorar empates, ignorar Série B, ignorar contexto do campeonato.

## 7. Checklist de dados por jogo
Últimos 10/5 jogos, desempenho casa/fora, gols pró/contra, saldo de gols, xG, lesões, suspensões, odds, histórico direto, motivação, necessidade de pontuar, calendário/desgaste.

## 8. Modelo híbrido "recomendado" — depende de fonte que ainda não temos
Pesos: odds das casas de apostas 40%, forma recente 25%, mando de campo 15%, gols marcados/sofridos 10%, histórico do confronto 10%.
- Conflito com a seção 2: modelo diferente do "Score" ponderado (sem odds de mercado, com peso a lesões).
- Gap de dados: "odds de mercado" pressupõe uma fonte (casa de apostas/agregador) ainda não pesquisada nem decidida neste projeto.

## 9. Trecho corrompido no material colado
Entre a seção de duplos/triplos e "Defesa" o texto perdeu conteúdo (formulas/imagens que não coladas como texto) — não preenchido por suposição.

## Decisão que este material força
Não implementar nenhum dos filtros/pesos como está — contradições internas e dependência de dado (odds de mercado) fora do escopo decidido (fonte única = endpoint da CAIXA). Ver pendências em `README.md`/cofre.

# Manual de Produtos das Loterias CAIXA v21 — fonte oficial (seção Loteca)

Estado vivo no cofre Obsidian (`Loteca/Notas/Manual de Produtos das Loterias CAIXA v21 (fonte oficial).md`). Cópia de trabalho abaixo.

Fonte: documento oficial da CAIXA fornecido pelo usuário, "Manual de Produtos das Loterias CAIXA", versão 21 (Circular CAIXA nº 1.123/2026, agosto/2026, 102 páginas), também público em caixa.gov.br. É o documento que a Carta de Serviços cita como consolidador de toda a regulação — a fonte mais autorizada lida neste projeto. Cópia salva em `docs/fontes-oficiais/MANUAL_DE_PRODUTOS_v21.pdf`.

## Base legal completa da Loteca — confirma o decreto que faltava
"[Loteca/Lotogol] regulamentados pelo **Decreto n.º 66.118/1970**, e pela Norma Geral dos concursos de Prognósticos Esportivos, baixada pela **Portaria MF n.º 356/1987** (alterada pela **Portaria MF n.º 151/1989**) e pela **Lei n.º 13.756/2018**."

Confirma o Decreto nº 66.118/1970 que antes eu tinha marcado como "não encontrado" (não estava na Carta de Serviços, mas é real). Também explica de onde vêm os anos 1987/1989 citados pelo NotebookLM: são portarias regulatórias gerais, **não** uma mudança no número de jogos — a história "13→16→13 jogos, 'A Gorda'" continua sem confirmação oficial.

## Contradição entre dois documentos oficiais da CAIXA (mesmo mês)
- Manual de Produtos (glossário): "Loteca - modalidade criada pela CAIXA **em 1970**."
- Carta de Serviços (linha do tempo): "**2001** - Lançamento da Loteca e Lotogol."

Registrado como contradição não resolvida, não escolhida por conta própria.

## Estrutura oficial da aposta
Simples/Duplo/Triplo confirmados; aposta mínima = 1 duplo (2 apostas, R$4,00); aposta máxima = 864 apostas (5 duplos + 3 triplos); só 13 ou 14 acertos premiam.

## Tabela oficial de preços do Bolão (Anexo I)
Todas as combinações de 0-6 triplos × 0-9 duplos, com apostas/valor/cotas — salva em `data/loteca-boloes-oficial.csv`. Fórmula `2^duplos × 3^triplos × R$2,00` validada contra 100% das linhas da tabela oficial.

## Distribuição oficial da arrecadação (mais completa que antes)
Prêmio Bruto = 55% da arrecadação total. Dentro dele: 1ª faixa (14 pts) 70%, 2ª faixa (13 pts) 10%, 3ª faixa 10% (acumula para concursos de "final zero/cinco" — ligado ao último algarismo do número do concurso), 4ª faixa 10% (acumula para a Loteca Especial). **Loteca Especial tem divisão própria: 90%/10%**, diferente do concurso regular.

## Regras de apuração — mais detalhadas
Prorrogação não conta, exceto quando usada para compensar interrupção no próprio tempo normal. Partida suspensa após iniciada: vale o placar no momento da suspensão. Decisão judicial posterior não altera resultado já apurado. Jogo antecipado/atrasado fora da janela do concurso: sorteio.

## Possíveis erros no próprio documento (sinalizados, não resolvidos)
- Tabela de chance de acerto mostra "R$3,00" no cabeçalho onde a tabela de preços oficial (e o Anexo I) dizem R$4,00 — provável erro de copiar/colar da seção da Quina.
- Item 6.3.3.9 diz que a Loteca tem Bolão eletrônico; item 6.4.1.2 não a lista entre as modalidades com Bolão eletrônico. Contradição interna.

## Achado que pode invalidar dado usado antes
Página 4, "Alterações em relação à versão anterior": mudança do dia de sorteio de sábado para domingo "em todo o documento" — o prazo "14h de sábado" citado antes por outras fontes pode estar desatualizado. Não usar sem reconfirmar.

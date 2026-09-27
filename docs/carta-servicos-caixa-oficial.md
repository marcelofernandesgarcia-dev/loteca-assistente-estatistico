# Carta de Serviços ao Usuário — CAIXA Loterias (fonte oficial, agosto/2026)

Estado vivo no cofre Obsidian (`Loteca/Notas/Carta de Serviços ao Usuário - CAIXA (fonte oficial).md`). Cópia de trabalho abaixo.

Fonte: documento oficial da CAIXA, https://www.caixa.gov.br/Downloads/loterias-carta-servicos-cidadao/Carta_de_servicos_cidadao.pdf (agosto/2026, 28 páginas), baixado e lido diretamente. Cópia guardada em `docs/fontes-oficiais/Carta_de_servicos_cidadao_CAIXA_2026-08.pdf` para referência (documento público). Primeiro documento realmente oficial (não sintetizado por IA) lido neste projeto — onde conflita com o NotebookLM, esta Carta prevalece.

## Base normativa oficial (confirmada)
- Decreto-Lei nº 204/1967 — exploração de loterias (marco geral).
- **Decreto-Lei nº 594, de 27/05/1969 — institui a Loteria Esportiva Federal.** Confirma o número já citado pelo NotebookLM.
- Lei nº 13.756/2018 — revoga dispositivos dos Decretos-Leis 204/1967 e 594/1969; trata da modalidade "apostas de quota fixa" (categoria da Loteca).
- **Não encontrado nesta lista oficial:** "Decreto nº 66.118/1970" que o NotebookLM tinha citado como regulamentador. Não é prova de inexistência, mas não posso mais tratá-lo como verificado — status: não confirmado em fonte oficial.

## Correção sobre a história da Loteca
Linha do tempo oficial (página 3): 1970 = "Surge o 1º concurso ligado ao futebol: Loteria Esportiva"; **2001 = "Lançamento da Loteca e Lotogol"**. Isso não bate com a narrativa do NotebookLM (13→16 jogos em 1987 "A Gorda" → volta a 13 em 1989, quando o nome "Loteca" teria sido adotado) — a Carta oficial não menciona 1987/1989 nem essa evolução de número de jogos. Não reconciliei as duas versões — fica em aberto. **Para qualquer texto público do app, usar só a data oficial (Loteca lançada em 2001) e evitar repetir 1987/1989 sem confirmação em outra fonte oficial.**

## Confirmações oficiais úteis
- Aposta mínima/simples da Loteca: **R$ 4,00** — bate com o que já tínhamos.
- 14 jogos por concurso, prêmio para 13 ou 14 acertos — confirmado.
- Concursos semanais; existe também o "Concurso da Loteca Especial" (anual ou conforme calendário esportivo) — provavelmente o termo oficial para o que o NotebookLM chamou de "Copa da Loteca 2026".
- **Regra de pagamento específica da Loteca:** prazo de pagamento conta a partir do dia útil seguinte à **apuração** (não ao sorteio, diferente das outras loterias) — confirma que o campo `dataApuracao` da API da CAIXA é o conceito regulatório certo a usar como data de referência do concurso.
- Loteca não está disponível no Internet Banking CAIXA (só Mega-Sena) — só lotérica, Portal Loterias Online e App.
- Bolão CAIXA oficial (produto da CAIXA, diferente do "fechamento" matemático): tarifa de serviço de até 35% sobre o valor da cota.
- **Jogo responsável:** CAIXA Loterias tem certificação **Nível 3 de 4** no Responsible Gaming Framework da World Lottery Association (WLA) — referência oficial forte para o aviso de responsabilidade do app.

## Impacto no projeto
Nenhuma mudança na fonte de dados nem no benchmark estatístico. Duas pendências novas: não repetir a narrativa histórica não confirmada (1987/1989/"A Gorda"); tratar o Decreto nº 66.118/1970 como não confirmado. Uma pendência resolvida: Decreto-Lei nº 594/1969 confirmado oficialmente.

# Pesquisa de fontes de dados

Estado vivo desta decisão fica no cofre Obsidian Cerebro Pessoal (`Loteca/Notas/Pesquisa de fontes de dados.md`). Cópia de trabalho abaixo.

## Decisão preliminar (27/09/2026) — testado na prática

O endpoint não-oficial usado pelo próprio site da CAIXA (`https://servicebus2.caixa.gov.br/portaldeloterias/api/loteca` e `/loteca/<numero-do-concurso>`) foi testado direto:

- **Concurso atual:** `.../loteca` sem sufixo retorna o concurso vigente (testado: nº 1271, 14 jogos, resultado ainda em aberto).
- **Concurso específico/histórico:** `.../loteca/<numero>` funciona desde o concurso mais antigo. Testado concurso 1 (18/02/2002) e 1270 — ambos responderam 200 com os 14 jogos, placares (`nuGolEquipeUm`/`nuGolEquipeDois`) e data.
- **Achado importante:** o campo `resultado` de cada jogo vem `null` mesmo em concursos já encerrados com placar definido — o 1 (casa) / X (empate) / 2 (visitante) **precisa ser calculado por nós** a partir do placar, não vem pronto.
- **Achado importante 2 — a Loteca não é só futebol brasileiro:** concursos testados incluem jogos de Série A, Série B (ex.: Remo, Londrina no concurso 1271) **e também ligas estrangeiras** (La Liga, Premier League, Serie A italiana, no concurso 1270). Uma API só de futebol brasileiro não cobriria o concurso inteiro.

### Implicação para a arquitetura
O próprio endpoint da CAIXA já devolve todos os jogos do concurso com placar final — a base histórica de frequência 1/X/2 e a "forma" de cada time podem ser construídas só com os dados desse endpoint, sem depender de API externa de estatística de futebol.

- Vantagem: uma fonte só, sem custo, sem dependência de terceiro para o dado principal.
- Risco aceito: endpoint não-documentado oficialmente pela CAIXA — pode mudar de formato ou ficar instável sem aviso. Mitigar guardando cópia própria do histórico (banco local) assim que importado.
- Cuidado operacional: a API da CAIXA recusa muitas requisições em sequência rápida — importador de histórico precisa de espaçamento entre chamadas (ex.: ~700ms) e paralelismo baixo (2–3 requisições simultâneas no máximo).

### Ainda em aberto
- Fonte externa (lesões, escalação, posição na tabela) só entraria depois, se o usuário quiser enriquecer a forma do time — não é bloqueio para a v1.
- Decidir se a base histórica completa (concurso 1 ao atual, ~1271 concursos × 14 jogos ≈ 17.800 jogos) é importada de uma vez ou de forma incremental.

## Levantamento original (busca web, não verificado) — mantido como referência
- Projetos de terceiros com propósito parecido: `guidi/loteria_api`, `dantetesta/LotoLogic`, `rockcavera/nim-lotcef`, pacote PyPI `loteria-caixa`, `guto-alves/loterias-api`, `fabriciocovalesci/loterias-caixa-api`.
- APIs de futebol brasileiro consideradas e descartadas da v1 após o achado acima: API Futebol, `campeonato-brasileiro-api`, `api-futebol-brasileiro`, Base dos Dados.

# Dados

## loteca-historico-valorfinal.csv

Histórico de resultados 1/X/2 da Loteca, concurso 1 (18/02/2002) ao 1271, com 10 concursos ausentes e documentados (244, 245, 393, 727, 770, 778, 779, 780, 781, 786).

- **Fonte:** [ValorFinal — Histórico da Loteca em CSV e JSON](https://valorfinal.com.br/dados/loteria-loteca), dado primário Caixa Econômica Federal.
- **Licença:** Creative Commons BY 4.0 (uso, cópia, redistribuição e trabalho derivado livres, com citação).
- **Baixado em:** 27/09/2026. **Data-base do arquivo:** 21/09/2026.
- **Integridade:** SHA-256 do conteúdo versionado (fim de linha LF, `.gitattributes`) — `7553a22c2f748a6df01108cd2b9ee4a285cdf6dcfbfb9d3ce3faa8b6a3dc6ba5` — conferido contra o hash publicado pela ValorFinal no momento do download (que era `b1794ca3...`, da cópia local com fim de linha CRLF do Windows; achado e corrigido em 29/09/2026, ver `docs/parecer-tecnico-28-09-2026.md`). Os dois hashes são o MESMO arquivo, só com fim de linha diferente -- não há divergência de conteúdo.
- **Formato:** `concurso;data;resultados` — `resultados` é uma string de 14 caracteres (`1`=mandante, `X`=empate, `2`=visitante), um por jogo.
- **Limitação:** não traz nome de time nem placar — só a coluna vencedora. Para dado por clube, a fonte é o endpoint da CAIXA (ver `docs/pesquisa-fontes-dados.md`).
- **Validação feita:** recontagem própria dos caracteres do arquivo deu 47,25% / 26,20% / 26,55% (Coluna 1/X/2), consistente com o benchmark histórico oficial levantado no NotebookLM (47,23%/26,15%/26,62% sobre a base completa de 1.271 concursos) — a diferença é exatamente os 10 concursos ausentes deste arquivo.

Como citar (fornecido pela própria ValorFinal): ValorFinal. Histórico da Loteca hoje: 1.261 concursos, de 18 de fevereiro de 2002 a 21 de setembro de 2026. Disponível em: https://valorfinal.com.br/dados/loteria-loteca. Fonte do dado: Caixa Econômica Federal - Loterias. Dados de: 21/09/2026.

# Pesquisa de fontes de dados (27/09/2026)

Levantamento inicial via busca web. **Nenhuma fonte abaixo foi verificada em uso real** (disponibilidade, limites de taxa, licença de uso, estabilidade). Antes de adotar qualquer uma, testar o endpoint/pacote e checar termos de uso.

## Concursos e resultados oficiais da Loteca

- Endpoint não-oficial usado pelo próprio site da CAIXA: `https://servicebus2.caixa.gov.br/portaldeloterias/api/loteca` (e `/loteca/<numero-do-concurso>` para um concurso específico). Não documentado oficialmente pela CAIXA; usado por vários projetos de terceiros. Retorna JSON com os jogos do concurso e, quando encerrado, o resultado. Risco: pode mudar ou ser bloqueado sem aviso, por não ser API pública oficial.
- Projetos de terceiros que já envolvem essa API/dados históricos da Loteca:
  - [guidi/loteria_api](https://github.com/guidi/loteria_api) — API própria, com endpoint documentado em `https://api.guidi.dev.br/loteria` (endpoint específico da Loteca não confirmado ainda — retornou 404 na primeira tentativa, precisa investigar a rota certa).
  - [dantetesta/LotoLogic](https://github.com/dantetesta/LotoLogic) — aplicativo desktop com histórico de mais de 23 mil concursos (todas as loterias CAIXA), exporta CSV.
  - [rockcavera/nim-lotcef](https://github.com/rockcavera/nim-lotcef) — baixa resultados diretamente do site da CEF.
  - [PyPI: loteria-caixa](https://pypi.org/project/loteria-caixa/) — pacote Python.
  - [guto-alves/loterias-api](https://github.com/guto-alves/loterias-api) e [fabriciocovalesci/loterias-caixa-api](https://github.com/fabriciocovalesci/loterias-caixa-api) — outras APIs de terceiros com o mesmo propósito.

## Desempenho/estatística dos clubes (futebol brasileiro)

- [API Futebol](https://www.api-futebol.com.br/) — base `https://api.api-futebol.com.br/v1`, cobre Brasileirão Série A/B, Copa do Brasil e outras competições regionais. Precisa checar plano gratuito x pago.
- [ezefranca/campeonato-brasileiro-api](https://github.com/ezefranca/campeonato-brasileiro-api) — API aberta com tabela, gols, cartões e forma recente do Brasileirão.
- [kariofreire/api-futebol-brasileiro](https://github.com/kariofreire/api-futebol-brasileiro) — Brasileirão, Libertadores, Sul-Americana, Copa do Brasil.
- [Base dos Dados — Campeonatos de Futebol](https://basedosdados.org/dataset/c861330e-bca2-474d-9073-bc70744a1b23) — dataset público (BigQuery) com Série A desde 2003, gols, estádio, árbitro, técnicos.

## Lacuna a resolver

A Loteca inclui jogos de Série A, B, C e D e às vezes outras competições — nenhuma fonte acima confirmadamente cobre as quatro séries com atualização automática por concurso. Precisa validar cobertura antes de decidir a arquitetura de ingestão de dados.

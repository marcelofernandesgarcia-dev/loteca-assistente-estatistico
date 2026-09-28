# Plano — Fase 2: Painel do time (aprovado em 27/09/2026)

Cópia permanente da Fase 2 do plano aprovado via Claude Code (Plan Mode). A Fase 1 está em `docs/plano-app-v1-aprovado.md`. Original da ferramenta: `C:\Users\marce\.claude\plans\velvety-toasting-squid.md` (pasta interna, pode ser limpa).

## Contexto

A v1 já estava implementada e ajustada (até o commit `a6fe588`): importador, banco, `stats/` completo, camada `externo/` de notícias, e a página "Concurso atual" com os 3 cards (resultado real, percentual histórico, bilhete interativo) — **mantidos como estão, sem alteração nesta fase**.

O usuário trouxe 3 imagens de referência (app "SportX", dashboard Power BI "EPL Season Analysis", dashboard Power BI brasileiro "Futebol Analytics") e um link do Instagram, pedindo melhorar o **acompanhamento por time**. O link do Instagram não foi possível abrir (rede social, sem sessão logada) — o plano usa só as 3 imagens.

## Diagnóstico — viável x não viável com o dado que temos

Nosso dado é só o placar final de cada jogo da Loteca (`jogos`: gols_casa, gols_fora, resultado, data_jogo, campeonato). Não há escalação, cartão, gol por jogador nem evento ao vivo.

**Viável:** aproveitamento casa x fora; contagem por resultado (V/E/D com %); cartão de KPIs; tendência por ano (barra + linha); tabela de jogos filtrável com total; insight de texto gerado por regra (não IA).

**Não viável (exigiria fonte de dado que não temos):** estatística de jogador (artilheiros, assistências, cartões, defesas); "Attack Momentum"/ticker ao vivo; tabela de classificação oficial de campeonato — nossa base só tem os jogos que caíram na grade da Loteca, então uma "classificação" seria incompleta e enganosa. A seção se chama **"Desempenho na Loteca"**, nunca "Classificação".

## O que mudou — só a página "Por time"

Filtros (ano, campeonato, mando) → KPIs → leitura rápida (insight por regra) → gauges de aproveitamento casa x fora → barra empilhada de resultados → tendência por ano → tabela detalhada com total → seções que já existiam (forma recente, desempenho no ano, fatores externos).

Novo módulo puro e testado `stats/desempenho.py`: `aproveitamento_casa_fora`, `contagem_por_resultado`, `kpis`, `tendencia_por_ano`, `gerar_insight`. Dependência nova: `plotly` (MIT, instalado via pip).

## Fora do escopo (reafirmado)
Estatística de jogador, eventos ao vivo/momentum, classificação oficial de campeonato.

## Verificação executada
34 testes automatizados passando (10 novos em `tests/test_desempenho.py`); verificação visual no Streamlit (gauges, barra de resultados, gráfico de tendência renderizando); dado-a-dado conferido para um time de amostra grande (Flamengo: 28 jogos, 17V 6E 5D, consistente com o card "Seu bilhete").

## Limitação conhecida
O gráfico de tendência por ano só terá mais de um ponto depois da importação histórica completa (hoje só estão importados os concursos 1225–1271, todos de 2026).

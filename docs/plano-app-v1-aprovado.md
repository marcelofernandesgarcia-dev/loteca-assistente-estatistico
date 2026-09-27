# Plano — App local de acompanhamento estatístico da Loteca (aprovado em 27/09/2026)

Cópia permanente do plano aprovado pelo usuário via Claude Code (Plan Mode). Original ficava só em `C:\Users\marce\.claude\plans\velvety-toasting-squid.md` — pasta de ferramenta, não do projeto; copiado aqui para não se perder se aquela pasta for limpa. Implementação: commit `97506a4`.

## Contexto

Todo o projeto até aqui foi só pesquisa e registro (repositório `loteca-assistente-estatistico`, sem código de produto): decidimos a fonte de dados (endpoint não-oficial da CAIXA, testado do concurso 1 ao 1271), lemos duas fontes oficiais (Carta de Serviços, Manual de Produtos v21) e um dataset aberto (ValorFinal), validamos a combinatória e a tabela de preços do Bolão contra a fonte oficial, e confirmamos ao vivo que a grade da Loteca mistura clubes brasileiros com **seleções nacionais** (concurso 1272: Inglaterra x Espanha, Alemanha x Grécia etc.) — isso muda o modelo de dados.

O usuário pediu um **aplicativo instalado localmente** para acompanhar informação, estatística, resultado e resultado acumulado de todos os participantes, com visualização por time e por concurso. Na revisão deste plano, o usuário pediu duas adições importantes, já incorporadas abaixo:
1. Uma **coluna de percentual de possível vitória** por participante em cada jogo, baseada no histórico já analisado.
2. Uma **categoria de análise de desempenho externa** — notícias, comentário de analistas/jornalistas ligados a cada participante — coletada por **varredura automática semanal, na antevéspera (2 dias antes) do prazo de cada concurso**, e que **ajusta automaticamente** o percentual histórico.

**Objetivo declarado pelo usuário, que rege todo o projeto:** por se tratar de jogo de azar, o aplicativo existe para **fortalecer a análise e reduzir risco e erro na escolha do apostador** — nunca para prometer ou garantir resultado.

## Arquitetura proposta

**Stack: Python + SQLite + Streamlit**, executado localmente. A lógica de negócio fica em módulos Python puros e testáveis, independentes da UI.

```
importer/        -> cliente da API da CAIXA, rate-limited, incremental
stats/           -> frequência 1/X/2, forma do time, percentual histórico, fechamento de bolão
externo/         -> varredura semanal de notícias/análises e cálculo do ajuste
app/             -> páginas Streamlit (consomem stats/externo, sem lógica própria)
tests/           -> pytest para as funções de stats/importer/externo
scripts/         -> tarefa agendada (varredura semanal) para o Agendador de Tarefas do Windows
loteca.db        -> banco SQLite local (gerado, fora do git)
```

## Modelo de dados (SQLite)

- `concursos`, `participantes` (com tipo `clube`/`selecao`), `jogos` (com `situacao` `normal`/`suspenso`/`sorteio`), `premiacoes`, `percentuais` (histórico + ajuste + final), `fatores_externos` (log da varredura).

## Camada de análise externa — a adição desta revisão

Uma tarefa agendada roda uma vez por semana, dois dias antes do prazo de aposta do próximo concurso. Para cada participante: busca na web, extrai sinais estruturados (lesão, suspensão, tendência de imprensa), aplica um ajuste máximo pré-definido e limitado (teto total, ex. ±8 pontos), soma ao percentual histórico. Log completo em `fatores_externos` para auditoria.

## Visualização (Streamlit, 4 páginas)

Concurso atual · Por concurso · Por time · Fechamento de bolão — ver detalhe completo no histórico do commit ou na versão original do plano.

## Fora do escopo da v1
Odds de mercado; enriquecimento adicional (escalação oficial, xG de provedor externo); suporte a Lotogol.

## Verificação
`pytest` para as funções puras; teste de integração leve contra a API real; verificação visual com `streamlit run` e dado real — todos executados na entrega, ver `README.md`.

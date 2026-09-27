# Loteca — Assistente Estatístico

Aplicativo web pessoal para monitoramento e análise estatística da Loteca (loteria esportiva de prognóstico da CAIXA — resultado 1/X/2 em 14 jogos por concurso), pensado para uso numa lotérica.

Projeto pessoal, sem vínculo institucional. Ver `CLAUDE.md`.

## Escopo definido com o usuário (27/09/2026)

- **Uso:** aplicativo de monitoramento e análise estatística — não é uma ferramenta de "palpite", e sim de orientação baseada em probabilidade e no histórico de cada clube participante.
- **Método:** acompanhamento automático de cada clube do concurso (não só do resultado final da loteria), construindo uma base de dados própria para as análises.
- **Entregas estatísticas esperadas:**
  - Frequência histórica de 1 (casa) / X (empate) / 2 (visitante) por concurso e por clube.
  - Desempenho/forma recente dos times (dados externos de futebol).
  - Fechamento de bolão/combinações dentro de orçamento.
  - Sugestões de melhoria sobre as bases já marcadas pelo usuário.
- **Plataforma:** aplicativo web (site/painel), acessível de qualquer computador ou tablet do balcão da lotérica.
- **Fonte de dados dos concursos:** decidida e testada — endpoint não-oficial da CAIXA, ver `docs/pesquisa-fontes-dados.md`.

## Status atual

Planejamento. Fonte de dados fechada para a v1 (endpoint da CAIXA cobre concurso atual e histórico completo desde 2002, sem precisar de API externa de futebol). Regulamento oficial e benchmarks estatísticos levantados — ver `docs/regras-e-estatisticas-notebooklm.md`. Metodologia estatística de referência analisada, com pendências de decisão (filtros seco/duplo/triplo e uso ou não de odds de mercado) — ver `docs/metodologia-estatistica-material-usuario.md`. Arquitetura, stack e modelo estatístico final ainda não desenhados.

## Aviso importante

Loteca é loteria regulada pela CAIXA — jogo de azar. As análises deste projeto são estatística histórica e probabilidade, nunca previsão garantida de resultado. Qualquer interface construída a partir daqui deve deixar isso explícito ao usuário final.

## Próximos passos

Ver `Notas`/pendências no cofre Obsidian Cerebro Pessoal (`Loteca/02 - Pendências.md`) para a lista viva de decisões pendentes.

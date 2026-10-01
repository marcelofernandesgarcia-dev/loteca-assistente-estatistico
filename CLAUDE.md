# Loteca — Assistente Estatístico

Projeto pessoal de análise estatística para apostas na Loteca (loteria esportiva da CAIXA), pensado para uso numa lotérica. Não é sistema de governo: o padrão gov.br, a Conta gov.br e o e-PING **não se aplicam** aqui. Continuam valendo boas práticas de segurança, LGPD (nenhum dado pessoal de apostador é necessário para as análises) e qualidade de código.

> Este aplicativo é feito por mim, como atividade pessoal/comercial ligada a uma lotérica, sem vínculo com meu cargo público no MGI. Nenhum dado, sistema, marca ou conta institucional entra neste projeto.

## Natureza das análises
O assistente entrega estatística e probabilidade histórica (frequência de 1/X/2, forma dos clubes, fechamento de bolão). Ele **não prevê resultados** e não deve ser apresentado ao usuário final como garantia de acerto — loteria é jogo de azar regulado. Qualquer texto de interface deve deixar isso claro.

## Cofre de registro
Decisões de arquitetura, pesquisa de fontes de dados e estado do projeto ficam no cofre Obsidian **Cerebro Pessoal**, área `Loteca/` (`C:\Users\marce\Cerebro Pessoal\Loteca\`). Ler o `00 - Estado Atual.md` daquela área no início de qualquer sessão futura.

## Status (atualizado em 01/10/2026)
App local funcionando (Python + SQLite + Streamlit), 9 páginas, aberto pelo atalho da Área de Trabalho. Principais blocos: importadores (CAIXA, CBF, seleções), percentual por jogo em três camadas (modelo, calibração e ajuste de notícias), volante com análise do palpite, versões e bilhetes salvos, **chances matemáticas por bilhete e por conjunto de bilhetes** do concurso, painel comparativo, premiações e a página "Estudos estatísticos". Ver `README.md` para instalação, uso e a lista de módulos.

Regras que governam as evoluções (decididas com o usuário):
- **Régua única:** um modelo só substitui outro se tiver perda logarítmica menor fora da amostra, em teste pareado, com correção para vários testes. Critérios fixados antes de ver o resultado.
- **Percentual calibrado:** clubes e frequência simples são corrigidos (tabela `calibracao`, refeita por `scripts/atualizar_tudo.py`); o Elo das seleções não. Interruptor: `LOTECA_CALIBRACAO=0`.
- **Sugestão do app:** no máximo um duplo ou um triplo. A chance, porém, é calculada para qualquer marcação do usuário.
- **Sem promessa:** estimativas, nunca garantia; o app não calcula prêmio em reais.
- Cada solicitação e cada estudo ficam registrados em `docs/` e no cofre; resultado descartado por erro de método fica registrado, não apagado.

Os testes (`.venv\Scripts\pytest tests/`) passam em 622 casos. O estado vivo, as pendências e as decisões em aberto ficam no cofre (`Loteca/00 - Estado Atual.md` e `02 - Pendências.md`).

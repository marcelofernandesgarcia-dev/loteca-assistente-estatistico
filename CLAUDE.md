# Loteca — Assistente Estatístico

Projeto pessoal de análise estatística para apostas na Loteca (loteria esportiva da CAIXA), pensado para uso numa lotérica. Não é sistema de governo: o padrão gov.br, a Conta gov.br e o e-PING **não se aplicam** aqui. Continuam valendo boas práticas de segurança, LGPD (nenhum dado pessoal de apostador é necessário para as análises) e qualidade de código.

> Este aplicativo é feito por mim, como atividade pessoal/comercial ligada a uma lotérica, sem vínculo com meu cargo público no MGI. Nenhum dado, sistema, marca ou conta institucional entra neste projeto.

## Natureza das análises
O assistente entrega estatística e probabilidade histórica (frequência de 1/X/2, forma dos clubes, fechamento de bolão). Ele **não prevê resultados** e não deve ser apresentado ao usuário final como garantia de acerto — loteria é jogo de azar regulado. Qualquer texto de interface deve deixar isso claro.

## Cofre de registro
Decisões de arquitetura, pesquisa de fontes de dados e estado do projeto ficam no cofre Obsidian **Cerebro Pessoal**, área `Loteca/` (`C:\Users\marce\Cerebro Pessoal\Loteca\`). Ler o `00 - Estado Atual.md` daquela área no início de qualquer sessão futura.

## Status
App local v1 funcionando (Python + SQLite + Streamlit): importador da CAIXA, motor estatístico (frequência, forma, percentual Poisson, fechamento de bolão) e camada de ajuste externo por notícias, com 4 páginas de visualização. Ver `README.md` para instalação/uso e o plano completo em `C:\Users\marce\.claude\plans\velvety-toasting-squid.md`.

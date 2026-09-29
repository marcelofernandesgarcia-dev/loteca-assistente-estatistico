# Estudo: análise do palpite do usuário e aprendizado com as marcações (29/09/2026)

Pedido do usuário (item 20 da rastreabilidade): acrescentar interações para pedir ao app uma análise das próprias marcações (se são coerentes com os dados, se há zebra, como duplos e triplos potencializam o bilhete), apresentar opções de análise, **registrar essas análises para aprendizado** e descrever os pontos positivos e negativos. Status: **estudo, nenhum código escrito.**

## 1. O que já existe e sustenta o pedido

- **A3 (bilhete salvo):** `bilhetes` e `bilhete_jogos` já guardam as marcações e o percentual do momento de cada jogo. `conferir_bilhete` já compara com o resultado real e com o que a sugestão do app teria acertado. A base do "aprendizado" já existe: falta analisar antes e acumular depois.
- **`stats/bilhete.montar_bilhete`** já calcula a chance estimada de 14 acertos.
- **Q6 (aprovado):** faixas históricas por coluna, medidas na base real (1: 5-9 jogos; X: 2-5; 2: 2-5).
- **Limiares de sugestão:** seco a partir de 65%, duplo a partir de 45% (`config.SUGESTAO_LIMIAR_*`).

## 2. Opções de análise (todas por regra, auditáveis, sem IA)

| # | Análise | O que responde | Exemplo real (concurso 1272) |
|---|---|---|---|
| A1 | Coerência com os dados | Cada marcação é a favor dos dados, contra (zebra) ou num jogo equilibrado | "Jogo 1: você marcou 1 (Inglaterra, 21%); o mais provável é 2 (52%)" |
| A2 | Zebras marcadas | Quais marcações têm probabilidade baixa, e quanto custam em chance | Idem, listadas juntas |
| A3 | Rendimento dos duplos e triplos | Quanto cada duplo ou triplo aumenta a chance daquele jogo, pelo mesmo custo; onde ele renderia mais | Duplo X2 no jogo 1: 52% → 79% (+27). Duplo 1X no jogo 14: 80% → 93% (+13). Mesmo custo, ganho diferente |
| A4 | Chance estimada do bilhete | Probabilidade de 14 e de 13 ou mais, e acertos esperados | Sugestão do app: 14 acertos ≈ 1 em 1.297; 13 ou mais ≈ 1 em 119; ≈ 8,6 acertos esperados |
| A5 | Distribuição por coluna | Quantos 1, X e 2 foram marcados, contra as faixas históricas (Q6) | "11 jogos na coluna 1: acima da faixa de 5 a 9 que cobre 79% dos concursos" |
| A6 | Jogos sem base própria | Onde o percentual é a média geral (47/26/27), porque o time tem pouco histórico | Jogos 8, 10 e 13 do 1272. Ali, nenhuma marcação tem apoio forte nos dados |
| A7 | Contexto que apoia ou contradiz | Notícia (lesão, suspensão), zona na tabela e forma no ano de cada lado | "Marcou o mandante, que tem notícia de desfalque nesta semana" |
| A8 | Diferença para a sugestão do app | Onde e por que você divergiu | "Você divergiu em 3 jogos" |
| A9 | Depois do resultado | O que aconteceu em cada categoria (a favor, zebra, equilibrado) e se os duplos "salvaram" algum jogo | "Seus 2 duplos: 1 salvou o jogo, 1 não fez diferença" |

**Registro para aprendizado:**
- Ao salvar, guardar a análise junto com o bilhete: a categoria de cada marcação, a probabilidade dela e se diverge da sugestão.
- Opcional: **motivo da marcação** por jogo, em etiquetas simples ("técnico novo", "clássico", "time poupado", "notícia", "intuição"). É informação que o app não tem, justamente a lacuna deixada pelas fontes descartadas (redes sociais, dado tático).
- Com o tempo, um painel "Meu histórico de palpites" em "Meus bilhetes": acerto por categoria, acerto quando você diverge do app (você x app nos mesmos jogos), acerto por motivo, e utilidade dos duplos e triplos.

## 3. Pontos positivos

1. **Serve o objetivo do app.** Transforma o card em apoio à decisão ("reduzir risco e erro"), sem decidir pelo usuário.
2. **Deixa o risco visível.** Zebra, custo e ganho real de cada duplo ou triplo, e a chance verdadeira do bilhete (1 em 1.297 para 14 acertos, no exemplo) são números concretos, não impressão. Isso reforça o jogo responsável.
3. **Duplos mais bem colocados.** A3 mostra onde o mesmo gasto rende mais. É o ganho mais prático e mais seguro da proposta, porque é aritmética sobre os percentuais.
4. **O usuário vira fonte de dado.** As marcações e os motivos trazem conhecimento que o app não coleta. Medir se esse conhecimento acerta mais que o app é a forma honesta de aproveitá-lo.
5. **Mede o app também.** Comparar "você x app" nos mesmos jogos é um backtest contínuo, do mesmo tipo do B3, com dados novos toda semana.
6. **Custo baixo.** Reaproveita A3, Q6, notícias e contexto de tabela. Sem fonte nova.

## 4. Pontos negativos e riscos (e como tratar)

1. **A referência é fraca.** O B3 mostrou que o modelo atual **perde da frequência simples**. "Coerente com os dados" não pode ser lido como "certo". Tratamento: nunca usar "certo/errado"; mostrar a confiança do número e, ao lado, a frequência histórica simples.
2. **Ilusão de controle.** Uma análise bem apresentada pode fazer o palpite parecer "validado". É loteria. Tratamento: mostrar sempre a chance real do bilhete inteiro e o aviso de responsabilidade.
3. **Punir zebra por padrão pode piorar o prêmio.** O estudo anti-manada (Q7) viu que concursos com mais zebras tendem a ter menos ganhadores (correlação fraca, -0,13). Uma análise que só desencoraja zebra empurra o usuário para o palpite de todo mundo. Tratamento: mostrar zebra como "chance menor, prêmio possivelmente menos dividido", sem juízo.
4. **Amostra pequena.** Um bilhete por semana dá 14 marcações por semana. Conclusões sobre "você acerta mais que o app quando diverge" levam meses. Tratamento: número mínimo de casos antes de mostrar qualquer conclusão, e a amostra sempre visível.
5. **Viés de memória.** Os acertos marcam mais que os erros. O registro automático corrige isso, desde que todo bilhete seja salvo, e não só os bons.
6. **Risco de sobreajuste.** Usar as marcações do usuário para mexer nos pesos do modelo seria ajustar o app à sorte de uma pessoa. Tratamento: registrar e medir, sim. Mudar o modelo, só depois de um backtest mostrar ganho (mesma regra do B2).
7. **O card pode voltar a ficar confuso.** Você acabou de apontar isso. Tratamento: a análise fica fora do volante, num botão "Analisar meu palpite", com seções recolhíveis.
8. **Percentual sem base própria.** Em jogos com pouco histórico (A6), qualquer análise de coerência é fraca. Tratamento: marcar esses jogos explicitamente.

## 5. Interações propostas

1. **"Analisar meu palpite"** (antes de salvar): executa A1 a A8 sobre as marcações atuais. Pode ser usado quantas vezes quiser.
2. **"Onde um duplo rende mais"**: lista os jogos pela chance ganha por real gasto. Ajuda a montar o bilhete, sem marcar nada sozinho.
3. **Motivo da marcação (opcional)**: etiquetas por jogo.
4. **Ao salvar**: a análise é guardada junto com o bilhete.
5. **Ao conferir** (em "Meus bilhetes"): A9 para o bilhete.
6. **"Meu histórico de palpites"**: o acumulado, liberado só quando houver amostra mínima.

## 6. Arquivos que seriam tocados (estimativa, para validar depois)

- `stats/analise_palpite.py` (novo): funções puras A1 a A9 e o acumulado.
- Tabela nova (ex. `bilhete_analises`) ou colunas novas em `bilhete_jogos`: migração aditiva, sem apagar dado.
- `app/pages/1_Concurso_atual.py` (card 3) e `app/pages/6_Meus_bilhetes.py`.
- `config.py`: limiares de zebra, jogo equilibrado e amostra mínima.
- Testes unitários e de página.

## 7. Perguntas para validação

1. Quais análises entram na primeira entrega? Sugestão: A1, A2, A3, A4 e A6 antes de salvar; A9 depois do resultado. As demais depois.
2. Quer o campo opcional de **motivo da marcação**?
3. O que conta como **zebra**? Sugestão: marcação com probabilidade abaixo de 25% (parâmetro ajustável).
4. **Ordem das entregas:** card de 3 quadrados, depois análise do palpite, depois painel comparativo? Ou outra ordem?

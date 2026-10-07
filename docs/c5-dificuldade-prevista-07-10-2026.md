# C5 — dá para saber antes do prazo se o concurso será "fácil"? (07/10/2026)

> Item C5 do plano v2. Só mede; nada no app muda por ele.

## Pergunta
O material do usuário de 07/10/2026 propunha ajustar duplos e triplos "para concursos com perfil semelhante" aos pulverizados. O perfil (muitos ou poucos ganhadores de 14) só é conhecido depois do resultado. A pergunta é se algum dado disponível antes do prazo o antecipa.

## Método
- **Dificuldade prevista:** soma, nos 14 jogos, de −ln(chance do favorito), com a previsão do app feita sem olhar o futuro (`stats.calibracao.carregar_registros`: modelo histórico do B3 e Elo nas seleções). Um valor maior significa mais jogos sem favorito claro. Função: `stats.anti_manada.dificuldade_prevista`.
- **Resultado:** ganhadores de 14 por milhão arrecadado (a mesma medida do estudo anti-manada Q7).
- **Teste:** correlação de Spearman estratificada por ano, como no Q7 (`testar_dificuldade_prevista`), com 5.000 permutações e reamostragem para o intervalo. Se a dificuldade fosse previsível, a correlação seria negativa.

## Resultado (banco real, 07/10/2026)
- **838 concursos.** Correlação −0,048 (intervalo de 95%: −0,123 a +0,026; p = 0,19). **Sem diferença perceptível.**
- Concurso 1273: dificuldade prevista de 8,13, um pouco acima da mediana (7,85; 10% dos concursos ficam abaixo de 6,75 e 10% acima de 9,28). Mesmo assim, foi o concurso com mais ganhadores por milhão em 2026.

## Decisão
O perfil do concurso não é previsível com os percentuais do app. Ele serve só para a revisão pós-jogo (D4) e nunca para mudar a sugestão de um concurso futuro.

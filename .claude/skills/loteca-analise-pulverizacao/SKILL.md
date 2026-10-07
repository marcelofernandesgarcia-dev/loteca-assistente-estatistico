---
name: loteca-analise-pulverizacao
description: Análise pós-jogo de um concurso da Loteca, em especial de concurso com muitos ganhadores (pulverizado), usando os números que o próprio app calcula (diagnóstico do concurso, revisão do bilhete, retrato, notícias lidas). Usar quando o usuário pedir a análise de um concurso apurado ou quando o diagnóstico do app classificar o concurso como "fácil". Só vale neste projeto.
---

# Análise pós-jogo de concurso da Loteca (concurso pulverizado)

Skill de projeto, criada em 07/10/2026 com autorização do usuário (plano v2, decisão 9), depois que a revisão pós-jogo (D2) e o diagnóstico do concurso (D4) entraram no app. Não se aplica fora do repositório `loteca-assistente-estatistico`.

## Regras que não mudam
- **Nada de dado fabricado.** Todo número vem do banco ou das funções do app. O que faltar é declarado como lacuna.
- **Um concurso não recalibra o modelo.** Um concurso tem 14 jogos; ajustar o modelo a ele é ajustar ao acaso. Muitos ganhadores com erro do app é **sinal para examinar** os jogos errados, nunca ordem de mudar peso. Mudança de modelo só com teste fora da amostra (perda logarítmica menor, q < 0,05) em todos os concursos.
- **O perfil do concurso só existe depois do resultado.** Não use "concurso parecido" para mudar a sugestão de um concurso futuro, a menos que um indicador conhecido antes do prazo tenha sido testado (item C5 do plano v2).
- **Comprovante da CAIXA nunca entra** em relatório, cofre, repositório ou log: tem nome e CPF.
- Sugestão do app: no máximo um duplo ou um triplo. O app nunca estima prêmio em reais.
- Volume de apostas por coluna: o app não tem esse dado; não afirme "a maioria apostou em X".

## Passos
1. **Diagnóstico do concurso** (`stats.anti_manada.carregar_concursos` + `stats.revisao.diagnostico_do_concurso` e `frase_do_diagnostico`): ganhadores de 14 por milhão arrecadado, posição no ano e entre os concursos com ganhador, classe (fácil, médio, difícil, acumulou). Ganhadores de 13 vêm de `premiacoes` (pontos = 13).
2. **Jogo a jogo** dos bilhetes salvos do concurso (`stats.bilhetes_salvos.conferir_bilhete`, `stats.retrato.retrato_do_bilhete`, `stats.revisao.revisao_do_bilhete`): marcação, sugestão do app, percentual do momento e a origem dele (temporada da CBF, Elo, histórico da Loteca, frequência geral), resultado, surpresa = −ln(chance dada ao resultado) e leitura (acerto, erro, zebra, duplo útil, dispensável, não bastou). Compare a perda logarítmica média do app com a da frequência simples **neste** concurso, avisando que um concurso só não mede o modelo.
3. **Onde o app errou o que a maioria acertou**: separe os jogos errados por origem e cobertura (`stats.cobertura`, `stats.painel_bilhetes.segmentos_do_jogo`). Num concurso fácil, erro concentrado em cobertura parcial ou baixa aponta falta de dado; erro em cobertura completa aponta fraqueza do modelo.
4. **Notícias da semana**: `externo.varredura.noticias_lidas_do_concurso` mostra cada manchete lida, a decisão do filtro e o motivo do descarte. Confira se algum sinal caiu no time errado e se algum desfalque confirmado ficou de fora. Manchete nova rotulada pelo usuário entra no gabarito (`scripts/gabarito_noticias.py`).
5. **O que aconteceu fora dos dados**: só com fonte verificada na sessão (busca na web, citando veículo e data). Sem fonte, não afirme.
6. **Recomendações**: só as que um teste pode validar depois. Escreva cada uma com o teste que a aprovaria e o critério.

## Saída
- Relatório em Artifact (o usuário revisa por lá), com: resumo do diagnóstico; tabela jogo a jogo; onde o app errou e por quê (dado faltando, notícia, modelo); o que mudou na semana (com fonte); recomendações com o teste de cada uma.
- Nota no cofre Cerebro Pessoal, área `Loteca/Notas/`, com link para o Artifact, pela skill `gestor-conhecimento-cofres`. Lições ficam como "proposta" até o usuário validar.

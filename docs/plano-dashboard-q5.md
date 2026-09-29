# Plano: painel comparativo de times e seleções (Fase Q5, 29/09/2026)

Pedido do usuário: "dashboard com informações visuais detalhadas por times, seleções, classificações, vitórias, empates, derrotas entre outras métricas", **com linhas de tendência**, **priorizado para agora**. Status: **implementado em 29/09/2026** (autorização do usuário: "pode implementar"). Ver `stats/painel.py` e `app/pages/7_Painel_comparativo.py`.

## 0. Respostas do usuário à versão 1 (29/09/2026)

| # | Pergunta | Resposta | Efeito |
|---|---|---|---|
| 1 | Duas abas separadas (CBF / Loteca) | **Sim** | Mantido |
| 2 | Tendência só como média móvel, sem reta projetada | **Não.** "A ideia é justamente imaginar o que pode acontecer caso persista o desempenho do time analisado." | Entra **projeção de cenário** (seção 3) |
| 3 | Até 8 times por gráfico | **Não.** "Todos os times do concurso devem ser analisados." | Sem limite; legibilidade resolvida por organização por jogo e mini-gráficos (seção 4) |
| 4 | Mínimo de 10 jogos na Loteca | **Sim, inicialmente.** Registrar que pode aumentar se mais informação favorecer a análise | `PAINEL_MIN_JOGOS_LOTECA = 10`, com esse registro no próprio `config.py` |

## 1. Diagnóstico (verificado no código e no banco real)

**Dois universos de dado que não se misturam num número só:**

| Universo | O que tem | Cobertura real hoje |
|---|---|---|
| Temporada CBF (`cbf_partidas`, `cbf_classificacao`, `cbf_estatisticas_time`) | Campeonato inteiro, rodada a rodada | Série A 2026 (277 jogos, até a rodada 28) e Série B 2026 (296 jogos, até a rodada 30); 20 times cada; 40 clubes pareados com a Loteca |
| Histórico da Loteca (`jogos`) | Só os jogos que caíram na grade, 2002-2026 | 947 clubes (mediana de 4 jogos) e 74 seleções (mediana de 11; 23 com 20 ou mais) |

**Concurso a jogar (1272):** 28 participantes, 14 clubes e 14 seleções; 12 clubes pareados com a CBF.

**Formato da temporada, lido no regulamento oficial (não suposto):** REC Série A 2026, Art. 14, e REC Série B 2026, Art. 11: pontos corridos, turno e returno, 19 jogos de ida e 19 de volta, ou seja, **38 jogos por time**. É isso que permite projetar "até o fim da temporada".

**Limite do dado atual:** o banco só tem jogos já disputados (0 jogos sem placar). Os adversários que faltam para cada time não estão coletados. Por isso a projeção v1 usa o ritmo do time, sem considerar a força dos adversários restantes. Isso fica escrito na tela.

**Reaproveitado sem alteração:** `stats/competicao.py` (`carregar_partidas`, `tabela_por_rodada`, `evolucao_do_time`, `jogos_do_time`, `aproveitamento_movel`, `sequencia_atual`, `metricas_por_time`, `disciplina_da_liga`), `stats/contexto.py` (`selo_da_posicao`, `zona_da_posicao`), `stats/cbf.py`, `stats/concursos.py`, `app/paleta.py`.

**Achado:** `stats/desempenho.tendencia_por_ano` guarda em `pct_aproveitamento` o **% de vitórias**. A Ficha do time rotula certo ("% vitórias"), então não há erro visível. O painel usa **aproveitamento por pontos** (3/1/0), igual à CBF. A Ficha não é alterada.

## 2. Estrutura: duas abas, dois modos

Página nova **"Painel comparativo"** (`app/pages/7_Painel_comparativo.py`).

Em cada aba, um seletor de modo:
- **Concurso a jogar (padrão):** analisa **todos** os participantes do concurso, organizados pelos 14 jogos.
- **Livre:** qualquer conjunto de times escolhido pelo usuário, sem limite de quantidade.

### Aba 1: Temporada (CBF), clubes das Séries A e B
- **Tabela comparativa:** posição oficial e zona, pontos, J, V, E, D, gols pró e contra, saldo, aproveitamento (geral, casa, fora), sequência atual, cartões por jogo, **e as colunas de projeção** (seção 3). Posição e pontos vêm da classificação oficial da CBF; a evolução, da reconstrução já validada.
- **Gráficos:**
  1. Posição rodada a rodada, zonas sombreadas, com a **posição projetada na rodada 38**.
  2. Pontos acumulados, média da série tracejada, e **a continuação projetada até a rodada 38** em dois cenários (faixa entre eles).
  3. Aproveitamento nos últimos 5 jogos, com **reta de tendência** estendida até o fim da temporada.
  4. V/E/D em barras empilhadas, com os números escritos.
  5. Ataque x defesa: série inteira em cinza, selecionados destacados, médias da liga.
  6. **Mapa de calor** times x rodadas (cor = posição, número escrito na célula): mostra todos os times de uma vez sem virar um emaranhado de linhas.
- **Leituras automáticas por regra**, com o número que as sustenta. Exemplo: "No ritmo das últimas 5 rodadas, terminaria com 61 pontos, na zona de Libertadores."

### Aba 2: Histórico na Loteca, clubes e seleções
- **Aviso fixo:** "Desempenho nos jogos que caíram na grade da Loteca. Não é classificação de campeonato."
- **Tabela:** J, V, E, D (e %), aproveitamento por pontos, gols por jogo, casa e fora, tamanho da amostra, **ritmo recente** (aproveitamento nos últimos 10 jogos na Loteca) contra o histórico.
- **Gráficos:** aproveitamento por ano (marcador proporcional ao número de jogos; anos com menos de 3 jogos vazados) com **reta de tendência** estendida ao ano seguinte; V/E/D empilhado.
- **Mínimo de 10 jogos:** filtra só o modo livre. No modo concurso, **todo participante aparece**, mesmo abaixo de 10, com a marca "amostra pequena" (porque todos os times do concurso devem ser analisados).

## 3. Projeção "se o desempenho persistir"

É um **cenário**, não uma previsão. O rótulo na tela diz isso e diz o que o cálculo ignora.

**Aba 1 (temporada), dois cenários por time:**
- **Ritmo da temporada:** pontos atuais + (38 − jogos disputados) × pontos por jogo na temporada.
- **Ritmo recente:** o mesmo, com os pontos por jogo dos últimos 5 jogos.
- **Posição e zona projetadas:** todos os 20 times da série projetados no próprio ritmo, reordenados, e a zona lida do regulamento (mesma regra do C1). Resultado: "terminaria entre o 4º (ritmo recente) e o 7º (ritmo da temporada)".
- **Reta de tendência do aproveitamento:** mínimos quadrados sobre a série da média móvel, estendida até a rodada 38, limitada entre 0% e 100%.

**Aba 2 (histórico na Loteca):** reta de tendência do aproveitamento anual (ponderada pelo número de jogos do ano), estendida ao ano seguinte. Só é desenhada com pelo menos 3 anos que tenham 3 jogos ou mais; fora disso, a tela diz que não há base para projetar.

**Quanto a projeção costuma errar (medido, não suposto):** o projeto já mede o modelo contra a própria base (página "Confiabilidade", B3). A projeção recebe o mesmo tratamento: com os dados da temporada atual, projeto a partir de uma rodada passada (por exemplo, a 19ª) e comparo com os pontos reais de hoje. O erro médio, em pontos, aparece ao lado da projeção ("nesta temporada, projetar da rodada 19 para a 28 errou em média X pontos"). É um teste do método, não uma garantia.

**O que o cenário não considera (escrito na tela):** a força dos adversários restantes (calendário futuro não coletado), lesões, suspensões, troca de técnico e a disputa de outras competições. Coletar o calendário futuro da CBF é uma melhoria possível para depois, registrada aqui e não incluída nesta entrega.

## 4. Todos os times do concurso, sem limite, legíveis

- **Visão por jogo (modo concurso):** 14 blocos, um por jogo, com mandante e visitante lado a lado: os números principais, as linhas de tendência e a projeção dos dois no mesmo mini-gráfico. Na aba 1, só entram os clubes com dados da CBF; o bloco diz quando um lado não tem esse dado. Na aba 2, entram todos os 28.
- **Visão geral:** tabela com todos (ordenável) e, na aba 1, o mapa de calor.
- **Modo livre com muitos times:** até 8, linhas sobrepostas no mesmo gráfico; acima disso, **mini-gráficos** (um por time, mesma escala), sem limite de quantidade.

## 5. Arquivos (nenhum existente é reescrito)

| Arquivo | Ação |
|---|---|
| `stats/painel.py` | **Novo.** Funções puras: tabela comparativa, séries de tendência, projeção por ritmo (dois cenários), posição/zona projetada, reta de tendência, erro medido da projeção, resumo e tendência anual na Loteca por pontos, participantes do concurso agrupados por jogo, leituras por regra |
| `config.py` | Novos parâmetros: `TEMPORADA_JOGOS_POR_TIME` por (série, ano) = 38, citando o REC; `PAINEL_MIN_JOGOS_LOTECA = 10` (com o registro de que pode aumentar); `PAINEL_MIN_JOGOS_ANO = 3`; `PAINEL_LINHAS_SOBREPOSTAS_MAX = 8`; `PAINEL_JANELA_RECENTE_LOTECA = 10`; `PAINEL_RODADA_TESTE_PROJECAO = 19` |
| `app/pages/7_Painel_comparativo.py` | **Nova** página, sem regra de negócio |
| `tests/test_painel.py` | **Novo.** Unitários, com casos de borda e de erro (inclusive: time com 38 jogos não projeta nada; série/ano sem cadastro de temporada não projeta; aproveitamento projetado nunca sai de 0-100%) |
| `tests/test_pagina_painel.py` | **Novo.** `AppTest` sobre banco sintético |
| `README.md`, rastreabilidade, cofre | Registro |

Sem tabela nova, sem migração, sem dependência nova, sem fonte nova.

## 6. Casos de borda
- CBF não coletada ou desligada: a aba 1 explica como coletar; a aba 2 funciona.
- Série/ano sem o número de jogos cadastrado em `TEMPORADA_JOGOS_POR_TIME`: tabela e gráficos aparecem, a projeção não (e a tela diz por quê). O módulo nunca supõe o tamanho da temporada.
- Time com menos de 5 jogos: cenário "ritmo recente" não calculado.
- Participante sem jogo no período: "sem jogos no período", sem divisão por zero.
- 94 jogos da Loteca sem data: entram nos totais, ficam fora da tendência anual; a página informa quantos.
- Concurso a jogar inexistente: o modo concurso avisa e o modo livre continua disponível.

## 7. Sequência
1. `config.py`, `stats/painel.py` e testes unitários (inclui a medição do erro da projeção).
2. Aba 1 (tabela, gráficos, mapa de calor, projeção, visão por jogo) e teste de página.
3. Aba 2 e teste de página.
4. `pytest` completo; app com o banco real; conferência no navegador em tela larga e estreita; captura de tela.
5. README, rastreabilidade, cofre, commit e push.

## 8. Riscos
- **Nenhum ponto de não retorno:** tudo aditivo.
- **Projeção lida como previsão:** rótulo "cenário se o ritmo persistir", dois cenários em faixa (nunca um número só), erro medido ao lado, e a lista do que o cálculo ignora.
- **Reta de tendência em amostra pequena:** na aba 2 só aparece com base mínima; no fim da temporada a reta é limitada a 0-100%.
- **Excesso visual com todos os times:** organização por jogo, mapa de calor e mini-gráficos.
- **Desempate reconstruído:** posição atual vem da CBF oficial; a posição projetada usa o mesmo desempate documentado em `competicao.py` (pontos, vitórias, saldo, gols pró).

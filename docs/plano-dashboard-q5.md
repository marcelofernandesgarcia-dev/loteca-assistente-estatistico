# Plano: painel comparativo de times e seleções (Fase Q5, 29/09/2026)

Pedido do usuário: "dashboard com informações visuais detalhadas por times, seleções, classificações, vitórias, empates, derrotas entre outras métricas", **com linhas de tendência**, **priorizado para agora**. Status: **plano aguardando validação; nenhum código escrito.**

## 1. Diagnóstico (verificado no código e no banco real)

**Dois universos de dado que não podem ser misturados num número só:**

| Universo | O que tem | Cobertura real hoje |
|---|---|---|
| Temporada CBF (`cbf_partidas`, `cbf_classificacao`, `cbf_estatisticas_time`) | Campeonato inteiro, rodada a rodada | Série A 2026 (277 jogos, 28 rodadas) e Série B 2026 (296 jogos, 30 rodadas); 40 clubes pareados com a Loteca |
| Histórico da Loteca (`jogos`) | Só os jogos que caíram na grade, 2002-2026 | 947 clubes (mediana de 4 jogos cada) e 74 seleções (mediana de 11 jogos; 23 com 20 ou mais) |

**No concurso a jogar (1272):** 28 participantes, 14 clubes e 14 seleções. Só 12 dos clubes estão pareados com a CBF. Metade do concurso (as seleções) só existe no histórico da Loteca. Por isso o painel precisa das duas visões.

**O que já existe e será reaproveitado sem alteração:**
- `stats/competicao.py`: `carregar_partidas`, `tabela_por_rodada`, `evolucao_do_time` (posição, pontos e média da série por rodada), `jogos_do_time`, `aproveitamento_movel` (média móvel de 5 jogos, `config.COMPETICAO_JANELA_MOVEL`), `sequencia_atual`, `metricas_por_time` (ataque, defesa, aproveitamento casa/fora), `disciplina_da_liga` (cartões por jogo).
- `stats/contexto.py`: `selo_da_posicao` (zona pelo regulamento oficial).
- `stats/cbf.py`: `nomes_dos_times`, `cod_time_do_participante`.
- `stats/concursos.py`: `concurso_a_jogar`.
- `app/paleta.py`: cores já conferidas quanto a contraste.

**Achado ao ler o código:** `stats/desempenho.tendencia_por_ano` devolve um campo chamado `pct_aproveitamento`, mas o valor é **% de vitórias** (vitórias/jogos), não aproveitamento por pontos. Na Ficha do time o gráfico está rotulado corretamente como "% vitórias", então não há erro visível. O painel vai usar **aproveitamento por pontos** (vitória 3, empate 1), a mesma definição da CBF, rotulado assim, para as duas abas serem comparáveis. A Ficha do time **não** será alterada.

## 2. O que o painel mostra

Página nova **"Painel comparativo"** (`app/pages/7_Painel_comparativo.py`), com duas abas.

### Aba 1: Temporada (CBF), só clubes das Séries A e B
- **Filtros:** série (A ou B); times (até 8 por gráfico). Pré-seleção: os times daquela série que estão no concurso a jogar. Atalhos: "times do concurso", "zona de cima", "zona de rebaixamento".
- **Tabela comparativa:** posição oficial e zona (selo do regulamento), pontos, J, V, E, D, gols pró, gols contra, saldo, aproveitamento geral, em casa e fora, sequência atual, cartões por jogo. Posição e pontos vêm da **classificação oficial** da CBF; a evolução vem da reconstrução rodada a rodada, já validada contra a CBF.
- **Gráficos com linhas de tendência:**
  1. Posição rodada a rodada (1º no topo), com as faixas de zona sombreadas.
  2. Pontos acumulados por rodada, com a média da série tracejada.
  3. Aproveitamento nos últimos 5 jogos, rodada a rodada. É a linha de tendência principal: mostra quem está subindo ou caindo agora.
  4. V/E/D por time em barras empilhadas, com o número escrito em cada barra.
  5. Ataque x defesa (gols pró e contra por jogo): todos os times da série em cinza, os selecionados destacados, com as médias da liga.
- **Leitura automática por regra** (sem IA), cada frase com o número que a sustenta. Exemplo: "Maior subida nas últimas 5 rodadas: X, do 9º para o 4º."

### Aba 2: Histórico na Loteca, clubes e seleções
- **Aviso fixo:** "Desempenho nos jogos que caíram na grade da Loteca. Não é classificação de campeonato."
- **Filtros:** tipo (clube, seleção ou todos); participantes (até 8); período (ano inicial e final); mínimo de jogos (padrão 10). Pré-seleção: participantes do concurso a jogar.
- **Tabela:** J, V, E, D (e %), aproveitamento por pontos, gols pró e contra por jogo, aproveitamento em casa e fora, e o tamanho da amostra. Marcação "amostra pequena" abaixo do mínimo.
- **Gráficos:**
  1. Aproveitamento por ano, uma linha por participante. O marcador cresce com o número de jogos do ano; anos com menos de 3 jogos aparecem vazados, como sinal fraco.
  2. V/E/D empilhado, com os números escritos.

### Acessibilidade (padrão já adotado no D2)
Cada linha tem cor, símbolo de marcador e traço diferentes; a informação nunca depende só da cor. Toda tabela tem cabeçalho. Todo gráfico tem uma frase-resumo em texto.

## 3. Arquivos a tocar (nenhum existente é reescrito)

| Arquivo | Ação |
|---|---|
| `stats/painel.py` | **Novo.** Funções puras: tabela comparativa da temporada, séries de tendência por time, resumo e tendência anual na Loteca (aproveitamento por pontos), participantes do concurso, leituras por regra |
| `config.py` | +3 parâmetros: `PAINEL_MAX_TIMES = 8`, `PAINEL_MIN_JOGOS_LOTECA = 10`, `PAINEL_MIN_JOGOS_ANO = 3` |
| `app/pages/7_Painel_comparativo.py` | **Nova** página, sem regra de negócio (só consome `stats/`) |
| `tests/test_painel.py` | **Novo.** Unitários, incluindo casos de borda e de erro |
| `tests/test_pagina_painel.py` | **Novo.** `AppTest` sobre banco sintético (nunca o real) |
| `README.md`, este documento, cofre | Registro |

Sem tabela nova, sem migração, sem dependência nova (Plotly já instalado), sem fonte de dado nova.

## 4. Casos de borda previstos
- CBF não coletada ou desligada (`LOTECA_CBF_HABILITADO=0`): a aba 1 mostra como coletar; a aba 2 funciona normalmente.
- Nenhum time selecionado: texto de orientação, não tela vazia.
- Mais de 8 selecionados: aviso e corte.
- Participante sem jogo no período: linha "sem jogos no período", sem divisão por zero.
- Seleção escolhida na aba 1: não é oferecida (não tem dado da CBF).
- 94 jogos da Loteca sem data: entram nos totais e ficam fora da tendência por ano; a página informa quantos ficaram de fora.
- Rodada com jogo adiado: já tratado por `tabela_por_rodada`.

## 5. Sequência
1. Parâmetros em `config.py`, `stats/painel.py` e testes unitários.
2. Aba 1 e seu teste de página.
3. Aba 2 e seu teste de página.
4. `pytest` completo; rodar o app com o banco real; conferir no navegador em tela larga e estreita; captura de tela.
5. README, rastreabilidade, cofre, commit e push.

## 6. Riscos e pontos de não retorno
- **Nenhum ponto de não retorno:** tudo é aditivo. Desfazer = apagar os arquivos novos e reverter 3 linhas do `config.py`.
- **Poluição visual:** limite de 8 linhas por gráfico.
- **Confundir os dois universos:** abas separadas e rótulos explícitos. Nenhuma métrica soma CBF com Loteca.
- **Amostra pequena (seleções, clubes raros):** tamanho da amostra sempre visível e mínimo configurável.
- **Desempate reconstruído:** a posição da tabela vem da CBF oficial; só as linhas de evolução são reconstruídas (critérios além do 4º podem divergir da CBF, limitação já documentada em `competicao.py`).

## 7. Perguntas para validação
1. Aprova as duas abas separadas (temporada CBF / histórico na Loteca), em vez de uma visão única misturando as fontes?
2. "Linha de tendência" = média móvel dos últimos 5 jogos (padrão do projeto). Proposta: **não** incluir reta de regressão projetada para frente, porque isso sugere previsão. Concorda?
3. Limite de 8 times por gráfico, com pré-seleção nos participantes do concurso a jogar. Está bom?
4. Mínimo de 10 jogos na Loteca para entrar no comparativo histórico por padrão (ajustável na tela). Está bom?

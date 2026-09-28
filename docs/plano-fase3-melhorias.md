# Fase 3 — Melhorias do aplicativo (proposta para validação, 27/09/2026)

## Contexto

O app já tem: importador da CAIXA, banco local, percentual por jogo (Poisson), sugestão seco/duplo/triplo, bilhete interativo, painel por time, leitura das páginas públicas da CBF (40 times, 573 partidas), notícias com veículos prioritários (ge, ESPN Brasil) e 51 testes. Esta fase propõe melhorias **mantendo os 3 cards e todas as solicitações anteriores** (datas dd/mm/aaaa, explicação dos cards, bilhete marcável, confronto com o desempenho do ano em curso). Objetivo que rege tudo: **fortalecer a análise e reduzir risco e erro na escolha** — nunca prometer resultado. Cada melhoria abaixo traz a evidência que a justifica.

## Diagnóstico — o que a verificação de hoje mostrou

1. **O bilhete ainda não serve para o concurso que vai ser jogado.** Os cards 2 e 3 rodam sobre o último concurso *encerrado* (1271). A grade do próximo (1272) existe no mesmo servidor da CAIXA em `/api/loteca/programacao` (testado hoje: 14 jogos, prazo exato **15h de 26/09/2026**) e o app não a usa. O prazo que exibimos é só uma aproximação.
2. **O ajuste de notícias não aparece na tela.** Você pediu que ele ajuste o percentual automaticamente; ele é calculado e gravado (`percentuais.percentual_final`), mas nenhuma página lê essa tabela (busca em `app/` sem resultado). Além disso, o ajuste é somado por coluna sem renormalizar, então 1+X+2 pode não fechar 100%.
3. **O bilhete some ao recarregar a página** (fica só na sessão): não dá para conferir depois nem medir seu desempenho contra o do modelo.
4. **O modelo nunca foi medido.** Não sabemos se os percentuais acertam mais que a frequência histórica (47/26/27). A média de gols usada mistura Brasileirão, ligas europeias e seleções; times com pouca amostra caem na frequência global (vimos jogos diferentes com os mesmos 47/26/27). Os limiares 65%/45% foram escolhidos entre 3 propostas de fontes, sem teste com dado.
5. **Base pequena e nomes sujos:** só 47 dos 1.271 concursos importados; nomes como `SERVIA/SER` e `ESCOCIA/SCT` não batem com a lista de seleções e hoje seriam classificados como clube.
6. **Destaque só por cor** nos cards (vermelho = venceu/marcar): informação transmitida apenas por cor.
7. **Operação frágil:** as duas coletas agendadas dependem de você criar as tarefas e falham em silêncio; não há painel de status nem atalho para abrir o app (item 10 do plano original ficou pela metade).

## Roteiro (prioridade, justificativa, o que muda, critério de aceite)

Tamanhos: P pequeno · M médio · G grande.

### Fase A — corrigir lacunas entre o que foi pedido e o que está na tela (prioridade máxima)

**A1. Grade do concurso a jogar (programação oficial) — M**
- *Por quê:* sem isso o card 3 não é um bilhete de verdade; o prazo passa de aproximado a exato.
- *Muda:* `importer/caixa_client.py` ganha `importar_programacao()` (endpoint acima; jogos futuros com placar vazio); coluna `horario_fim_apostas` em `concursos` (migração simples); normalização de nomes (`SERVIA/SER` → `SERVIA`) em `stats/resultado.py`; a página "Concurso atual" passa a abrir no **próximo concurso** (card 1 continua mostrando o último encerrado), com prazo dd/mm/aaaa hh:mm.
- *Aceite:* a página mostra o concurso vigente com 14 jogos e o prazo real; cards 2 e 3 preenchidos; testes com JSON sintético + um teste de integração leve.

**A2. Percentual final visível (histórico + notícias) — M**
- *Por quê:* é um pedido seu que hoje não tem efeito visível.
- *Muda:* cards 2 e 3 leem `percentual_final` (ou o histórico, se não houve varredura); mostram a decomposição (ex.: "56% + 2 notícias = 58%") e um "por que ajustou" com a manchete e o veículo; o ajuste é **renormalizado para somar 100%**.
- *Aceite:* teste unitário da renormalização (soma 100, teto ±8 respeitado); tela mostra o ajuste e sua origem.

**A3. Bilhete salvo, conferência e controle de gastos — M**
- *Por quê:* o card 3 existe para confrontar a sua marcação com a análise; se ela some, não há como aprender com o resultado. E controlar gasto x prêmio é a medida mais direta de reduzir risco (jogo responsável).
- *Muda:* tabela `bilhetes` (concurso, marcações, apostas, custo, sugestão e percentuais do momento); botão "Salvar bilhete"; depois do resultado, "Conferir" (acertos x/14, se chegou a 13 ou 14, e como a sugestão do modelo teria ido); página "Meus bilhetes" com gasto acumulado, prêmios que você informar e saldo. Tudo local, sem dado pessoal.
- *Aceite:* salvar, recarregar e reabrir mantém a marcação; conferência do concurso 1271 bate com o resultado real (teste com dado conhecido).

### Fase B — confiança no modelo

**B1. Histórico completo e qualidade do dado — M** (~15 min de rede, retomável)
- *Por quê:* com 47 concursos as amostras são pequenas e não dá para validar nada.
- *Muda:* importar os concursos 1–1224 mantendo os 700 ms de intervalo; usar o campo `icSorteioResultado` (já vem na API) para marcar `situacao='sorteio'` e não contaminar as estatísticas com resultado sorteado; **conferência cruzada CAIXA x CBF** (mesmo jogo, mesma data → mesmo placar) com relatório de divergências, que também responde à pendência "o placar da CAIXA é do tempo regulamentar?".
- *Aceite:* 1.271 concursos importados; relatório de divergências gerado; testes das regras.

**B2. Modelo por competição, com os jogos completos da CBF — G**
- *Por quê:* hoje a média de gols mistura ligas; a CBF entrega a temporada inteira de 40 times (~28 jogos cada), muito mais amostra que os jogos que caíram na Loteca.
- *Muda:* forças de ataque/defesa e fator casa **por competição** (Série A, Série B, demais); em vez de cair na frequência global com pouca amostra, encolhimento em direção à média da própria liga; seleções em modelo à parte, marcadas como "baixa confiança".
- *Cuidado:* isso **muda os números dos cards**. Fica atrás de uma chave (`MODELO_VERSAO`) e só vira padrão depois que o B3 provar que melhora, com comparativo antes/depois para você ver.

**B3. Backtest, calibração e limiares com dado — M/G**
- *Por quê:* é o coração de "minimizar erro": medir se os percentuais valem alguma coisa e trocar opinião por evidência na escolha de 65%/45%.
- *Muda:* `stats/backtest.py` (walk-forward: cada concurso usa só jogos anteriores); métricas de acerto do favorito, Brier score, calibração por faixa (quando o modelo diz 60–70%, quanto acontece de fato?), acertos médios por bilhete e custo; comparação com duas referências simples (frequência histórica 47/26/27 e "sempre mandante"); laboratório de limiares (seco/duplo) mostrando acertos x custo; painel "Confiabilidade do modelo" no app.
- *Honestidade:* se o modelo mal superar a referência simples, o painel diz isso — também é informação útil.
- *Aceite:* relatório reproduzível, testes das métricas, painel na interface.

### Fase C — contexto e sinais

**C1. Contexto de tabela (CBF) — M**
- *Por quê:* as três fontes de metodologia que você trouxe citam contexto/motivação (~8%), e a notícia da CBF mostra que a Série B agora tem playoff do 3º ao 6º.
- *Muda:* `stats/contexto.py` classifica a situação do time (briga por título/acesso/playoff/rebaixamento/sem objetivo) por posição e rodadas restantes, com as zonas em `config.py`; aparece como selo ao lado do time no bilhete, **só informativo** de início.
- *Pendente de confirmação:* o tamanho das zonas de rebaixamento e de vagas continentais ainda não foi confirmado no regulamento da CBF — não vou supor; busco no site como usuário (já autorizado para a CBF) antes de codificar.

**C2. Notícias mais precisas e transparentes — M**
- *Por quê:* palavra-chave solta gera falso positivo (jogador do adversário, "sem lesão", "recuperado").
- *Muda:* exigir o nome do participante na manchete; anular sinal com "volta/recuperado/liberado"; guardar a evidência; medir a precisão com um conjunto de manchetes rotuladas (você valida algumas). Leitura por modelo de linguagem fica como opção futura, mantendo o teto de ±8 pontos.

### Fase D — operação e conformidade

**D1. "Atualizar tudo", painel de status e atalho — P/M**
- *Por quê:* evitar falha silenciosa e dispensar linha de comando no balcão.
- *Muda:* `scripts/atualizar_tudo.py` (programação e resultados da CAIXA, CBF, notícias, recálculo) com relatório; tabela `execucoes` e um painel "Status dos dados" na página inicial (última coleta de cada fonte, alerta se velha); `iniciar_loteca.bat` que ativa o ambiente e abre o app. As duas tarefas agendadas continuam sendo criadas por você (comandos no README).

**D2. Acessibilidade, testes de tela e cadeia de suprimentos — P/M**
- *Por quê:* destaque só por cor; testes de tela feitos à mão; dependências sem versão fixa.
- *Muda:* marca textual/ícone e `title` nas células destacadas ("✓ venceu", "★ marcar"); verificação de contraste; testes `AppTest` das 5 páginas viram parte do `pytest`; versões fixadas (`requirements.lock`) e `pip-audit`; logs estruturados nos scripts.

### Fase E — opcional, depende de decisão sua
- **ESPN Brasil (estatística por jogador)**, **UFMG (probabilidades por jogo como conferência independente do nosso modelo, entra no B3)**, **títulos dos canais de YouTube** e **"anti-manada" descritivo** (prêmio pago x número de zebras nos concursos passados, usando `premiacoes`, coerente com o estudo de Soto Costa, 1980). Nada disso é coletado sem o seu aval, e ESPN/UFMG têm termos próprios ainda não lidos.

## Ordem sugerida

A1 → A2 → B1 (pode andar em paralelo) → A3 → B3 → B2 → C1 → C2 → D1 → D2 → (E). Uma entrega pequena por vez, com testes, commit, registro no cofre e demonstração para você validar.

## Fora do escopo (reafirmado)
Odds de mercado; qualquer promessa ou garantia de resultado; estatística de jogador sem fonte autorizada; "classificação oficial" montada só com jogos da Loteca; criar tarefas agendadas do sistema (fica com você).

## Decisões que preciso de você
1. Aprova o escopo e a ordem A → D?
2. **A3:** posso guardar seus bilhetes e gastos no banco local?
3. **B2:** aceita que os percentuais dos cards mudem quando o novo modelo provar ser melhor (com comparativo antes/depois)?
4. **C1:** posso buscar no site da CBF o regulamento para confirmar as zonas antes de codificar?
5. **Fase E:** autoriza ou não ESPN, UFMG e YouTube?
6. Vai criar as duas tarefas agendadas (coleta da CBF e varredura de notícias)?

## Verificação (vale para todos os itens)
`pytest` verde a cada entrega; páginas executadas com `AppTest` sem erro; conferência com dado real (concurso 1271 encerrado e 1272 vigente); demonstração visual no navegador; commit + push; nota no cofre Obsidian. Nenhum dado da CBF entra no GitHub.

# P2: temporadas 2019 a 2025 da CBF (30/09/2026)

Segundo item da priorização estatística (`priorizacao-estatistica-30-09-2026.md`). Autorizado pelo usuário em 30/09/2026. Mesma fonte e mesmo método já usados em 2026: páginas públicas da CBF, 2 s entre páginas. O risco de termos de uso da CBF continua sendo o já assumido e registrado em `cbf-fonte-de-dados.md`.

## O que foi coletado

14 competições (Séries A e B, 2019 a 2025), em cerca de 16 minutos (uma primeira tentativa parou antes de gravar qualquer coisa: nas temporadas encerradas a CBF devolve o "próximo jogo" como lista, formato que o coletor não previa; corrigido e coberto por teste). O banco passou de **573 para 5.892 jogos** da CBF. Backup do banco antes (`loteca.db.bak-...-antes-cbf-historico`) e depois.

| | Jogos |
|---|---|
| 13 temporadas completas (380 jogos) | 4.940 |
| Série B 2023 (379 de 380: falta 1 jogo) | 379 |
| Temporada 2026 (em andamento) | 573 |

## Conferência dos dados

Para cada temporada, reconstruí a tabela a partir dos jogos e comparei com a classificação final publicada pela CBF. **11 das 14 conferem em jogos, pontos, gols e posição.** As outras 3, todas entendidas e nenhuma inventada:

| Temporada | O que difere | Tratamento |
|---|---|---|
| Série A 2019 | 1 gol a mais na soma dos jogos em dois times (Atlético 45 x 44; Internacional 39 x 38). Jogos e pontos batem | Inconsistência dentro das páginas da CBF. Não afeta resultado |
| Série B 2020 | Cruzeiro: 55 pontos na soma dos jogos, 49 na tabela da CBF (exatamente 6 a menos) | Compatível com perda de pontos por punição; **a causa não foi conferida**. A análise usa os resultados dos jogos |
| Série B 2023 | Falta 1 jogo (rodada 20, Juventude x Botafogo-SP) nas páginas dos times; a tabela da CBF o conta | O jogo **não foi inventado**. A temporada fica de fora das medições que exigem 380 jogos |

Ficam registradas em `config.CBF_ANOMALIAS_CONHECIDAS`; o roteiro as trata como conhecidas e termina sem falha.

## O que os dados mostram

**1. Base de referência sólida.** Nas 13 temporadas completas (4.940 jogos): mandante vence 46,6%, empate 28,5%, visitante vence 24,9%. Por temporada os valores variam pouco (mandante de 40,5% a 52,4%). A Loteca, sozinha, dava 47/26/27.

**2. Quanto a projeção do painel erra (medido em 13 temporadas, não em 1).** Projetando o fim da temporada com o que havia até ali, erro médio absoluto em pontos por time:

| Faltam | Ritmo da temporada | Ritmo dos últimos 5 jogos |
|---|---|---|
| 10 jogos | 3,8 | 5,6 |
| 19 jogos | 5,8 | 9,6 |
| 28 jogos | 10,1 | 12,7 |

**O ritmo recente foi pior em 13 de 13 temporadas, em todos os horizontes.** Isso contraria o que o painel mostrava com uma temporada só (onde o recente parecia só um pouco pior). Cinco jogos são pouca amostra; o ritmo recente oscila mais do que o time realmente muda. O painel agora mostra esse erro medido, com a contagem "o recente foi melhor em 0 de 13 temporadas".

**3. Exploratório, não adotado: uma projeção mais cautelosa.** Puxar o ritmo do time em direção à média da liga (60% do ritmo do time + 40% da média) reduz o erro nos três horizontes:

| Faltam | Ritmo da temporada (100%) | Cautelosa (60%) | Redução |
|---|---|---|---|
| 10 jogos | 3,76 | 3,66 | 3% |
| 19 jogos | 5,83 | 5,36 | 8% |
| 28 jogos | 10,05 | 7,90 | 21% |

Um só parâmetro e 13 temporadas, escolhido olhando os mesmos dados (por isso "exploratório"). Não foi para o app: mudaria os cenários que o usuário aprovou. Proposta na pergunta ao usuário.

**4. Em 4 clubes, o código da CBF mudou quando viraram SAF** (verificado nos nomes e anos): Vasco (20012 até 2021, 60646 desde 2022), Coritiba (20025 até 2022, 61590 desde 2023), Fortaleza (20048 até 2024, 63238 desde 2025) e Londrina (20069 até 2023, 62726 em 2026). O pareamento com a Loteca guarda só o código atual, então a história anterior desses clubes fica sob outro código. Antes de usar a história por clube (P3), é preciso uma tabela de códigos equivalentes, validada pelo usuário. **Não foi criada.**

## O que mudou no código

- `importer/cbf_client.py`: uma temporada antiga **não sobrescreve** o nome atual do time em `cbf_times` (sem isso, "Coritiba SAF" voltaria a "Coritiba" e a marca de SAF e o link do Transfermarkt quebrariam); o nome de cada temporada fica em `cbf_classificacao.nome_no_ano`; temporada encerrada (próximo jogo como lista) grava sem erro.
- `scripts/coleta_cbf_historico.py`: coleta única, retomável (pula temporada completa e conferida).
- Consultas de "time atual" (`stats/cbf.py`, `serie_do_time`) olham só a temporada mais recente: um clube que só aparece em anos passados não é mostrado como se estivesse na competição de agora.
- Painel comparativo: o modo "todos do concurso" usa só a temporada atual; o modo livre oferece as 16 temporadas, com o nome que cada time tinha no ano, e o erro da projeção passa a ser o medido entre temporadas.
- Pareamento com a Loteca: **não alterado** (40 clubes, como antes).

## Limitações

- Só Séries A e B, de 2019 a 2025 (2018 e antes não foram conferidas).
- Uma temporada com 1 jogo faltando (Série B 2023) e uma com pontos perdidos por punição (Série B 2020, causa não conferida).
- Clubes que jogaram só a Série C nesse período não estão na base.

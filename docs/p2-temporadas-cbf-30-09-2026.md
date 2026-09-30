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

**3. Projeção cautelosa, adotada em 30/09/2026 a pedido do usuário.** Puxar o ritmo do time em direção à média da liga reduz o erro. A primeira ideia, um peso fixo de 60% para o time, foi escolhida olhando as mesmas 13 temporadas em que foi medida, então testei sem olhar a temporada de fora (deixando uma temporada de fora por vez, escolhendo o parâmetro nas outras 12):

- O melhor peso fixo **não** era 0,6: variava entre 0,4 e 0,5 e dependia do horizonte, porque com poucos jogos disputados o ritmo do time é menos confiável.
- Uma forma melhor: **peso do time = jogos / (jogos + k)**, que cresce com os jogos disputados. O k escolhido sem a temporada de fora foi **18 ou 22 nas 13 validações**. Usei **k = 20** (`config.PROJECAO_JOGOS_DE_MEDIA_DA_LIGA`). Com 28 jogos disputados o time vale 58%; com 19, 49%; com 10, 33%.

| Faltam | Só o ritmo do time | Projeção cautelosa (fora da amostra) | Redução | Melhor em quantas das 13 temporadas |
|---|---|---|---|---|
| 10 jogos | 3,76 | 3,67 | 2% | 7 |
| 19 jogos | 5,83 | 5,41 | 7% | 9 |
| 28 jogos | 10,05 | 7,51 | 25% | 11 |

O ganho é grande longe do fim da temporada e pequeno perto dele (faltando 10 jogos, 7 de 13 temporadas e 2% de redução: praticamente empate). O painel mostra as duas linhas, com o erro medido, e o ritmo dos últimos 5 jogos saiu (foi melhor que o da temporada em 0 de 39 medições).

**4. Em 11 clubes, a CBF trocou o código** (achado por busca sistemática nos 68 códigos e revisão manual; primeiro eu tinha visto só 4): Amazonas (2025), América-MG (2022), Atlético Goianiense (2024), Atlético Mineiro (2023), Bahia (2023), Botafogo-RJ (2022), Coritiba (2023), Cruzeiro (2022), Fortaleza (2025), Londrina (2026) e Vasco (2022). Em todos, o mesmo nome e a mesma UF, um código termina e o outro começa no ano seguinte. É compatível com a criação da SAF, mas **a causa não foi verificada** numa fonte externa. O pareamento com a Loteca guarda só o código atual, então a história anterior desses clubes fica sob outro código. A tabela de equivalência está em `data/cbf-codigos-equivalentes.csv` e foi **validada pelo usuário em 30/09/2026 ("todas corretas")**; `stats/cbf.codigos_equivalentes()` lê só as linhas com status `validado`. Ainda não é usada em nenhuma análise (fica para a P3).

**5. A marca de SAF olhava só o nome de 2026 e ficava incompleta.** América-MG, Atlético-MG, Cruzeiro e Cuiabá tiveram "Saf" no nome da CBF em anos anteriores (por exemplo, Cruzeiro de 2022 a 2025), mas o nome de hoje não traz. **Feito (decisão do usuário, 30/09/2026):** a Ficha do time usa o nome de cada temporada (`nome_no_ano`, `stats/cbf.historico_saf_na_cbf`). Se o nome traz "SAF" sem interrupção até hoje: "Registrado como SAF na CBF desde AAAA" (com o aviso "o ano mais antigo coletado; pode ser anterior" quando AAAA é o primeiro ano coletado do clube). Se houve interrupção ou o nome de hoje não traz: "Consta como SAF no nome da CBF em [anos]", sem afirmar "desde". No banco real, 13 clubes recebem a marca; os quatro acima entram sem a frase "desde". A ausência do sufixo continua sem provar que o clube não é SAF (Botafogo-RJ e Bahia não trazem).

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

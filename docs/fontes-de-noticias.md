# Fontes de notícia, análise e referência trazidas pelo usuário (27/09/2026)

Estado vivo no cofre Obsidian (`Loteca/Notas/Fontes de notícia e referência.md`). Para cada item: o que é, o que dá para aproveitar, e o que fica pendente de decisão.

## Canais esportivos (lista do usuário)
| Canal | Natureza | Uso no projeto |
|---|---|---|
| **ge (Globo/SporTV)** | portal de notícias | **Em uso**: consulta `site:ge.globo.com` no monitoramento semanal (só manchete, veículo e link) |
| **ESPN Brasil** | portal de notícias | **Em uso**: consulta `site:espn.com.br` |
| TV Globo, SporTV (TV), Premiere, BandSports (TV) | transmissão de TV / pay-per-view | Não são fonte de dado. Útil, no máximo, para o apostador saber onde assistir |
| CazéTV, TNT Sports Brasil, Desimpedidos, Canal GOAT | canais de YouTube | **Pendente**: dá para ler os títulos dos vídeos via feed público de cada canal, mas exige o `channel_id` de cada um (não chutei) e o valor é baixo (título de transmissão ao vivo/entretenimento raramente traz lesão ou escalação) |

Mudanças em `externo/coleta.py`: busca geral + uma consulta por veículo prioritário (lista em `config.NOTICIAS_FONTES_PRIORITARIAS`), sempre com janela recente (`when:10d`, `config.NOTICIAS_JANELA_DIAS`) para uma lesão antiga não virar sinal falso; deduplica manchetes; testado sem rede (`tests/test_coleta_noticias.py`). O texto das matérias não é copiado.

## Driblab (artigo da CBF, 21/07/2026)
A CBF contratou a Driblab (métricas avançadas, sede em Madri, fundada em 2017) para fornecer dados e monitorar atletas e adversários da **Seleção Feminina Principal**, contrato até a Copa do Mundo Feminina de 2027. É serviço **comercial e privado, para a comissão técnica** — sem API aberta descrita, e de futebol **feminino** (as grades da Loteca são masculinas). Não muda a coleta atual. Fica como **possível fonte licenciada futura** para métricas avançadas (xG etc.), hoje fora do escopo.

## Vídeo "Análise de Futebol com o Power BI" (YouTube, canal Marcoaurélio, 54 min, transmissão de 01/05/2024)
Licença do vídeo: Creative Commons Atribuição. A **transcrição não carregou** na interface, então a análise se baseia no título e na descrição. Achado útil: o vídeo coleta dados **das páginas de estatísticas da ESPN Brasil** (`espn.com.br/futebol/estatisticas/_/liga/<código>/temporada/<ano>/vista/gols`) para montar tabelas. Isso indica que a ESPN Brasil tem **estatística por jogador** (gols; provavelmente outras visões) — justamente o que a CBF e a Loteca não trazem. **Pendente de decisão do usuário**: a ESPN tem termos próprios (ainda não lidos) e o pedido de acesso "como usuário, por agendamento" foi dado só para a CBF; não coletei nada da ESPN.

## Site "Probabilidades no Futebol" (UFMG) — https://www.mat.ufmg.br/futebol/
Grupo acadêmico que publica, para Série A e B (e outras competições), **probabilidades por time** (título, vaga em competição continental, acesso/rebaixamento), probabilidade por pontuação, classificações auxiliares (últimas 10 rodadas, como mandante, como visitante, turno/returno), **tabela de probabilidades da próxima rodada** e sequências (vitórias, invencibilidade, melhor ataque/defesa). A página indicada mostra, para a Série A 2026, a probabilidade acumulada de ser campeão por pontuação (ex.: com 72 pontos, ~59%). Aproveitamento possível: (1) **referência independente** para conferir os nossos percentuais de vitória/empate; (2) probabilidades de título/acesso/rebaixamento como insumo do fator "contexto de tabela". O site declara "todos os direitos reservados"; o mesmo cuidado dos termos vale — **só link e leitura; nada coletado ainda**, aguarda decisão do usuário. O site também expõe a API REST padrão do WordPress (`/wp-json/`), que retorna o texto das páginas, não os dados dos modelos.

## Reddit — "Power BI report for football fans (but not only)"
**Não foi possível abrir**: o navegador integrado bloqueia reddit.com por restrição de segurança e não contornei isso. Se o usuário colar aqui o texto do post e dos comentários mais úteis, eu analiso.

## Já usado antes: dashboards de referência
As imagens SportX, EPL Season Analysis e Futebol Analytics viraram a Fase 2 (`docs/plano-fase2-painel-do-time.md`). O vídeo acima é do mesmo universo do painel "Futebol Analytics" (Power BI + dados da web).

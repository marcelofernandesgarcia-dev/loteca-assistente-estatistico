# CBF como fonte de dados (27/09/2026)

Estado vivo no cofre Obsidian (`Loteca/Notas/CBF como fonte de dados.md`). Este arquivo não contém nenhum dado copiado do site da CBF — só o que descobri sobre a estrutura e as decisões.

## O ponto de partida
Notícia indicada pelo usuário: *CBF anuncia Programa de Apoio à Reestruturação Financeira para clubes da Série B* (05/02/2026). É um comunicado, não uma base de dados. O que interessa ao projeto nela: o **novo formato da Série B em 2026** — 38 rodadas de pontos corridos e, depois, playoffs de ida e volta entre o 3º e o 6º colocados (3º x 6º e 4º x 5º) para definir as duas últimas vagas de acesso; calendário mantido durante a Copa do Mundo; programa de apoio (PARF-B) condicionado ao Fair Play Financeiro, fiscalizado pela ANRESF. Isso pesa no fator "contexto de tabela/motivação" (quem disputa playoff, acesso ou rebaixamento).

## Existe API?
**Não há API pública documentada da CBF.** O site (Next.js) usa `/api/auth/...` só para login — não foi tocado. Os dados aparecem nas **páginas públicas**, já embutidas no HTML (fluxo `self.__next_f.push`):

| Página (padrão de URL) | O que traz |
|---|---|
| `/futebol-brasileiro/tabelas/campeonato-brasileiro/{serie-a\|serie-b}/{ano}` | classificação oficial: posição, pontos, jogos, V/E/D, gols pró/contra/saldo, cartões amarelos/vermelhos, aproveitamento, rodada, últimos 3 jogos, próximo adversário; código e UF de cada time |
| `/futebol-brasileiro/times/campeonato-brasileiro/{serie}/{ano}/{cod_time}` | estatísticas do time (incl. jogos sem sofrer gol), **todos os jogos da temporada** (rodada, data, hora, local, placar, pênaltis) e a lista do elenco |
| `/futebol-brasileiro/atletas/...` | página por atleta (não coletada) |

Não existe `robots.txt` (a rota devolve a página 404). Rotas `/jogos/...` que tentei deram HTTP 500 — não usadas.

## Termos de uso e decisão do usuário
Termos da CBF, item 6: os conteúdos são protegidos por direitos de autor e **"é vedada a cópia, imitação, modificação, reprodução, difusão, transmissão, venda, publicação, distribuição ou utilização, comercial ou não comercial, não especificamente autorizada"**.

Levei a questão ao usuário, com três caminhos (construir desligado e pedir autorização / usar localmente sob demanda / buscar fonte licenciada). **Decisão do usuário (27/09/2026): "fazer uso como usuário acessando o portal e lendo como se fosse o usuário acessando os dados, conforme agendamento."** O risco perante os termos da CBF é dele; ficou registrado. Salvaguardas implementadas:
- lê as páginas como um navegador comum, **uma por vez, 2 s entre chamadas**, e **não repete a coleta se o dado tem menos de 20 h** (`config.CBF_VALIDADE_HORAS`);
- 42 páginas por rodada de coleta (2 tabelas + 40 times); agendamento sugerido 3x por semana, não diário;
- dado guardado **só no banco local** (`loteca.db*` no `.gitignore`); nada da CBF vai para o GitHub; testes usam páginas sintéticas com nomes fictícios;
- não coleta a lista de atletas (minimização: as análises não precisam de nome de pessoa);
- não exibe os escudos hospedados pela CBF; mostra a fonte e a data da coleta na tela;
- chave para desligar tudo: `LOTECA_CBF_HABILITADO=0`.

## Problema técnico resolvido: certificado
O servidor da CBF envia a **cadeia de certificados incompleta** (falta o intermediário). O Windows completa sozinho; o Python com `certifi` falha (`unable to get local issuer certificate`). Solução: `truststore` (usa o repositório de certificados do sistema), **mantendo a verificação de certificado ligada**. Desligar a verificação foi descartado.

## Primeira coleta real (27/09/2026)
Séries A e B 2026: 40 times, 573 partidas, estatísticas e classificação. **Os 40 times foram pareados 1 a 1 com os participantes da Loteca** por UF + nome (`importer/cbf_mapeamento.py`), sem ambiguidade. Conferência cruzada: os 55 gols do Flamengo e o "melhor ataque" citados antes pelo NotebookLM batem com a CBF.

## Defeito encontrado e corrigido no caminho
`participantes` era único só por (nome, tipo): o Atlético-MG e o Atlético-GO (ambos "ATLETICO" na Loteca), Botafogo RJ/SP/PB e América MG/RN viravam **o mesmo participante**, misturando estatísticas. Agora a identidade é (nome, tipo, UF). Migração automática com backup do banco (`loteca.db.bak-AAAAMMDD-HHMMSS`) e reimportação dos concursos. Os percentuais desses times passam a estar corretos.

## Como usar
- Coletar agora: `.venv\Scripts\python scripts\coleta_cbf.py` (`--forcar` ignora a validade de 20 h).
- Na interface: página **Por time** → "Classificação oficial (CBF)" e calendário/resultados da temporada; página **Concurso atual** → anotação "CBF: posição · aproveitamento · últimos jogos" ao lado de cada time do bilhete.

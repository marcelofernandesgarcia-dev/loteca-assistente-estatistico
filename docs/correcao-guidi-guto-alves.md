# Correção: re-análise de guidi/loteria_api e guto-alves/loterias-api (27/09/2026)

Estado vivo no cofre Obsidian (`Loteca/Notas/Correção - guidi loteria_api e guto-alves loterias-api.md`). Cópia de trabalho abaixo.

O usuário pediu para reanalisar esses dois repositórios especificamente. Refiz o teste em vez de confiar na conclusão anterior — e havia um erro a corrigir: eu tinha dito que "nenhuma API de terceiro cobre Loteca". Isso é falso para o `guidi/loteria_api`.

## guto-alves/loterias-api — confirmado, sem correção
`GET https://loteriascaixa-api.herokuapp.com/api` não inclui "loteca" na lista viva de modalidades; `GET .../api/loteca/latest` devolve 404. Não serve para este projeto.

## guidi/loteria_api — correção importante
README lista "loteca" entre as loterias compatíveis (snapshot: 1.240 concursos já na base, medição de 17/06/2026). A URL correta é `api.guidi.dev.br/loteria/loteca/ultimo` (ou `/loteca/<concurso>`) — minha tentativa anterior usou uma URL incompleta e por isso deu 404.

**Bug real encontrado ao testar a rota certa:** a resposta vem HTTP 200 com metadados corretos (número do concurso, datas, faixas de premiação, batendo com a própria CAIXA), mas o campo `listaResultadoEquipeEsportiva` — que deveria trazer os 14 jogos com time e placar — vem vazio/corrompido (array de estruturas vazias aninhadas), tanto para o concurso atual (1271) quanto para um concurso antigo testado (1210). A parte que mais importa para este projeto está com bug nessa API.

Outros pontos do README: desde 12/07/2026 a API bloqueia IP fora do Brasil e aplica rate limit; é serviço de mantenedor único (Digital Ocean, GPL-3.0, sem SLA).

## Conclusão
Mantém-se a decisão de usar o endpoint da CAIXA diretamente — agora pela razão certa: a alternativa que existia (guidi) tem bug na parte crítica (times/placar), não porque "não existe alternativa" em absoluto.

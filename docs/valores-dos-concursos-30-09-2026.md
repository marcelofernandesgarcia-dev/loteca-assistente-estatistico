# Valores de cada concurso: arrecadação, ganhadores, prêmios e acumulados (30/09/2026)

**Pedido do usuário (30/09/2026):** acrescentar as informações dos valores de cada concurso, a quantidade de premiados, os valores distribuídos por ganhador e os valores totais. **Decisões do usuário:** reimportar o histórico completo (sim), mostrar nas telas de "Concurso atual", "Por concurso" e numa página de histórico (sim), não incluir o município dos ganhadores, e procurar na fonte oficial o significado dos campos de acumulado.

## O que a CAIXA publica e o que o app guarda

Resposta do endpoint `/loteca/<n>` (conferida ao vivo no concurso 1272):

| Campo da API | Significado | Fonte oficial | Onde fica |
|---|---|---|---|
| `valorArrecadado` | Arrecadação total do concurso | Manual de Produtos v21, item 18.1.3.12.1 ("Arrecadação total, distribuição e destinação dos valores arrecadados") | `concursos.valor_arrecadado` |
| `valorAcumuladoConcurso_0_5` | Valor acumulado para o próximo concurso de final zero ou cinco | item 18.1.3.12.1 ("Valor acumulado para o próximo concurso final zero ou cinco") e item 6.3.4.2, 3ª faixa | `concursos.valor_acumulado_final_0_5` |
| `valorAcumuladoConcursoEspecial` | Valor acumulado para a Loteca Especial | item 18.1.3.12.1 ("Valor acumulado para o sorteio especial da Loteca Especial") e item 6.3.4.2, 4ª faixa | `concursos.valor_acumulado_especial` |
| `valorAcumuladoProximoConcurso` | Acumulado na 1ª faixa do concurso seguinte (quando ninguém faz 14) | item 6.3.4.2.4 | `concursos.valor_acumulado_proximo` |
| `valorEstimadoProximoConcurso` | Estimativa de prêmio do próximo concurso | item 18.1.3.12.1 | `concursos.valor_estimado_proximo` (já existia) |
| `listaRateioPremio[]` | Ganhadores e valor por ganhador de cada faixa | item 18.1.3.12.1 | `premiacoes` (já existia) |

**Nível de certeza do mapeamento:** o Manual lista as informações publicadas e a API usa campos de mesmo sentido. A correspondência entre o nome do campo e o item do Manual é por significado, não por documentação da API (que não é oficial). **Conferido nos dados** (30/09/2026, depois de importar os 1.272 concursos): nos concursos 1260 a 1272, o acumulado de final 0/5 cresce, a cada concurso, exatamente 3,85% da arrecadação do concurso e **volta a começar nos concursos 1265 e 1270** (finais 5 e 0), como o item 6.3.4.2 descreve. No 1272, os R$ 298.574,51 são a soma de 3,85% da arrecadação de 1270, 1271 e 1272. O acumulado para a Loteca Especial cresce igual, mas não zera nesses concursos. O próximo concurso de final 0/5 informado pela API é o 1275.

O campo `indicadorConcursoEspecial` da API **não foi interpretado** (significado não confirmado), e o concurso Loteca Especial, que tem divisão própria (90% / 10%, item 6.3.4.3), não é calculado pelo app.

## Regra oficial de distribuição (Manual de Produtos v21, item 6.3.4)

55,00% da arrecadação vão para prêmios, com desconto do Imposto de Renda. No concurso regular, desse valor: 70% na 1ª faixa (14 acertos), 10% na 2ª (13), 10% acumulam para a 1ª faixa dos concursos de final zero ou cinco e 10% acumulam para a Loteca Especial. Sem ganhador em uma faixa, o prêmio acumula para a 1ª faixa do concurso seguinte.

**Decisão: o app não calcula valores por essa regra.** Medido nos dados, ela não reproduz o que foi pago ao longo de todo o histórico. Na 2ª faixa (a única sem mistura com acumulado), o pago sobre o previsto pela regra foi de 0,70 a mais de 1,0, e só 12 de 836 concursos ficaram em 0,69 a 0,71. Em concursos antigos (800 a 1000, 400 a 600) o acumulado nunca cresce 3,85% da arrecadação. A regra descreve bem os concursos recentes, mas as regras anteriores eram outras (o Manual v21 é de agosto de 2026). A tela mostra só o que a CAIXA publicou e explica isso num quadro recolhível.

## O que é dado e o que é conta

- **Dado publicado:** arrecadação, acumulados, ganhadores e valor por ganhador.
- **Conta do app:** total pago na faixa = ganhadores × valor por ganhador; total pago no concurso = soma das faixas.
- **Limite:** o total pago **não é retorno sobre a arrecadação**. Ele já desconta o Imposto de Renda e a 1ª faixa soma o que acumulou de concursos anteriores. Exemplo do 1272: arrecadação R$ 2.570.788,00; total pago R$ 1.393.416,75 (R$ 1.294.441,38 de 1 ganhador de 14 + 13 × R$ 7.613,49).
- **Dado ausente:** vira "sem dado", nunca zero. Achado na importação: para os **363 primeiros concursos (1 a 363)** a API devolve arrecadação 0,0, que é "não informado" (arrecadação zero é impossível); a arrecadação existe de 364 em diante (909 concursos). Os acumulados e a premiação existem em todos os 1.272.

## Onde aparece

- **Concurso atual:** bloco "Valores do concurso N" logo abaixo do resultado do último concurso apurado.
- **Por concurso:** a seção "Premiação" traz o mesmo bloco para qualquer concurso.
- **Premiações** (página nova): resumo do histórico, gráficos do prêmio de 14 acertos e da arrecadação, tabela dos 50 concursos mais recentes do período e detalhe de um concurso.

## Como preencher e manter

- `scripts/importar_valores.py`: preenche arrecadação, acumulados e premiação dos concursos já importados, sem tocar em jogos nem participantes. Retomável, com backup do banco antes. Cerca de 20 minutos para 1.272 concursos.
- `importer/caixa_client.importar_concurso` passa a gravar os valores sozinho; como `scripts/atualizar_tudo.py` (e o lançador, ao abrir) importam o último apurado, os concursos novos entram preenchidos.

## Fora do escopo (por decisão do usuário)

Município dos ganhadores (a API traz, é dado público agregado, mas não ajuda a análise estatística).

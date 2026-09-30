# Estudo: sugestões de alteração em jogos complexos (E1 a E4) — 30/09/2026

**Pedido do usuário:** "Estude a possibilidade de sugerir melhorias de sugestões de alterações em jogos mais complexos." **Decisão do usuário:** estudar e testar antes de mostrar qualquer sugestão na tela.

**Situação:** estudo concluído em 30/09/2026. **As 5 recomendações do fim foram aprovadas pelo usuário na mesma data e implementadas** (ver "Implementação" no fim). O lançador também foi confirmado nas opções recomendadas.

Código: `stats/otimizacao_bilhete.py` (E1 a E3), `stats/estudo_sugestoes.py` e `scripts/estudo_sugestoes.py` (E4). Números brutos: `docs/estudo-sugestoes-resultado.json`. Para reproduzir: `.venv\Scripts\python scripts\estudo_sugestoes.py` (só leitura do banco, cerca de 4 segundos).

## Como foi testado

- **Base:** 1.127 concursos passados com os 14 jogos apurados.
- **Sem olhar o futuro:** o percentual de cada jogo foi calculado só com os concursos anteriores. É o mesmo método da página "Confiabilidade do modelo".
- **Comparação justa:** as estratégias foram comparadas **com o mesmo custo**. Isso quer dizer o mesmo número de duplos e de triplos, porque 2^d × 3^t só se repete com o mesmo par.
- **Limitação:** o teste usa o modelo histórico dos clubes. Não inclui o Elo das seleções (que hoje é melhor) nem o ajuste de notícias (a tabela continua vazia).

## E1: complexidade de cada jogo

A regra marca três níveis, com os motivos e o número que sustenta cada um:
- favorito abaixo de 45%;
- 1º e 2º resultado separados por menos de 10 pontos;
- time com pouco histórico;
- o favorito do percentual indo pior no ano em curso.

**Resultado nos 16.973 jogos testados:**

| Complexidade | Jogos | O favorito acertou |
|---|---|---|
| baixa | 12.183 | 49,7% |
| média | 3.937 | 44,0% |
| alta | 853 | 37,2% |

A marca separa os jogos de verdade: quanto mais complexo, menos o favorito acerta. Mesmo no nível "baixa", porém, o favorito acerta só metade das vezes.

O sinal "vai pior no ano em curso" não entrou no teste, porque o histórico não tem o ano em curso de cada época.

## E2 e E4: onde pôr os duplos e triplos

Três estratégias, com o mesmo custo:
- **cálculo exato:** a melhor distribuição pelos percentuais;
- **regra simples:** a que o app já usa, com triplos e duplos nos jogos de favorito mais fraco;
- **aleatório:** duplos e triplos em jogos sorteados.

| Duplos + triplos | Custo | Acertos médios: exato | regra | aleatório | 13 ou mais (exato / regra) | 13 ou mais previsto pelo app |
|---|---|---|---|---|---|---|
| 1 + 0 | R$ 4 | 7,04 | 7,06 | 7,01 | 0 / 0 | 10,0 |
| 0 + 1 | R$ 6 | 7,34 | 7,35 | 7,25 | 1 / 1 | 12,9 |
| 2 + 0 | R$ 8 | 7,37 | 7,37 | 7,35 | 0 / 0 | 14,7 |
| 1 + 1 | R$ 12 | 7,66 | 7,66 | 7,60 | 1 / 1 | 19,1 |
| 3 + 0 | R$ 16 | 7,67 | 7,68 | 7,55 | 1 / 1 | 20,8 |
| 2 + 1 | R$ 24 | 7,96 | 7,97 | 7,79 | 2 / 2 | 26,9 |
| 4 + 1 | R$ 96 | 8,53 | 8,55 | 8,35 | 9 / 11 | 49,7 |
| 3 + 2 | R$ 144 | 8,82 | 8,84 | 8,59 | 15 / 18 | 62,8 |

**Achados:**
1. **O cálculo exato não acrescenta nada à regra simples.** Com 95% de confiança, não houve diferença perceptível em nenhum dos 8 custos. Em muitos concursos os dois escolhem a mesma coisa (892 de 1.127 no caso de um duplo só).
2. **Onde pôr o duplo ou o triplo importa** em relação a pô-los ao acaso. A diferença foi de +0,07 a +0,23 acerto por concurso, perceptível em 6 dos 8 custos. As exceções foram 1 duplo e 2 duplos.
3. **Nenhuma estratégia fez 14 em 1.127 concursos,** nem com R$ 144 por concurso.
4. **A "chance de acertar" que o app mostra é otimista demais.**
   - Somando os 8 custos, o app previa 217 bilhetes com 13 ou mais; aconteceram 29, cerca de 7 vezes menos.
   - Para 14 acertos, previa 29 e aconteceram 0.
   - Nos últimos 300 concursos o quadro se repete: 10,8 previstos contra 2 ocorridos, com R$ 144.
   - O motivo é que os percentuais dos favoritos são mais confiantes do que a realidade, e a conta supõe esses percentuais corretos.
   - Isso afeta a "Análise do palpite" e a tabela de versões, que hoje mostram "1 em X".

## E2 e E4: sugestão de alteração num bilhete já marcado

Aqui o teste simula um bilhete montado **sem critério**: duplos e triplos em jogos sorteados, e 25% dos secos marcados contra o favorito. Nesse bilhete foi aplicada a melhor troca de um passo, que mantém o custo. Ela só é sugerida quando aumenta a chance em 10% ou mais.

| Bilhete | Recebeu sugestão | Ganhou acerto | Perdeu | Igual | Diferença média |
|---|---|---|---|---|---|
| 1 duplo | 1.120 | 628 | 219 | 273 | **+0,36** acerto (perceptível) |
| 2 duplos + 1 triplo | 1.119 | 582 | 174 | 363 | **+0,35** (perceptível) |
| 3 duplos + 2 triplos | 1.120 | 542 | 193 | 385 | **+0,30** (perceptível) |

**De onde vem o ganho.** Refiz o teste sem as marcações contra o favorito, deixando só a mudança de lugar dos duplos e triplos:
- 1 duplo: +0,03, sem diferença perceptível;
- 2 duplos + 1 triplo: +0,10;
- 3 duplos + 2 triplos: +0,15.

O resto do ganho vem de trocar a coluna "contra o favorito" pela coluna favorita.

**Leitura:** a sugestão ajuda, mas pouco, cerca de um acerto a mais a cada três concursos. Sozinha, nunca leva a 13 ou 14.

## E3: economia

Para cada duplo ou triplo, o app calcula quanto se economiza tirando a coluna menos provável e quanto da chance se perde. O resultado vem ordenado pela menor perda por real. Nunca sugere tirar o último duplo ou triplo, porque o volante exige ao menos um.

Não houve teste próprio: é o mesmo raciocínio do E2 no sentido contrário. Tirar a cobertura do jogo menos incerto custa menos acerto.

## Recomendações (dependem da sua decisão)

1. **Mostrar a complexidade de cada jogo (E1),** com os motivos, na análise do palpite e no quadro do ano em curso. O efeito foi validado: 49,7% / 44,0% / 37,2%.
2. **Sugestões de alteração pelo mesmo custo, pela regra simples, sem o cálculo exato:**
   - "leve o duplo/triplo do jogo A para o jogo B, mais incerto";
   - "no jogo C você marcou contra o favorito".
   - Cada uma sempre acompanhada do efeito medido: "nos 1.127 concursos testados, esse tipo de ajuste rendeu em média +0,1 a +0,35 acerto por concurso; não leva a 13 ou 14 sozinho".
   - Continua valendo a sua regra de sugestão do app: no máximo um duplo ou um triplo.
   - Estas são **sugestões de alteração do seu bilhete**: nunca aumentam o custo nem o número de duplos e triplos que você escolheu.
3. **Corrigir a "chance de acertar" mostrada hoje (achado 4).** Ao lado do "1 em X", mostrar o que aconteceu de fato com bilhetes do mesmo custo nos concursos testados. Exemplo: "com R$ 24, 13 ou mais em 2 de 1.127 concursos; 14 em nenhum". Ou trocar o número pela frequência observada. É uma correção de algo que já está na tela, por isso precisa da sua decisão.
4. **Economia (E3)** entra junto com a recomendação 2, como leitura: "se quiser gastar menos, o duplo que menos rende é o do jogo X".
5. **Medir o seu comportamento real** assim que houver bilhetes e versões salvas. Este teste usou um bilhete simulado; as versões gravadas no banco vão permitir medir as suas mudanças de verdade (etapa 2).

## Implementação (30/09/2026, depois da aprovação)

1. **Complexidade de cada jogo:** coluna "Complexidade do jogo" (nível e motivos) no quadro do ano em curso da página "Concurso atual" e na tabela da "Análise do seu palpite". O sinal "vai pior no ano em curso" só entra quando as duas partes têm dado da mesma fonte e sem amostra pequena (`stats/sugestoes_bilhete.melhor_no_ano`). Uma legenda traz o que o teste mediu (cerca de 50%, 44% e 37% de acerto do favorito).
2. **Sugestões de alteração pelo mesmo custo** (`stats/sugestoes_bilhete.py`): até 3 trocas de um passo, cada uma só com o mesmo número de apostas e a mesma quantidade de duplos e triplos (conferido no código; uma sugestão que mude o custo é descartada). Mais uma linha quando há jogo marcado contra o favorito dos dados. O efeito medido aparece ao lado, e só quando há alteração sugerida.
3. **Chance mostrada corrigida** (`stats/calibracao_bilhete.py`): os rótulos viraram "(pelos percentuais)" e, ao lado, vem o que aconteceu de fato com bilhetes do mesmo custo nos concursos passados, calculado a partir do banco e atualizado quando entra concurso novo. Com menos de `config.CALIBRACAO_MIN_CONCURSOS` (200) concursos, a tela diz que não há base suficiente. A tabela de versões ganhou uma legenda no mesmo sentido.
4. **Economia:** até 2 leituras "se quiser gastar menos", ordenadas pela menor perda de chance por real.
5. **Comportamento real:** as versões gravadas no banco alimentam "Minhas versões: as mudanças ajudaram?" em "Meus bilhetes", que só tira conclusão com `config.VERSOES_CONCURSOS_MINIMOS` (10) concursos.

Limitações mantidas: o teste usa o modelo histórico dos clubes (sem o Elo das seleções nem as notícias), e a sugestão do próprio app continua em no máximo um duplo ou um triplo. "Onde um duplo rende mais" continua existindo e agora avisa que aumenta o custo.

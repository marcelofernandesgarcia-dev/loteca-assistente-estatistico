# P1: força das seleções pela base aberta (30/09/2026)

Primeiro item da priorização estatística (`priorizacao-estatistica-30-09-2026.md`). Autorizado pelo usuário em 30/09/2026.

## Problema

Metade dos participantes do concurso 1272 são seleções (14 de 28), mas a base da Loteca tem só 2 a 45 jogos de cada uma (523 jogos entre seleções em 17.784). Com menos de 5 jogos, o modelo anterior cai na frequência geral 47/26/27; com poucos, exagera (Alemanha x Grécia 80%). Dos 420 jogos de seleções avaliados no teste, o modelo anterior usou a frequência geral em 266.

## Fonte e licença

`data/externos/international_results.csv`, do projeto público `martj42/international_results` (GitHub). **Licença CC0-1.0** (domínio público; texto da licença lido no repositório). 49.547 jogos de seleções masculinas, de 1872 a 26/08/2026 (verificado no arquivo baixado; a página do projeto dizia "até 2024", o que estava desatualizado). Traz data, times, placar, torneio, cidade, país e se o campo era neutro. 3,7 MB, versionado no repositório por ser domínio público.

Os 74 nomes de seleção da Loteca foram ligados aos nomes da base em `data/selecoes-nomes.csv`; todos existem na base. Mesmo a seleção com menos jogos na Loteca (Gibraltar, 2) tem 109 jogos desde 2014 na base.

## Método

1. **Rating Elo** calculado jogo a jogo por toda a base, só com o passado de cada jogo. Vitória contra time mais forte vale mais; goleada e torneio importante mexem mais no rating; jogar em casa dá uma vantagem que vale só se o campo não é neutro.
2. **Curva** que converte a diferença de rating em chance de 1, X e 2 (regressão logística ordenada, com o campo neutro ou não como segunda variável), ajustada por máxima verossimilhança. Sem `scipy`: usa um minimizador Nelder-Mead próprio.
3. **Campo desconhecido.** Antes do jogo não se sabe se o campo é neutro. O app usa a fração de jogos de seleções da Loteca em campo não-neutro nos últimos 5 anos (57% no momento).

Os pesos do Elo (K por torneio, vantagem de 100 pontos) seguem a convenção dos sistemas Elo de futebol de seleções. **Não foram ajustados** aos jogos da Loteca, nem conferidos numa fonte nesta sessão: são parâmetros em `config.py`.

## Teste (jogo a jogo, sem olhar o futuro)

- Curva ajustada só com jogos da base **antes de 2010**; teste com jogos da Loteca **de 2010 em diante**.
- Cada jogo da Loteca é casado com o da base (mesmos times, data com até 3 dias de diferença); o rating usa só jogos da base **estritamente anteriores** ao dia daquele jogo.
- Das 523 partidas de seleções da Loteca, 509 casaram; 420 entram no teste (depois de 2010 e com previsão do modelo anterior).

| Modelo | Acerto do favorito | Perda logarítmica (menor é melhor) |
|---|---|---|
| **Elo, campo desconhecido (o que o app usa)** | **59,0%** | **0,9205** |
| Elo, campo conhecido (só para dimensionar) | 59,8% | 0,9149 |
| Modelo anterior (só jogos da Loteca) | 45,0% | 1,0927 |
| Frequência histórica simples | 41,7% | 1,0899 |

O Elo é melhor que o modelo anterior por **0,172 na perda logarítmica (erro padrão 0,025)**, com 95% de confiança. O modelo anterior nem superava a frequência simples nesses jogos. Não saber o campo custa só 0,006.

**Robustez.** Variei os pesos (K x0,5, x1, x2; vantagem 0, 100, 150), sem escolher o melhor: o ganho ficou entre 0,156 e 0,172 nas 9 combinações, sempre "melhor". Não depende de um valor específico.

## O que mudou no app

- Jogo entre duas seleções: o percentual vem do Elo (`stats/percentual.py`, chave `config.MODELO_SELECOES`, padrão "elo"). Para voltar ao anterior: variável de ambiente `LOTECA_MODELO_SELECOES=historico`.
- Jogo com clube: nada muda.
- Sem a base (arquivo ausente), o app registra um aviso no log e cai no modelo anterior.
- Página "Confiabilidade do modelo": seção nova com o teste acima. Ficha do time: texto explicando a origem do percentual.
- **Concurso 1272, antes e depois (1 / X / 2, em %):**

| Jogo | Antes | Depois |
|---|---|---|
| Inglaterra x Espanha | 21 / 27 / 52 | 29 / 30 / 41 |
| Dinamarca x País de Gales | 47 / 26 / 27 | 67 / 21 / 12 |
| Sérvia x Holanda | 20 / 20 / 60 | 19 / 26 / 55 |
| Gibraltar x Andorra | 47 / 26 / 27 | 42 / 30 / 28 |
| Noruega x Portugal | 17 / 22 / 60 | 39 / 30 / 30 |
| Israel x Irlanda | 47 / 26 / 27 | 37 / 31 / 33 |
| Alemanha x Grécia | 80 / 13 / 7 | 67 / 21 / 12 |

A sugestão do app mudou: o triplo, que estava em Fortaleza x Athletic Club, passa para Israel x Irlanda (o jogo mais incerto agora), e a chance estimada de 14 acertos da sugestão passa de 1 em 1.275 para 1 em 3.297.

## Limitações

- **Torneios de base e feminino.** A Loteca lista alguns jogos de Sub-20 e da Copa feminina com o nome da seleção principal (14 dos 523 jogos não têm par na base). O app não consegue saber isso antes do jogo; para esses jogos o Elo da seleção masculina principal não vale.
- **Prorrogação.** A base soma a prorrogação; a Loteca conta os 90 minutos. Em 8 jogos (mata-mata de Copa do Mundo) o resultado difere. Efeito pequeno no rating.
- **Campo desconhecido.** Tratado por mistura, custa pouco no teste.
- **Só seleções masculinas principais**, e só jogos entre duas seleções. Clube contra seleção continua no modelo anterior.
- **Base aberta mantida por terceiros.** Atualizar: baixar o arquivo de novo (comando em `data/externos/LEIAME.md`).

# Priorização pelo ganho estatístico (30/09/2026)

Pedido do usuário: "priorize apenas as informações que possam fortalecer as análises estatísticas, que é o objetivo do aplicativo". Este documento reordena tudo que resta do estudo de fontes (`estudo-fontes-qualitativas-29-09-2026.md`) por um critério só: **a informação melhora uma conta que o app já faz, ou permite testar uma hipótese?**

## O que o app sabe hoje (medido no banco real)

- O teste do modelo (B3) mostrou que o percentual atual **perde da frequência histórica simples**. O ponto fraco é a falta de amostra por time, não a falta de "contexto".
- **Seleções:** só 523 dos 17.784 jogos apurados (3%), mas são **14 dos 28 participantes do concurso atual**. Seis têm menos de 10 jogos na base (Gibraltar 2, Andorra 4, Israel 5, País de Gales 7, Irlanda 10, Noruega 13). Nesses jogos o app usa a média geral 47/26/27, por isso vários jogos do concurso 1272 mostram números idênticos.
- **Campeonato da CBF:** só a temporada 2026 (573 jogos). O erro da projeção (3,7 pontos por time) foi medido em **uma** temporada.
- **Notícias:** a tabela `fatores_externos` está **vazia**. A varredura nunca rodou de verdade no banco real, então nenhum fator vindo de notícia tem histórico.

## Critério

Uma informação entra na frente quando: (1) é número comparável entre times; (2) tem histórico para testar contra o resultado; (3) cobre muitos jogos do concurso; (4) vem de fonte já autorizada ou aberta; (5) não é opinião.

## A ordem

### Urgente, porque o atraso não se recupera
**P0. Fazer a varredura de notícias acumular histórico.** O RSS só devolve os últimos 10 dias: o que não for guardado semana a semana se perde para sempre. Sem isso, os sinais de lesão, suspensão, contratação, técnico e salário nunca poderão ser testados. Ação sua: criar a tarefa agendada de `scripts/atualizar_tudo.py` (comando no README); o Claude não altera configuração do sistema.

### Maior ganho estatístico (dado novo)
**P1. Resultados de seleções, base aberta. ✅ FEITO em 30/09/2026** (ver `p1-selecoes-elo-30-09-2026.md`): o Elo acerta o favorito em 59,0% dos 420 jogos de seleções testados, contra 45,0% do modelo anterior, com ganho de 0,172 na perda logarítmica (95% de confiança); o arquivo vai até 26/08/2026, então o ponto a conferir abaixo estava resolvido. Descrição original: conjunto "International Football Results" (49.459 jogos, 1872 a 2024, licença **CC0-1.0**, domínio público; leitura da página do projeto em 30/09/2026). Traz data, placar, torneio, local e se o campo era neutro. Efeito: dá força de ataque e defesa para as 74 seleções da Loteca, onde hoje há 2 a 45 jogos por seleção. Precisa de uma lista curada de nomes português-inglês (INGLATERRA = England etc.), no padrão de `data/apelidos-participantes.csv`. Medição: teste jogo a jogo nos 523 jogos de seleções da Loteca, com e sem a base nova. **Ponto a conferir antes de tudo:** a página fala em dados "até 2024"; se o arquivo parar aí, faltam os jogos de 2025 e 2026, que são os mais relevantes.

**P2. Temporadas 2019 a 2025 da CBF, Séries A e B. ✅ FEITO em 30/09/2026** (ver `p2-temporadas-cbf-30-09-2026.md`): 5.892 jogos no banco (eram 573), 11 das 14 temporadas conferem exatamente com a classificação final da CBF e as 3 diferenças estão explicadas. Achado: o ritmo dos últimos 5 jogos errou mais que o ritmo da temporada em 13 de 13 temporadas. Descrição original: verificado hoje, sem gravar nada: as páginas de classificação e de cada time existem para 2019, 2021, 2022, 2023, 2024 e 2025 nas duas séries, com 380 jogos por série e por ano, placar, data e estádio. Isso dá **5.320 jogos** contra os 573 de hoje. Mesma fonte e mesmo método já em uso (2 s entre páginas, cerca de 280 páginas, uns 10 minutos, uma vez só). Efeito: o erro da projeção passa a ser medido em 7 temporadas e não em 1; o modelo do campeonato (B2) pode ser testado de verdade; a Q4 ganha amostra. (2020 não foi conferida.)

### Transformar dado em conhecimento
**P3. Q4, análise de associação.** Cada fator contra o desempenho seguinte, com tamanho da amostra e cuidado com falso achado (muitos testes ao mesmo tempo). Candidatos que **já existem na base** e podem ser testados assim que P2 entrar: mando, forma recente, sequência, zona da tabela, cartões por rodada, e "SAF no nome da CBF" por ano. Fatores de notícia só depois de meses de P0.

**P4. Q6 (faixa por coluna) e Q7 (anti-manada).** Usam só os 1.272 concursos que já temos. Sem fonte nova.

### Só com baixo custo
- **Cartões (parte do Q0):** já estão na base por rodada. Entram como variável da Q4, sem fase própria.
- **Q3 (RSSF/ANRESF):** uma leitura de pesquisa. Só entra se for um indicador estruturado e com histórico.

### Fora da prioridade (ganho estatístico baixo)
| Item | Por que sai da frente |
|---|---|
| Artilharia individual (parte do Q0) | Descreve jogadores; o resultado do jogo já está no gol do time, que o modelo usa. Ganho quase nulo para prever resultado |
| Canais de YouTube (Q2b) | Repete as notícias que já lemos; título de vídeo é ruído e opinião; sem histórico |
| Sites oficiais dos 40+ clubes (Q2c) | Custo alto (cada site é diferente), dado não comparável entre clubes, sem histórico. Fica o que já existe: links de consulta manual |
| Skill de pesquisa de fonte oficial | Ferramenta de processo, não informação |
| Fechamento reduzido com garantia (Q9) | Otimização de custo da aposta, não informação. Mantido por decisão sua, em espera |

## Perguntas para o usuário
1. Começo pelo **P1 (seleções)**? Antes, preciso baixar `results.csv` do GitHub do projeto (fonte aberta, CC0; o tamanho eu confirmo ao baixar).
2. Autoriza o **P2** (coletar 2019 a 2025 da CBF, mesma fonte e método já usados em 2026)?
3. Você cria a tarefa agendada do **P0**?

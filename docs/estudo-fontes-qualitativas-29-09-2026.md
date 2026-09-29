# Estudo: fontes qualitativas de desempenho e potencialização do projeto (29/09/2026)

## Contexto

O usuário pediu, depois de testar o app, que as análises considerem "referências reais de melhorias ou pioras": contratações bem feitas, jogadores machucados, suspensos, satisfação da torcida com o elenco e com a classificação, coletividade/entrosamento/talento individual, idade de jogadores, técnicos, comissão técnica, presidentes, torcidas, situação financeira e atraso de pagamento — reconhecendo que futebol é complexo (jogo coletivo, contato físico, múltiplas variáveis). Pediu para estudar melhorias em coleta, registro, análise e metodologia, e avaliar a criação de skills/agentes.

Este documento é o estudo pedido — não implementa nada. Cada fonte foi checada antes de entrar na tabela (não incluí nada por suposição), seguindo a mesma disciplina já usada para o REC da CBF (C1).

## O que já existe hoje

| Fator já coberto | Como | Limite conhecido |
|---|---|---|
| Lesão, suspensão, desfalque, tendência de imprensa | Notícia (RSS), palavra-chave, com as barreiras do C2 (nome no título, nega negação) | Precisão só testada com manchete fictícia minha, não validada pelo usuário; teto de ajuste ±8 pontos |
| Zona de classificação (briga por título/acesso/rebaixamento) | REC oficial da CBF (C1) | Só Séries A e B |
| Sequência, aproveitamento recente x temporada, força do calendário, mando | Cálculo próprio sobre os jogos da CBF (E2-E4) | Só Séries A e B |

## Fontes novas avaliadas — tabela de viabilidade

Cada linha foi checada nesta sessão (não é suposição) ou fica marcada como "a confirmar".

| Fator pedido | Fonte real | Viabilidade | Observação |
|---|---|---|---|
| **Contratações** (nova, saída, elenco em movimento) | **`bid.cbf.com.br`** -- Boletim Informativo Diário. **Confirmado nesta sessão**: tem uma consulta pública, sem login, por UF e por clube, com as publicações oficiais de registro de atleta. | **Alta** -- fonte oficial, pública, sem cadastro. | "Bem feita" (qualidade da contratação) é julgamento, fora de alcance objetivo -- mas **volume de contratações/saídas num período** (giro de elenco) é medível e é um proxy razoável de instabilidade, sem precisar avaliar mérito. |
| **Troca de técnico** | Notícia (mesma infraestrutura do C2, com novas palavras-chave: "demitido", "demissão", "anuncia novo técnico", "apresentado como treinador") | **Alta** -- reaproveita o que já existe. | É um dos fatores mais estudados em análise esportiva séria (efeito de curto prazo de troca de comando é bem documentado). |
| **Atraso de pagamento / situação financeira** | (a) Notícia ("salário atrasado", "elenco ameaça greve", "paralisação", "vaquinha para viagem") -- viável agora, mesma infraestrutura. (b) **RSSF/ANRESF** (Regulamento do Sistema de Sustentabilidade Financeira / Agência Nacional de Regulação e Sustentabilidade do Futebol), citados nos REC que já li para o C1 -- **não confirmei ainda** se há um painel público de situação financeira por clube; fica como pesquisa futura, não suposto. | **Média** (via notícia, já) / **a confirmar** (via RSSF/ANRESF) | Atraso salarial é fato real e recorrente no futebol brasileiro, frequentemente noticiado -- entra pela mesma porta do C2. |
| **Satisfação da torcida com o elenco** | Sem fonte objetiva direta. Proxy possível: frequência de notícia com tom negativo ("crise", "pressão", já existe) ou público presente no estádio (ver linha abaixo). | **Baixa / só proxy** | Análise de sentimento em rede social exigiria raspagem de Twitter/X ou Instagram -- APIs pagas/restritas, ToS incerto, alto risco metodológico (amostra não representativa) e de custo. **Não recomendo agora.** |
| **Satisfação com a classificação** | A zona de tabela (C1) já é um proxy objetivo -- "insatisfação" pode ser inferida de estar abaixo do esperado pela zona, não medida diretamente. | **Já existe, como proxy** | Não é a satisfação em si, é a situação que costuma gerar satisfação/insatisfação. |
| **Público presente / torcida** | A CBF pode publicar público por partida em algumas competições -- não confirmado nesta sessão. | **A confirmar** | Indireto como proxy de ânimo da torcida. |
| **Coletividade, entrosamento, talento individual** | Exigiria dado tático (passes, xG, distância percorrida, etc.) -- nenhuma fonte já estudada neste projeto tem isso (Driblab foi avaliado antes e não contratado). | **Fora de alcance agora** | Só com provedor pago (Opta, Sofascore, Driblab). Registro para o futuro, não descartado. |
| **Idade dos jogadores, elenco** | O CBF SNR teria isso, mas **o projeto já decidiu não coletar elenco** (minimização de dado, registrado no início do projeto). | **Decisão já tomada -- precisa ser revisitada explicitamente, não meramente contornada** | Reverter a decisão de minimização é uma escolha sua, não uma implementação técnica só. |
| **Comissão técnica, presidentes de clube** | Notícia (troca de cargo, eleição) | **Média, mas baixo valor sozinho** | Mais especulativo; eleição de presidente tem efeito indireto e lento. |

## O que fica fora, e por quê

- **Sentimento de torcida via rede social:** custo, ToS, e principalmente risco metodológico -- amostra de quem posta não representa a torcida toda, e o projeto já tem o princípio de "proibido fabricar dado" quando a amostra é fraca.
- **Dado tático fino (xG, passes, entrosamento):** exigiria contratar um provedor pago -- decisão financeira do usuário, não técnica.
- **Elenco/idade dos jogadores:** contraria a decisão de minimização já tomada; só entra se o usuário reverter essa decisão de propósito.

## Complemento (mesmo dia): sites oficiais, canais/influencers, jornalistas, sites específicos

Pedido do usuário, na sequência do estudo acima. Cada fonte foi checada ao vivo nesta sessão antes de entrar aqui.

### Sites oficiais de clubes e seleções

**Checado: `flamengo.com.br/noticias`.** Achado importante: o site tem uma categoria própria **"Futebol" com "Boletim Médico"** -- ex.: *"Boletim Médico - De Arrascaeta"*, publicado pelo próprio clube. É a fonte de lesão **mais confiável que existe** (o clube falando de si mesmo, não imprensa especulando) -- muito melhor que o sinal por palavra-chave em notícia de terceiro que o C2 usa hoje.

**Viabilidade:** alta em valor, **cara em escala** -- são mais de 40 clubes (Séries A e B), cada um com estrutura de site e nome de categoria diferentes (não há padrão nacional, diferente da CBF que é uma fonte só para todos). Um "raspador genérico" não funciona; cada clube precisa de um mapeamento próprio (URL da categoria de notícia, como identificar "Boletim Médico"), crescendo aos poucos -- mesmo modelo do `data/apelidos-participantes.csv`, que também cresce um item de cada vez.

**Proposta:** priorizar só os clubes de maior amostra na Loteca (os que mais aparecem na grade) e crescer a lista aos poucos, não tentar os 40 de uma vez. Cadastro num CSV novo (ex. `data/fontes-oficiais-por-clube.csv`: participante, domínio, padrão da categoria de notícia/boletim médico).

### Canais e influencers (YouTube)

**Checado: canal CazéTV.** Confirmado que **todo canal do YouTube tem um feed RSS público, sem chave de API e sem login** -- `youtube.com/feeds/videos.xml?channel_id=...`. O `channel_id` é uma busca única por canal (não por vídeo), leve.

**Mas:** o feed traz TODO o conteúdo do canal, não só futebol -- o primeiro vídeo do CazéTV no teste era de tênis de mesa. Precisaria do mesmo filtro já usado em notícia (nome do participante + termo de futebol no título) -- é viável com a infraestrutura que já existe, não é uma fonte totalmente nova de mecanismo, só mais um "veículo" na mesma lógica.

**Distinção importante entre canal/jornalista e influencer:** título de vídeo que **relata um fato** (ex.: "FLAMENGO CONFIRMA LESÃO DE FULANO") pode ser tratado como notícia, igual ao C2. Título que é **opinião ou palpite** (ex.: "MEU PALPITE PRO CLÁSSICO", "ACHO QUE O TIME VAI GANHAR") **não deve virar sinal** -- isso importaria a opinião de outra pessoa como se fosse dado, contrariando o princípio já seguido no projeto de que "saída de modelo (ou de opinião) é insumo, nunca decisão". Proponho: só extrair sinal de título que descreve fato (lesão, suspensão, contratação, boletim médico), nunca de título que é previsão ou palpite de resultado.

### Jornalistas específicos

Se o jornalista publica em `ge.globo.com`, `espn.com.br` ou no site oficial de um clube -- **já está coberto** pela busca por site já existente. Se só publica em rede social pessoal (X/Twitter, Instagram) -- mesma limitação já registrada para "satisfação da torcida": custo de API, termos de uso restritivos, e o conteúdo lá tende a ser opinião, não fato verificável.

### Sites específicos

Pedido genérico demais para avaliar sem exemplo concreto -- mesmo processo já usado neste projeto (você traz o link, eu leio e avalio antes de propor, como fiz com o REC e o BID). Se tiver sites específicos em mente, me diga quais.

## Plano em fases (atualizado com o complemento)

### Fase Q1 -- estender a infraestrutura de notícia já existente (barato, sem fonte nova)
Adicionar categorias de sinal em `config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL`: troca de técnico, atraso de pagamento/crise financeira, giro de elenco (via notícia de contratação/saída, complementar ao BID). Mesmas barreiras do C2 (nome no título, negação anula). Nenhuma tabela nova -- reaproveita `fatores_externos`.

### Fase Q2 -- pesquisar e, se der, integrar o BID como fonte oficial de contratações
Antes de codificar: ler a página pública do BID com mais profundidade (que dado exatamente aparece por consulta, formato, se dá para automatizar sem login), documentar em `docs/` como fiz com o REC, e **te trazer o achado antes de decidir coletar**. Se viável: uma tabela nova (`bid_movimentacoes` ou similar) e uma métrica de "giro de elenco" (contratações + saídas numa janela) por participante.

### Fase Q3 -- pesquisar RSSF/ANRESF
Mesma disciplina: ler antes de propor. Ainda não confirmei se existe painel público de situação financeira -- essa fase só decide o que fazer depois dessa leitura.

### Fase Q2b -- canais do YouTube como mais um "veículo" de notícia
Levantar `channel_id` dos canais que você já tinha indicado (CazéTV, TNT Sports Brasil, Desimpedidos, Canal GOAT), incluir como fonte na varredura com o MESMO filtro do C2 (nome + palavra-chave de fato, nunca palpite/opinião). Barato -- reaproveita tudo, só soma feeds.

### Fase Q2c -- sites oficiais de clube, começando pelos de maior amostra
Mapear, um clube de cada vez (começando pelos que mais aparecem na Loteca), o endereço da categoria de notícia/boletim médico. Prioriza qualidade da fonte (o próprio clube) sobre cobertura total dos 40+ clubes de uma vez.

### Fase Q4 -- ligar os novos fatores à análise de associação (a mesma do plano anterior, "o que costuma vir junto")
Só depois de Q1-Q3 trazerem dado, testar estatisticamente (mesmo método do backtest: comparação pareada, com significância, sem promessa causal) se cada fator novo está de fato associado a melhora ou piora no desempenho seguinte. Fator sem diferença perceptível é mostrado como tal, não escondido.

## Avaliação: skills e agentes

- **Skill de pesquisa de fonte oficial** ("ler antes de codificar"): já é o que eu faço manualmente a cada nova fonte (REC, agora o BID). Formalizar como skill deste projeto tem valor -- padroniza o registro em `docs/` e no cofre, evita pular a checagem. Proponho criar `loteca-pesquisar-fonte-oficial` no seu `~/.claude/skills/` (ou escopada ao projeto).
- **Agente/skill de rotulagem de notícia**: o C2 tem uma pendência -- validar a precisão das palavras-chave contra notícia real, rotulada por você. Um fluxo semi-automático (eu proponho rótulo, você confirma/corrige) reduziria o trabalho, mas **a validação final continua sua** -- é exatamente o princípio "saída de modelo é insumo, nunca decisão" já seguido no projeto.
- **Agente para rodar `atualizar_tudo.py` periodicamente**: já existe o script; a tarefa agendada continua sendo criada por você (não crio tarefa do sistema operacional).
- **Não recomendo** um "agente autônomo" coletando rede social ou fazendo julgamento de "contratação bem feita" -- foge do princípio de não fabricar dado e de manter humano na decisão.

## Perguntas para sua validação

1. Aprova a ordem Q1 → Q2 → Q2b → Q2c → Q3 → Q4?
2. Sobre a decisão antiga de não coletar elenco (idade de jogadores): mantém a decisão, ou quer que eu reavalie com você?
3. Aprova a pesquisa do BID (Q2) como primeiro passo com fonte nova?
4. Para os canais do YouTube (Q2b): confirma CazéTV, TNT Sports Brasil, Desimpedidos e Canal GOAT, ou tem outros/quer tirar algum?
5. Para os sites oficiais de clube (Q2c): concorda em começar pelos clubes de maior amostra em vez de tentar os 40+ de uma vez? Tem algum específico que quer priorizar?
6. Quer que eu crie a skill de pesquisa de fonte oficial no seu `~/.claude/skills/`?
7. Confirma que sentimento de rede social e dado tático pago ficam fora do escopo por ora?
8. Tem sites específicos em mente para eu avaliar (além dos já estudados antes: Driblab, UFMG, ValorFinal)?

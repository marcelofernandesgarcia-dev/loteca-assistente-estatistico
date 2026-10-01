# Loteca — Assistente Estatístico

Aplicativo local (instalado na máquina, não exposto à internet) para acompanhamento estatístico da Loteca (loteria esportiva de prognóstico da CAIXA — resultado 1/X/2 em 14 jogos por concurso), pensado para uso numa lotérica.

Projeto pessoal, sem vínculo institucional. Ver `CLAUDE.md`.

**Objetivo declarado (governa todo o app):** por se tratar de jogo de azar, o app existe para fortalecer a análise e reduzir risco e erro na escolha do apostador — nunca para prometer ou garantir resultado.

## Instalação e uso

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.lock
```

`requirements.txt` declara as dependências diretas (sem versão travada); `requirements.lock` (gerado com `pip freeze`) trava tudo, inclusive dependências transitivas, para uma reinstalação futura não vir com versão diferente sem querer. Ao adicionar uma dependência nova em `requirements.txt`, regenere o lock com `pip freeze > requirements.lock` e confira vulnerabilidade conhecida:

```bash
.venv\Scripts\pip install pip-audit
.venv\Scripts\python -m pip_audit -r requirements.lock
```

### Abrir o aplicativo (uso do dia a dia)

Criar os atalhos uma vez (Área de Trabalho e Menu Iniciar, com ícone; não mexe no registro e não inicia com o Windows):

```bash
powershell -ExecutionPolicy Bypass -File scripts\criar_atalhos.ps1
```

Depois, é só abrir o atalho **Loteca - Assistente Estatistico**. O lançador (`iniciar.pyw`, regras em `lancador/regras.py`):

1. se o app já está aberto, só abre outra janela dele;
2. sobe o servidor em segundo plano, **só neste computador** (`127.0.0.1`, porta livre entre 8700 e 8799), sem janela preta;
3. abre a janela do app (Edge em modo aplicativo, perfil próprio em `%LOCALAPPDATA%\LotecaAssistente`), com "Abrindo…" enquanto o servidor sobe;
4. se a última tentativa de atualização tem mais de 12 horas, roda `scripts/atualizar_tudo.py` em segundo plano (o app abre na hora com os dados que já tem; sem internet, abre igual). Desligar: variável de ambiente `LOTECA_ATUALIZAR_AO_ABRIR=0`; mudar o intervalo: `LOTECA_HORAS_ENTRE_ATUALIZACOES`;
5. fechar todas as janelas do app encerra o servidor. Uma atualização em andamento termina sozinha.

Logs em `logs/` (fora do Git, sem dado pessoal): `lancador.log`, `servidor.log`, `atualizacao.log`. Sem o Edge, o app abre no navegador padrão e o servidor só para quando o Windows é encerrado. Para remover: apague os dois atalhos. O ícone é gerado por `scripts/gerar_icone.py`.

`.streamlit/config.toml` fixa o endereço `127.0.0.1` e desliga as estatísticas de uso do Streamlit, para qualquer forma de abrir o app a partir desta pasta (sem ele, o servidor atendia pela rede e enviava estatística de uso -- conferido com `streamlit config show` em 30/09/2026).

Modo de diagnóstico (com janela de console, mostra os erros): duplo clique em `iniciar_loteca.bat`, ou:

```bash
.venv\Scripts\streamlit run app/main.py
```

Atualizar as três fontes de dado de uma vez (CAIXA, CBF, notícias), com o resultado de cada uma registrado em `execucoes` e visível no painel "Status dos dados" da página inicial:

```bash
.venv\Scripts\python scripts\atualizar_tudo.py
```

Rodar os testes:

```bash
.venv\Scripts\pytest tests/
```

Importar histórico completo (opcional — o app já bootstrapa com `data/loteca-historico-valorfinal.csv` na primeira execução; para dado por clube/placar completo, importa da API da CAIXA concurso a concurso, ~15-20 min; retomável, faz backup do banco antes e junta grafias/UF ausente do mesmo time ao final):

```bash
.venv\Scripts\python scripts\importar_historico.py
```

## Estrutura

- `importer/` — cliente da API da CAIXA (rate-limited, incremental; `/loteca` para concursos apurados e `/loteca/programacao` para o concurso a jogar, com prazo exato de apostas), bootstrap do dataset ValorFinal e `unificar_participantes.py` (junta grafias diferentes do MESMO time; só por normalização automática ou por `data/apelidos-participantes.csv` curado à mão -- `candidatos_a_duplicidade` só lista pares parecidos para revisão humana, nunca une sozinho).
- `stats/` — regra de negócio pura: cálculo de resultado, frequência, forma, percentual histórico (Poisson), sugestão seco/duplo/triplo, desempenho no ano, painel de desempenho por time (`desempenho.py`), fechamento de bolão, `bilhete.py` (sugestão de aposta simples: no máximo UM duplo ou UM triplo, regra do usuário), `prazo.py` e `concursos.py` (qual concurso está a jogar), `competicao.py` (tabela por rodada, ranking na série, força do calendário), `modelo_temporada.py` (modelo EXPERIMENTAL de gols da temporada), `backtest.py` (mede o percentual atual contra a própria base, sem vazamento temporal -- ver página "Confiabilidade do modelo" e `docs/resposta-ao-parecer-29-09-2026.md`) e `contexto.py` (zona de classificação -- título/Libertadores/Sul-Americana/acesso/playoff/rebaixamento -- por posição, conforme o Regulamento Específico da Competição de cada série; nunca por suposição, ver docs/fontes-oficiais/).
- `externo/` — varredura semanal de notícias (RSS público, sem chave de API; janela de 10 dias; veículos prioritários ge/Globo-SporTV e ESPN Brasil, ver `docs/fontes-de-noticias.md`) e cálculo do ajuste externo limitado. O percentual mostrado nos cards 2 e 3 é o final (`externo/percentual_final.py`): o efeito no jogo é o ajuste do mandante menos o do visitante, limitado a ±8 pontos, redistribuído entre os outros resultados na proporção deles e sempre somando 100%. A manchete, o veículo e o link que sustentam cada ajuste ficam em `fatores_externos.evidencias` e aparecem em "Por que os percentuais foram ajustados".
- `importer/cbf_client.py`, `importer/cbf_mapeamento.py`, `stats/cbf.py`, `scripts/coleta_cbf.py` — leitura das páginas públicas da CBF, pareamento com os times da Loteca (UF + nome) e consultas.
- `app/` — páginas Streamlit (Concurso atual com 3 cards, Por concurso, Ficha do time em abas (Visão geral, Evolução na competição, Jogo a jogo, Ataque/defesa/mando, Comparação com a liga, Próximo jogo e resultados possíveis, Na Loteca), com ficha reduzida para quem não tem dados da CBF, Fechamento de bolão, Confiabilidade do modelo, Meus bilhetes, Painel comparativo), sem lógica de negócio própria.
- `scripts/coleta_cbf_historico.py` — coleta única e retomável das temporadas 2019 a 2025 das Séries A e B da CBF (mesma fonte e método de 2026; cerca de 16 minutos). Uma temporada antiga não sobrescreve o nome atual do time; o nome de cada ano fica em `cbf_classificacao.nome_no_ano`. As telas de "time atual" olham só a temporada mais recente; o painel comparativo oferece as antigas no modo livre. Diferenças entre a soma dos jogos e a tabela da CBF estão em `config.CBF_ANOMALIAS_CONHECIDAS`. Detalhes em `docs/p2-temporadas-cbf-30-09-2026.md`.
- `stats/selecoes.py` + `data/externos/international_results.csv` + `data/selecoes-nomes.csv` — força das seleções por rating Elo, calculado com a base aberta de resultados internacionais (49 mil jogos, licença CC0). Nos jogos entre duas seleções, o percentual vem daí (`config.MODELO_SELECOES`; `LOTECA_MODELO_SELECOES=historico` volta ao modelo anterior). Testado jogo a jogo, sem olhar o futuro: 59% de acerto do favorito contra 45% do modelo anterior (página "Confiabilidade do modelo"). Detalhes, limitações e antes/depois em `docs/p1-selecoes-elo-30-09-2026.md`; como atualizar a base em `data/externos/LEIAME.md`.
- `stats/cbf.historico_saf_na_cbf` — a Ficha do time mostra "Registrado como SAF na CBF desde AAAA" (Lei nº 14.193/2021) quando o nome do time na CBF traz "SAF" sem interrupção até hoje, ou "Consta como SAF no nome da CBF em [anos]" quando houve lacuna ou o nome de hoje não traz. Usa o nome de cada temporada (2019 a 2026). Só informação, sem efeito no percentual; a ausência do sufixo não prova que o clube não seja SAF, então a tela nunca afirma o contrário.
- `data/cbf-codigos-equivalentes.csv` — os 11 clubes que trocaram de código na CBF, validados pelo usuário em 30/09/2026; lido por `stats/cbf.codigos_equivalentes()` e ainda não usado em análise.
- `stats/links_externos.py` + `data/busca-transfermarkt.csv` — link de consulta MANUAL ao Transfermarkt (elenco, idade, valor de mercado) na Ficha do time. Os termos de uso do site reservam a extração de dados, então o app só monta o endereço; nada é coletado. A lista curada guarda o termo de busca testado de cada clube (a busca só acerta com o nome oficial: "Ceará SC" acha, "Ceará" não); clube fora da lista usa o nome da CBF e a tela avisa. Idem para o BID da CBF (`config.BID_CONSULTA_URL`). Lista viva: acrescente uma linha por clube, testando antes.
- `stats/painel.py` — painel comparativo (plano em `docs/plano-dashboard-q5.md`): aba da temporada da CBF (tabela comparativa, posição, pontos e aproveitamento rodada a rodada, projeção "se o desempenho persistir" até o fim da temporada em dois cenários -- o ritmo da temporada e a projeção cautelosa, que mistura o ritmo do time com a média da liga (peso do time = jogos / (jogos + 20)) --, com o erro medido em 13 temporadas completas (2019 a 2025) e não em uma só, mapa de calor) e aba do histórico na Loteca (clubes e seleções, aproveitamento por pontos, tendência anual). Modo "todos do concurso a jogar", organizado por jogo, e modo livre. O tamanho da temporada vem do regulamento (`config.TEMPORADA_JOGOS_POR_TIME`); sem cadastro, não há projeção. A página "Confiabilidade do modelo" não usa `pandas` de propósito (funciona mesmo se o `pandas` estiver bloqueado no Windows -- ver seção "Problema conhecido" abaixo).
- `stats/bilhetes_salvos.py` (etapa A3) — salva o bilhete marcado com o percentual do momento (snapshot, sem tabela de previsões separada), confere contra o resultado real quando o concurso estiver todo apurado, e soma gasto x prêmio (o prêmio é informado por você -- o app não consulta a CAIXA para saber se ganhou). Só no banco local; nenhum dado pessoal. Guarda também a análise do palpite e os motivos opcionais de cada marcação, para o aprendizado.
- `stats/bilhete.py` — sugestão de aposta simples e `validar_volante` (regras do volante: todo jogo marcado, ao menos um duplo ou triplo, no máximo 864 apostas). O card 3 da página "Concurso atual" é um volante de 3 quadrados por jogo (1, X, 2), que começa em branco.
- `stats/analise_palpite.py` — análise do palpite por regra, sem IA: coerência com os dados, zebras (abaixo de `config.ANALISE_LIMIAR_ZEBRA`, 25%), rendimento de duplos e triplos e onde um duplo rende mais, chance do bilhete (Poisson-binomial), jogos sem base própria; depois do resultado, o que cada tipo de marcação acertou e o histórico acumulado em "Meus bilhetes" (taxas só com `config.ANALISE_AMOSTRA_MINIMA` marcações). Ver `docs/estudo-analise-do-palpite.md`.
- `tests/` — pytest para `stats/`, `externo/`, um teste de integração leve contra a API real e `AppTest` (Streamlit) de todas as páginas, sobre banco sintético -- nenhum toca o `loteca.db` real.
- `scripts/atualizar_tudo.py` — roda as três fontes numa chamada só; cada uma isolada da outra (falha em uma não impede as demais); grava o resultado em `execucoes` (`db.registrar_execucao`/`db.ultima_execucao_por_fonte`), lido pelo painel "Status dos dados" da página inicial.
- `iniciar_loteca.bat` — modo de diagnóstico: ativa o `.venv` e abre o Streamlit com janela de console.
- `iniciar.pyw`, `lancador/` e `scripts/criar_atalhos.ps1` — lançador do dia a dia (ver "Abrir o aplicativo").
- `stats/ano_em_curso.py` + `app/ano_em_curso_ui.py` — o ano em curso sempre visível (página inicial, Concurso atual antes do volante; o Histórico na Loteca do painel e a Ficha do time abrem no ano em curso). Fonte de cada participante, da mais completa para a mais pobre: classificação da CBF do ano, jogos de seleções do ano na base aberta, jogos do ano na grade da Loteca. É o que aconteceu no ano, não previsão.
- `stats/premiacao.py`, `app/premiacao_ui.py`, `app/pages/8_Premiacoes.py` e `scripts/importar_valores.py` — valores de cada concurso: arrecadação, ganhadores e prêmio por faixa, total pago, acumulados (final zero/cinco e Loteca Especial) e estimativa do próximo. Aparecem em "Concurso atual", "Por concurso" e na página "Premiações" (histórico). O significado de cada campo está na fonte oficial (Manual de Produtos v21, itens 18.1.3.12 e 6.3.4); ver `docs/valores-dos-concursos-30-09-2026.md`. Para preencher o histórico: `.venv\Scripts\python scripts\importar_valores.py` (retomável, com backup).
- `stats/sugestoes_bilhete.py`, `stats/otimizacao_bilhete.py`, `stats/calibracao_bilhete.py`, `stats/estudo_sugestoes.py` e `app/sugestoes_ui.py` — complexidade de cada jogo, sugestões de alteração pelo mesmo custo (nunca aumentam o custo), leitura de economia e, ao lado da "chance de acertar" calculada pelos percentuais, o que aconteceu de fato com bilhetes do mesmo custo nos concursos passados (a chance calculada é otimista). Estudo e números em `docs/estudo-sugestoes-jogos-complexos-30-09-2026.md`; para repetir o teste: `.venv\Scripts\python scripts\estudo_sugestoes.py`.
- `stats/versoes_palpite.py` — versões do palpite gravadas no banco (tabela `versoes_palpite`): guardar cada tentativa, comparar (apostas, custo, chance, duplos/triplos, zebras), ver o que mudou, voltar a uma versão e salvar; todo bilhete salvo fica ligado a uma versão. Depois do resultado, "Meus bilhetes" mostra se as mudanças da primeira versão para a que virou bilhete ajudaram (conclusão só com `config.VERSOES_CONCURSOS_MINIMOS` concursos).
- `stats/associacao.py` e `scripts/estudo_associacao.py` — estudo de associação (P3/Q4): cada fator (mando, forma, sequência, zona da tabela, SAF) melhora a previsão do resultado fora da amostra, além do retrospecto do time e do mando? Só lê o banco e grava o relatório em `docs/p3-associacao-fatores-*.md`; parâmetros em `config.ASSOCIACAO_*`. Usa `numpy`, que já vem com o `pandas` (travado em `requirements.lock`). Resultado de 01/10/2026: só o mando melhora a previsão; ver o relatório.
- `stats/backtest_competicao.py` e `scripts/backtest_competicao.py` — teste B2: três modelos de 1/X/2 (frequência simples, retrospecto dos dois times por logística multinomial, Poisson da temporada) nos jogos da CBF, andando no tempo (treino só em anos anteriores) e sem jogo adiado antes de acontecer; comparação pareada com intervalo e valor q. **Só mede**: não altera nenhum percentual do app. Resultado de 01/10/2026: retrospecto e Poisson superam a frequência simples, sem diferença entre si; ver `docs/b2-modelo-por-competicao-01-10-2026.md`.
- `stats/anti_manada.py` e `scripts/estudo_anti_manada.py` — estudo anti-manada (Q7): jogos fora da coluna 1 contra ganhadores de 14 por milhão arrecadado, correlação de postos estratificada por ano, com permutação dentro do ano e intervalo; reproduz e corrige a conta anterior (-0,13, que era Pearson sobre contagens brutas). Ver `docs/q7-anti-manada-01-10-2026.md`.
- `app/pages/9_Estudos_estatisticos.py` e `app/estudos_ui.py` — página "Estudos estatísticos" com os três estudos (fatores do desempenho, modelos de 1/X/2 e anti-manada) em abas; só apresentação, com cálculo em cache renovado quando entram dados novos. O teste dos modelos roda sob demanda (cerca de 10 s).
- `scripts/varredura_semanal.py` — ponto de entrada para o Agendador de Tarefas do Windows.
- `scripts/importar_historico.py` — importa o histórico completo de concursos da CAIXA (1 até o último apurado); retomável, faz backup do banco antes, e roda `unificar_participantes.unificar()` para juntar grafias normalizadas do mesmo time.
- `config.py` — todos os parâmetros (rate-limit, pesos do ajuste externo, janela de forma, lista de seleções nacionais).

## Dados oficiais da CBF (Séries A e B)

A CBF não tem API pública documentada; o app lê as **páginas públicas** (classificação, estatísticas e jogos de cada time) como um usuário comum, com intervalo de 2 s entre páginas e sem repetir a coleta em menos de 20 h. Os termos de uso da CBF vedam uso não autorizado do conteúdo -- o uso foi decisão e risco do usuário (ver `docs/cbf-fonte-de-dados.md`). Os dados ficam só no banco local; nada da CBF vai ao GitHub. Para desligar: `LOTECA_CBF_HABILITADO=0`.

Coletar agora: `.venv\Scripts\python scripts\coleta_cbf.py` (`--forcar` ignora a validade de 20 h).

Agendar (você mesmo cria; o Claude não altera configuração do sistema) -- segunda, quinta e sexta às 07:30:

```
schtasks /Create /SC WEEKLY /D MON,THU,FRI /ST 07:30 /TN "Loteca - Coleta CBF" /TR "C:\Users\marce\Projetos\loteca-assistente-estatistico\.venv\Scripts\python.exe C:\Users\marce\Projetos\loteca-assistente-estatistico\scripts\coleta_cbf.py"
```

## Varredura semanal de notícias (ajuste externo)

Roda uma vez por concurso, quando faltam de 0 a 2 dias para o prazo de aposta (`config.VARREDURA_DIAS_ANTES_DO_PRAZO`); concurso que já tem linha em `fatores_externos` não é varrido de novo, e um dia perdido é recuperado no dia seguinte. Busca notícias por participante via RSS público do Google Notícias, extrai sinais estruturados por palavra-chave (lesão, suspensão, desfalque, tendência de imprensa) e aplica um ajuste limitado (`config.AJUSTE_EXTERNO_TETO_PONTOS`) sobre o percentual histórico. Log completo em `fatores_externos`, visível na página "Por time".

**Decisão de implementação:** a v1 usa palavra-chave sobre notícia real (RSS), não um modelo de linguagem pago — auditável, sem custo de API de terceiro. Se quiser trocar por leitura de IA depois, o ponto de extensão é `externo/analise.py`.

Para agendar (Windows, roda mesmo com o app fechado — crie você mesmo, o Claude não altera configuração do sistema):

```
schtasks /Create /SC DAILY /ST 08:00 /TN "Loteca - Varredura Semanal" /TR "C:\Users\marce\Projetos\loteca-assistente-estatistico\.venv\Scripts\python.exe C:\Users\marce\Projetos\loteca-assistente-estatistico\scripts\varredura_semanal.py"
```

(Roda diariamente, mas o script só faz algo quando algum concurso ainda não varrido está a até 2 dias do prazo — ver `externo.varredura.concurso_alvo_da_semana`.)

Tarefa única que atualiza as três fontes (CAIXA, CBF e notícias) de uma vez, às 08:00, e que dispensa as duas anteriores:

```
schtasks /Create /SC DAILY /ST 08:00 /TN "Loteca - Atualizar Tudo" /TR "C:\Users\marce\Projetos\loteca-assistente-estatistico\.venv\Scripts\python.exe C:\Users\marce\Projetos\loteca-assistente-estatistico\scripts\atualizar_tudo.py"
```

## Escopo definido com o usuário (27/09/2026, revisado)

- **Uso:** aplicativo de monitoramento e análise estatística — não é uma ferramenta de "palpite", e sim de orientação baseada em probabilidade e no histórico de cada participante (clube ou seleção nacional).
- **Percentual de vitória:** calculado por participante em cada jogo (método Poisson sobre o histórico próprio), ajustado por uma varredura semanal de notícias/análises externas, limitada e auditável.
- **Fonte de dados dos concursos:** endpoint não-oficial da CAIXA (dado por clube/placar) + dataset aberto ValorFinal (bootstrap rápido do 1/X/2 geral) — ver `docs/pesquisa-fontes-dados.md`.
- **Canais oficiais de acompanhamento:** https://loterias.caixa.gov.br/Paginas/Programacao-Loteca.aspx e https://loterias.caixa.gov.br/Paginas/default.aspx.

## Status atual

App funcional (v1): importador, banco SQLite, motor estatístico (frequência, forma, percentual Poisson, fechamento de bolão), camada de ajuste externo por notícias e as 4 páginas Streamlit. Testado localmente com dado real (47 concursos importados, varredura semanal executada, 17 testes automatizados passando). Toda a pesquisa que fundamenta as regras de negócio está em `docs/` e no cofre Obsidian (`Loteca/`). Plano completo em `C:\Users\marce\.claude\plans\velvety-toasting-squid.md`.

**Fora do escopo da v1 (decisão deliberada):** odds de mercado, suporte a Lotogol, enriquecimento com escalação oficial detalhada.

## Problema conhecido: Smart App Control (Windows) pode bloquear o `pandas`

Em 29/09/2026 o "Controle de Aplicativos Inteligente" do Windows 11 passou a bloquear a DLL nativa do `pandas` neste computador (Registro de Eventos, canal Code Integrity: "Smart App Control Block"). Isso derruba as páginas "Por concurso" e "Por time" (usam `pandas` para tabela); "Concurso atual", "Fechamento de bolão" e "Confiabilidade do modelo" não usam `pandas` e continuam funcionando. É uma política de segurança do Windows, não um defeito do código -- resolver em Configurações → Privacidade e segurança → Segurança do Windows → Controle de aplicativos e do navegador. Detalhes em `docs/resposta-ao-parecer-29-09-2026.md`, seção 4.

## Aviso importante

Loteca é loteria regulada pela CAIXA — jogo de azar. As análises deste projeto são estatística histórica e probabilidade, nunca previsão garantida de resultado. A CAIXA Loterias possui certificação Nível 3 (de 4) em Jogo Responsável pela World Lottery Association.

## Próximos passos

Ver pendências no cofre Obsidian Cerebro Pessoal (`Loteca/02 - Pendências.md`) para a lista viva de decisões pendentes (ex.: importação histórica completa, refinar regras de prorrogação/suspensão no importador).

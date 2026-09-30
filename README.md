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

Rodar a interface (abre no navegador em `http://localhost:8501`), ou dar duplo clique em `iniciar_loteca.bat`:

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
- `stats/cbf.registrado_como_saf` — a Ficha do time mostra "Registrado como SAF na CBF" (Lei nº 14.193/2021) quando o nome oficial do time na CBF traz "SAF". Só informação, sem efeito no percentual; a ausência do sufixo não prova que o clube não seja SAF, então a tela nunca afirma o contrário.
- `stats/links_externos.py` + `data/busca-transfermarkt.csv` — link de consulta MANUAL ao Transfermarkt (elenco, idade, valor de mercado) na Ficha do time. Os termos de uso do site reservam a extração de dados, então o app só monta o endereço; nada é coletado. A lista curada guarda o termo de busca testado de cada clube (a busca só acerta com o nome oficial: "Ceará SC" acha, "Ceará" não); clube fora da lista usa o nome da CBF e a tela avisa. Idem para o BID da CBF (`config.BID_CONSULTA_URL`). Lista viva: acrescente uma linha por clube, testando antes.
- `stats/painel.py` — painel comparativo (plano em `docs/plano-dashboard-q5.md`): aba da temporada da CBF (tabela comparativa, posição, pontos e aproveitamento rodada a rodada, projeção "se o desempenho persistir" em dois ritmos até o fim da temporada, com o erro da projeção medido na própria temporada, mapa de calor) e aba do histórico na Loteca (clubes e seleções, aproveitamento por pontos, tendência anual). Modo "todos do concurso a jogar", organizado por jogo, e modo livre. O tamanho da temporada vem do regulamento (`config.TEMPORADA_JOGOS_POR_TIME`); sem cadastro, não há projeção. A página "Confiabilidade do modelo" não usa `pandas` de propósito (funciona mesmo se o `pandas` estiver bloqueado no Windows -- ver seção "Problema conhecido" abaixo).
- `stats/bilhetes_salvos.py` (etapa A3) — salva o bilhete marcado com o percentual do momento (snapshot, sem tabela de previsões separada), confere contra o resultado real quando o concurso estiver todo apurado, e soma gasto x prêmio (o prêmio é informado por você -- o app não consulta a CAIXA para saber se ganhou). Só no banco local; nenhum dado pessoal. Guarda também a análise do palpite e os motivos opcionais de cada marcação, para o aprendizado.
- `stats/bilhete.py` — sugestão de aposta simples e `validar_volante` (regras do volante: todo jogo marcado, ao menos um duplo ou triplo, no máximo 864 apostas). O card 3 da página "Concurso atual" é um volante de 3 quadrados por jogo (1, X, 2), que começa em branco.
- `stats/analise_palpite.py` — análise do palpite por regra, sem IA: coerência com os dados, zebras (abaixo de `config.ANALISE_LIMIAR_ZEBRA`, 25%), rendimento de duplos e triplos e onde um duplo rende mais, chance do bilhete (Poisson-binomial), jogos sem base própria; depois do resultado, o que cada tipo de marcação acertou e o histórico acumulado em "Meus bilhetes" (taxas só com `config.ANALISE_AMOSTRA_MINIMA` marcações). Ver `docs/estudo-analise-do-palpite.md`.
- `tests/` — pytest para `stats/`, `externo/`, um teste de integração leve contra a API real e `AppTest` (Streamlit) de todas as páginas, sobre banco sintético -- nenhum toca o `loteca.db` real.
- `scripts/atualizar_tudo.py` — roda as três fontes numa chamada só; cada uma isolada da outra (falha em uma não impede as demais); grava o resultado em `execucoes` (`db.registrar_execucao`/`db.ultima_execucao_por_fonte`), lido pelo painel "Status dos dados" da página inicial.
- `iniciar_loteca.bat` — ativa o `.venv` e abre o Streamlit com duplo clique.
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

Roda 2 dias antes do prazo de aposta de cada concurso (`config.VARREDURA_DIAS_ANTES_DO_PRAZO`). Busca notícias por participante via RSS público do Google Notícias, extrai sinais estruturados por palavra-chave (lesão, suspensão, desfalque, tendência de imprensa) e aplica um ajuste limitado (`config.AJUSTE_EXTERNO_TETO_PONTOS`) sobre o percentual histórico. Log completo em `fatores_externos`, visível na página "Por time".

**Decisão de implementação:** a v1 usa palavra-chave sobre notícia real (RSS), não um modelo de linguagem pago — auditável, sem custo de API de terceiro. Se quiser trocar por leitura de IA depois, o ponto de extensão é `externo/analise.py`.

Para agendar (Windows, roda mesmo com o app fechado — crie você mesmo, o Claude não altera configuração do sistema):

```
schtasks /Create /SC DAILY /ST 08:00 /TN "Loteca - Varredura Semanal" /TR "C:\Users\marce\Projetos\loteca-assistente-estatistico\.venv\Scripts\python.exe C:\Users\marce\Projetos\loteca-assistente-estatistico\scripts\varredura_semanal.py"
```

(Roda diariamente, mas o script só faz algo nos dias em que algum concurso está a 2 dias do prazo — ver `externo.varredura.concurso_alvo_da_semana`.)

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

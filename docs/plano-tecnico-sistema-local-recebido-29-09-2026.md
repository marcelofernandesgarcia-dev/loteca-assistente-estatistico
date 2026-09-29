# Plano técnico para operação local — Loteca Assistente Estatístico

> Documento externo, recebido do usuário em 29/09/2026, anexado para análise
> junto com um print da tela "Controle inteligente de aplicativos" do Windows
> (Smart App Control, desativado pelo usuário -- resolve o bloqueio do
> `pandas` relatado em `docs/resposta-ao-parecer-29-09-2026.md`). Não foi
> escrito por esta sessão. Mantido na íntegra, como registro; avaliação
> crítica em `docs/avaliacao-plano-tecnico-29-09-2026.md`.

**Escopo:** planejamento e avaliação. Este documento não implementa alterações no código e não autoriza aumento de complexidade sem validação.

## 1. Diretriz principal

O sistema deve ser tratado como uma aplicação local de **apoio à análise**, e não como mecanismo de previsão garantida. O objetivo técnico correto é produzir probabilidades históricas calibradas, mostrar incerteza, comparar alternativas e manter rastreabilidade.

A estratégia recomendada é:

1. preservar o funcionamento atual como baseline;
2. sanear dados e reprodutibilidade;
3. construir backtest walk-forward;
4. medir calibração, erro e custo;
5. só depois avaliar novos sinais ou modelos;
6. manter todas as decisões do usuário separadas da estimativa estatística.

## 2. Arquitetura local recomendada

### 2.1 Componentes

```text
[Streamlit local]
       |
       v
[Camada de aplicação/orquestração]
       |
       +--> [Serviços de domínio]
       |       +--> probabilidades
       |       +--> backtest
       |       +--> decisão seco/duplo/triplo
       |       +--> explicações
       |
       +--> [Repositórios SQLite]
       |       +--> concursos e jogos
       |       +--> histórico por participante
       |       +--> previsões versionadas
       |       +--> resultados do backtest
       |       +--> evidências externas
       |
       +--> [Adaptadores de fontes]
               +--> CAIXA
               +--> CSV histórico
               +--> CBF
               +--> RSS/notícias
```

### 2.2 Princípios de código

- **Separar domínio de infraestrutura:** regras estatísticas não devem depender de Streamlit, requests ou SQLite diretamente.
- **Injeção de dependência:** serviços recebem repositórios e adaptadores, facilitando testes com dados sintéticos.
- **Adaptadores para fontes externas:** cada fonte deve ter timeout, retry limitado, cache, status e versão do payload.
- **Funções puras para cálculos:** uma função que recebe dados e parâmetros deve produzir o mesmo resultado sem acessar rede ou estado global.
- **Contratos explícitos:** usar `dataclass`, tipos e validação para concursos, partidas, probabilidades e evidências.
- **Idempotência:** executar duas vezes a mesma importação não deve duplicar nem apagar informação existente.
- **Configuração centralizada:** limiares, janelas, priors e fontes devem ficar em configuração versionada, não espalhados em literais.
- **Observabilidade local:** toda atualização deve registrar início, fim, fonte, quantidade, hash, erro e situação de completude.

## 3. Estrutura de diretórios sugerida

```text
loteca-assistente-estatistico/
├── app/
│   ├── main.py
│   ├── pages/
│   └── componentes/
├── domain/
│   ├── models.py          # dataclasses e tipos de domínio
│   ├── probabilidades.py  # cálculo puro
│   ├── decisao.py         # seco/duplo/triplo e custo
│   ├── evidencias.py      # explicações rastreáveis
│   └── erros.py
├── stats/
│   ├── baseline.py        # frequência global e mandante
│   ├── poisson.py
│   ├── calibracao.py
│   ├── backtest.py
│   └── metricas.py
├── importer/
│   ├── caixa.py
│   ├── cbf.py
│   ├── csv_historico.py
│   └── pipeline.py
├── externo/
│   ├── noticias.py
│   ├── sinais.py
│   └── politicas.py
├── persistence/
│   ├── db.py
│   ├── migrations.py
│   └── repositories/
├── scripts/
│   ├── validar_dataset.py
│   ├── executar_backtest.py
│   └── atualizar_dados.py
├── tests/
├── data/
│   ├── raw/
│   ├── processed/
│   └── manifests/
├── reports/
└── docs/
```

A reorganização só deve ser feita depois de existir uma suíte verde e um commit de referência. Não é recomendável mover muitos módulos simultaneamente à validação estatística.

## 4. Fase V0 — dados e reprodutibilidade

### 4.1 Manifesto do dataset

Criar um manifesto por arquivo de entrada com:

- nome e caminho;
- SHA-256;
- tamanho;
- fonte;
- URL, quando houver;
- data e hora de coleta;
- período coberto;
- delimitador e encoding;
- quantidade de concursos e jogos;
- concursos ausentes;
- regras de limpeza aplicadas.

A divergência de SHA-256 encontrada no CSV deve ser resolvida antes de qualquer conclusão de desempenho. Não atualizar o hash apenas para fazê-lo coincidir: primeiro identificar qual arquivo é oficialmente autorizado.

### 4.2 Camadas de dados

- `raw/`: cópia original, nunca sobrescrita.
- `processed/`: dados normalizados para uso do sistema.
- `manifests/`: hashes e relatórios de qualidade.
- SQLite: índice operacional e histórico de resultados.

### 4.3 Validações obrigatórias

- concurso não pode ser duplicado;
- número de jogos deve ser compatível com o concurso;
- resultado somente em `{1, X, 2}`;
- placar deve ser válido ou explicitamente ausente;
- data e horário devem ser parseáveis;
- participante deve possuir identidade estável;
- histórico não pode conter informação posterior ao corte do backtest;
- alterações em dados já importados devem gerar registro de revisão.

## 5. Fase V1 — modelo mínimo e backtest walk-forward

### 5.1 Baselines obrigatórios

Comparar pelo menos:

1. **Global:** frequência histórica geral de 1/X/2.
2. **Mando:** frequência separada para mandante, empate e visitante.
3. **Recente:** janela móvel, somente se houver quantidade mínima definida.
4. **Poisson atual:** método já existente.

Um modelo novo não deve ser considerado melhor se não superar os baselines fora da amostra.

### 5.2 Regra temporal

Para avaliar o concurso `t`:

```text
base_de_treino = todos os dados com data/concurso anterior a t
previsão_t = modelo(base_de_treino, jogos_do_concurso_t)
resultado_t = resultado_real_do_concurso_t
```

Nunca usar:

- resultado do próprio concurso na estimativa;
- partidas futuras;
- notícia publicada após o prazo do jogo;
- classificação atualizada depois do evento;
- parâmetros ajustados com todo o histórico incluindo o período avaliado.

### 5.3 Registro mínimo de cada previsão

A tabela de previsões deve guardar:

- `concurso_id`;
- `jogo_id`;
- `modelo_nome`;
- `modelo_versao`;
- `cutoff_concurso`;
- `p1`, `px`, `p2`;
- `fonte_dados_hash`;
- `parametros_json`;
- `amostra_utilizada`;
- `timestamp_calculo`;
- `resultado_real`, quando disponível.

Isso permite reproduzir por que uma determinada probabilidade foi produzida.

## 6. Fase V2 — métricas e critérios de sucesso

### 6.1 Métricas primárias

- **Brier score multiclasses:** mede a qualidade probabilística; quanto menor, melhor.
- **Calibração:** entre jogos estimados em 60%, aproximadamente 60% devem ocorrer naquele resultado em amostras suficientes.
- **Log loss:** penaliza probabilidades excessivamente confiantes e deve ser usado com cuidado em amostras pequenas.

### 6.2 Métricas secundárias

- acerto do resultado mais provável;
- matriz de confusão;
- desempenho por faixa de probabilidade;
- desempenho por competição e tipo de participante;
- cobertura de secos, duplos e triplos;
- quantidade de apostas equivalentes;
- custo por concurso;
- cobertura probabilística do resultado real;
- desempenho com e sem empate selecionado.

### 6.3 Critério de aprovação de um novo modelo

Um modelo somente deve substituir o baseline se:

1. for avaliado em período fora da amostra;
2. melhorar Brier ou manter desempenho equivalente com menor custo;
3. não piorar materialmente a calibração;
4. apresentar resultado consistente em mais de uma janela temporal;
5. tiver explicação reproduzível;
6. não depender de fonte externa frágil para funcionar.

Não usar somente "percentual de acerto" como critério.

## 7. Incerteza e amostra pequena

A interface deve distinguir:

- probabilidade calculada;
- confiança estatística;
- quantidade de observações;
- cobertura do histórico;
- ausência de informação.

Para amostra pequena:

- usar suavização/prior explícito;
- mostrar o tamanho da amostra;
- informar quando houve regressão à média global;
- evitar frases como "forte tendência" sem suporte;
- considerar intervalo de incerteza ou faixa de confiança;
- impedir que poucos jogos produzam uma probabilidade extrema.

A saída recomendada não é apenas `1: 62%, X: 21%, 2: 17%`, mas também:

```text
Estimativa: 62% / 21% / 17%
Base: 8 jogos relevantes
Fallback: parcial para frequência global
Incerteza: alta
Modelo: poisson-v1
```

## 8. Ajuste por notícias e fontes externas

O ajuste de notícias deve permanecer isolado até ser validado.

### 8.1 Três braços de experimento

- A: histórico/Poisson sem notícias;
- B: histórico/Poisson com heurística atual;
- C: histórico/Poisson com regra revisada.

Comparar Brier, calibração, log loss e custo. Não avaliar somente se o favorito mudou.

### 8.2 Regras técnicas mínimas

- exigir que o nome do participante apareça na evidência;
- identificar se a notícia se refere ao participante correto;
- tratar negação: "sem lesão" não é lesão;
- tratar recuperação: "volta aos treinos" não é ausência;
- distinguir rumor, confirmação e escalação oficial;
- deduplicar a mesma notícia em vários feeds;
- guardar título, veículo, URL, data de publicação, data de coleta e sinal extraído;
- aplicar validade temporal: a evidência só pode afetar jogos posteriores à publicação;
- manter teto de ajuste enquanto não houver calibração histórica.

### 8.3 Melhor alternativa futura

Em vez de pesos manuais, criar uma tabela de sinais rotulados e medir retrospectivamente o efeito. Até haver amostra rotulada suficiente, manter o ajuste como **informação contextual**, não como correção probabilística automática.

## 9. Decisão seco/duplo/triplo

A decisão deve ser uma camada posterior ao cálculo probabilístico.

### 9.1 Não confundir probabilidade com recomendação

- Probabilidade responde: "qual é a distribuição estimada?"
- Decisão responde: "qual conjunto de resultados atende ao custo e à cobertura desejada?"

### 9.2 Estratégia recomendada

Para cada jogo, calcular o conjunto de resultados escolhido, sua cobertura e seu custo. Comparar pelo menos:

- somente favoritos;
- regra atual de limiar;
- seleção por maior ganho de cobertura por unidade de custo;
- estratégia conservadora com orçamento fixo.

Os limiares 65% e 45% devem ser parametrizados e avaliados em laboratório. Não devem ser apresentados como empiricamente comprovados antes do backtest.

### 9.3 Orçamento

A interface deve permitir informar um orçamento máximo e mostrar:

- custo total;
- quantidade de combinações;
- cobertura estimada por jogo;
- jogos que receberam duplo/triplo;
- impacto de retirar cada expansão.

Isso melhora a decisão sem afirmar que o custo maior aumenta necessariamente o retorno.

## 10. Banco SQLite local

### 10.1 Tabelas recomendadas

- `concursos`
- `jogos`
- `participantes`
- `resultados`
- `fontes_dados`
- `importacoes`
- `previsoes`
- `backtest_execucoes`
- `backtest_resultados`
- `evidencias_externas`
- `config_modelos`
- `bilhetes` — somente após autorização explícita
- `bilhete_jogos` — somente após autorização explícita

### 10.2 Integridade

- chaves únicas para concurso, jogo e fonte;
- foreign keys habilitadas;
- transações por importação;
- migrations versionadas;
- backup antes de migration destrutiva;
- timestamp em UTC e apresentação local no app;
- nunca apagar placar confirmado durante atualização de programação.

## 11. Execução local no Windows

### 11.1 Ambiente

- Python em ambiente virtual `.venv`;
- dependências fixadas em `requirements.lock`;
- arquivo `.env.example` sem segredos reais;
- banco em diretório de dados configurável;
- logs em `logs/` com rotação simples;
- execução do Streamlit por script `.bat` ou PowerShell;
- atualização por tarefas agendadas somente depois de existir verificação de status.

Comandos conceituais:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.lock
python -m pytest -q
streamlit run app/main.py
```

### 11.2 Tarefas agendadas

Cada tarefa deve:

1. criar um `run_id`;
2. registrar início;
3. buscar dados com timeout;
4. salvar resposta bruta e hash;
5. validar antes de persistir;
6. fazer commit transacional;
7. registrar contagens e data-base;
8. registrar erro completo;
9. atualizar `ultima_atualizacao` somente após sucesso.

O app deve mostrar "última atualização bem-sucedida", não somente a hora em que a tarefa começou.

## 12. Testes recomendados

### 12.1 Unitários

- normalização de nomes;
- cálculo de probabilidades;
- soma de probabilidades igual a 1;
- regressão à média em amostras pequenas;
- Poisson com casos-limite;
- limiares de decisão;
- custo e combinações;
- validade temporal de notícias.

### 12.2 Contrato

Usar respostas salvas da CAIXA, CBF e feeds como fixtures. Testar alterações de formato sem depender sempre da rede.

### 12.3 Integração

A integração externa deve:

- ser separada da suíte determinística;
- ter timeout;
- informar claramente indisponibilidade;
- não transformar HTTP 403 em falsa aprovação;
- salvar evidência de quando foi executada.

### 12.4 Testes de propriedade

Adicionar propriedades como:

- probabilidades sempre somam 100%;
- nenhum valor é negativo;
- duplicar importação não duplica linhas;
- ordenar entradas não muda o resultado;
- aumentar o teto de custo não reduz a cobertura escolhida sem justificativa;
- uma notícia fora da janela temporal não altera a previsão.

## 13. Segurança e privacidade local

- manter o banco e logs no computador local;
- não enviar bilhetes, gastos ou notas para serviços externos sem autorização;
- não guardar API Keys no repositório;
- usar `.env` local e documentação de rotação;
- regenerar a chave do Obsidian que foi compartilhada na conversa;
- limitar o servidor REST do Obsidian a localhost sempre que possível;
- fazer backup criptografado do banco, caso existam dados pessoais;
- separar dados do projeto de dados do cofre pessoal.

## 14. O que não fazer agora

- não substituir Poisson por modelo complexo sem baseline;
- não adicionar machine learning apenas para aumentar sofisticação;
- não usar notícias como peso automático sem backtest;
- não otimizar limiares no mesmo período usado para avaliá-los;
- não apresentar probabilidade como previsão certa;
- não persistir gastos sem autorização específica;
- não fazer a API externa ser requisito para abrir o aplicativo;
- não alterar simultaneamente banco, modelo e interface;
- não considerar suíte unitária verde como prova de eficácia estatística.

## 15. Roadmap de implementação controlada

### Marco 1 — reprodutibilidade

Entrega: manifesto, hash confirmado, relatório de completude, backup e lock de dependências.

**Critério de aceite:** qualquer execução consegue identificar exatamente os dados usados.

### Marco 2 — backtest determinístico

Entrega: `stats/backtest.py`, fixtures, previsões versionadas e corte temporal.

**Critério de aceite:** execução repetida produz os mesmos resultados com o mesmo dataset.

### Marco 3 — métricas

Entrega: Brier, log loss, calibração, matriz de confusão, custos e comparação com baselines.

**Critério de aceite:** relatório mostra onde o modelo melhora, piora ou não difere.

### Marco 4 — operação local confiável

Entrega: pipeline idempotente, status de atualização, logs, backups e alertas locais.

**Critério de aceite:** falha de uma fonte não corrompe o banco nem fica silenciosa.

### Marco 5 — experimento externo

Entrega: comparação formal dos três braços de notícias.

**Critério de aceite:** nenhum ajuste passa a padrão sem benefício fora da amostra.

### Marco 6 — decisão de uso

Entrega: documentação de limitações, parâmetros aprovados e procedimento operacional.

**Critério de aceite:** o usuário consegue entender dados, incerteza, custo, evidência e versão antes de decidir.

## 16. Recomendação final

Para um sistema local e confiável, a melhor estratégia é uma arquitetura simples, determinística e auditável: **SQLite + Python modular + Streamlit local + adaptadores de fontes + backtest walk-forward + métricas de calibração**.

A prioridade não é aumentar a quantidade de sinais. É garantir que cada número tenha:

1. fonte identificada;
2. corte temporal correto;
3. tamanho de amostra;
4. versão do modelo;
5. incerteza conhecida;
6. comparação com baseline;
7. explicação rastreável.

Somente após essa base estar validada deve-se considerar maior granularidade por competição, CBF, notícias ou modelos mais complexos.

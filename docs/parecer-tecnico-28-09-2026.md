# Parecer técnico — Loteca Assistente Estatístico

> Documento externo, recebido pelo usuário em 29/09/2026 e anexado à sessão para
> análise. Não foi escrito por esta sessão; os fatos que ele afirma foram
> conferidos contra o repositório antes de qualquer ação (ver
> `docs/resposta-ao-parecer-29-09-2026.md`). Mantido aqui na íntegra, como
> registro, sem edição de conteúdo.

**Data da análise:** 28/09/2026
**Escopo:** análise e planejamento apenas; nenhum código ou dado do repositório foi alterado.
**Repositório avaliado:** `marcelofernandesgarcia-dev/loteca-assistente-estatistico`
**Objetivo declarado:** fortalecer a análise e reduzir risco e erro na escolha, sem prometer ou garantir resultados.

## 1. Conclusão executiva

O repositório apresenta uma **base técnica sólida para um assistente local, auditável e orientado a dados**. A separação entre ingestão (`importer/`), regras estatísticas (`stats/`), sinais externos (`externo/`), interface (`app/`) e testes (`tests/`) está bem alinhada ao objetivo.

A principal conclusão, entretanto, é que o projeto ainda deve ser considerado **ferramenta de organização e exploração estatística**, e não um modelo comprovadamente capaz de reduzir erro ou melhorar decisões. O motivo é objetivo: o percentual exibido é calculado, mas ainda não foi submetido a **backtest walk-forward, calibração e comparação formal contra referências simples**.

### Veredito

- **Arquitetura:** adequada.
- **Rastreabilidade e transparência:** boas, especialmente no ajuste por notícias.
- **Qualidade dos testes unitários e de interface:** boa.
- **Validação estatística do modelo:** insuficiente para afirmar redução de risco.
- **Qualidade operacional e governança dos dados:** requer correções antes de confiar em uso contínuo.
- **Recomendação:** aprovar somente a etapa de validação e governança; não aprovar ainda a adoção de novos pesos, novos sinais ou modelo mais complexo como padrão.

## 2. O que foi verificado

### 2.1 Estado do repositório

- Clone limpo, sem alterações locais.
- Branch `master` alinhada a `origin/master`.
- 25 commits no histórico analisado.
- 53 arquivos Python em `stats/`, `externo/`, `importer/`, `app/` e `tests/`.
- Compilação Python concluída sem erro.
- Nenhuma alteração foi feita no repositório.

### 2.2 Testes

Após instalar as dependências declaradas em `requirements.txt` no ambiente de análise:

```text
138 passed, 1 skipped in 9.04s
```

O teste ignorado é a integração com a API da CAIXA, que retornou HTTP 403 neste ambiente. Assim:

- a suíte sintética e unitária está verde;
- os testes de interface Streamlit existentes foram coletados e passaram;
- a integração real com a CAIXA não foi confirmada nesta execução;
- o teste de integração é permissivo: em indisponibilidade da API, ele faz `skip`, não falha.

### 2.3 Base de dados versionada

O CSV `data/loteca-historico-valorfinal.csv` contém:

- 1.261 concursos;
- concursos de 1 a 1.271;
- 10 concursos ausentes, documentados no próprio projeto;
- 17.654 jogos/resultados;
- distribuição observada:
  - mandante (`1`): 8.341 — **47,2471%**;
  - empate (`X`): 4.625 — **26,1980%**;
  - visitante (`2`): 4.688 — **26,5549%**.

## 3. Métodos atualmente selecionados

### 3.1 Dados principais

- Endpoint não documentado da CAIXA para concursos e programação.
- Dataset ValorFinal para bootstrap da frequência global 1/X/2.
- SQLite local como cache e armazenamento.
- Dados públicos da CBF para Séries A e B, com coleta de baixa frequência e opção de desligamento.
- RSS/Google Notícias para manchetes externas, priorizando ge e ESPN Brasil.

### 3.2 Estatística implementada

- Frequência global de 1/X/2.
- Frequência por participante, separando mando.
- Forma recente e desempenho no ano civil.
- Percentual por jogo usando médias de gols e distribuição de Poisson.
- Regressão para a frequência global quando a menor amostra de força própria é inferior a 5 jogos.
- Modelo experimental de forças de ataque/defesa por temporada, com prior e matriz de placares Poisson.
- Sugestão seco/duplo/triplo com limiares parametrizados em 65% e 45%.
- Fechamento combinatório e cálculo de custo.
- Ajuste externo limitado a ±8 pontos e renormalizado para manter a soma em 100%.

### 3.3 Governança da explicação

Pontos positivos:

- o app informa que é jogo de azar;
- o ajuste externo mantém evidências de manchete, veículo e link;
- o modelo experimental é rotulado como experimental;
- o projeto reconhece amostra pequena e fallback para frequência global;
- a documentação registra contradições metodológicas em vez de resolvê-las por suposição.

## 4. Principais riscos para o objetivo de reduzir erro

| Prioridade | Risco | Evidência | Impacto | Recomendação |
|---|---|---|---|---|
| **Crítica** | Não há prova de que o percentual melhora decisões | Não existe `stats/backtest.py`, Brier score, calibração ou avaliação walk-forward | Pode transformar números bem apresentados em falsa confiança | Executar B3 antes de alterar o modelo ou usar limiares como orientação forte |
| **Crítica** | Possível vazamento temporal em qualquer avaliação futura | O percentual atual consulta o estado corrente do banco; não há mecanismo de corte por concurso | Backtest ingênuo pode usar informação posterior ao jogo | Definir corte temporal estrito: treino somente com concursos anteriores |
| **Alta** | Dataset documentado não bate com o arquivo | SHA-256 documentado: `b1794c...`; SHA-256 observado: `7553a2...` | Compromete reprodutibilidade e auditoria | Verificar origem do CSV, atualizar documentação ou substituir o arquivo, registrando decisão |
| **Alta** | Dependência externa frágil | API da CAIXA retornou HTTP 403 no ambiente de análise; endpoint não é oficial/documentado | Atualizações podem falhar ou ficar silenciosas | Registrar status, erro e data da coleta; manter cópia local e relatório de completude |
| **Alta** | Histórico por clube ainda incompleto na operação descrita | O CSV tem histórico agregado; o histórico por time depende de importação concurso a concurso | Percentuais podem cair repetidamente na referência global | Importar histórico completo e medir cobertura por participante/competição |
| **Alta** | Ajuste por notícia é heurístico e propenso a falso positivo | Busca por substring em manchetes; ainda há casos como "recuperado", "sem lesão" e notícia do adversário | Pode deslocar percentual por sinal incorreto | Exigir participante na evidência, tratar negações/recuperação e medir precisão em amostra rotulada |
| **Média** | Limiares 65%/45% não foram calibrados | Documentação admite que foram escolhidos entre propostas conflitantes | Pode aumentar custo sem benefício ou reduzir cobertura | Laboratório de limiares com custo, acertos e calibração; não tratar como regra validada |
| **Média** | Bilhete não é persistido | A seleção vive na sessão Streamlit; não há tabela `bilhetes` | Impossibilita medir decisão, custo e resultado ao longo do tempo | Só implementar após autorização específica para armazenar bilhetes/gastos locais |
| **Média** | Agendamentos falham silenciosamente | Scripts dependem de tarefas Windows criadas manualmente; não há painel de execução | Dados podem ficar desatualizados sem aviso | Criar status de coleta, idade dos dados, erro da última execução e completude |
| **Média** | Dependências sem lock | Há `requirements.txt`, mas não `requirements.lock` | Reexecução pode mudar com versões futuras | Fixar versões e adicionar auditoria de dependências |
| **Baixa/Média** | Teste real da CAIXA é pulado em HTTP 403 | `skip` mantém a suíte verde | Pode dar impressão de validação completa | Separar teste unitário, contrato de resposta e integração externa obrigatória em ambiente autorizado |

## 5. Avaliação metodológica

### Pontos fortes

1. **Separação entre probabilidade e decisão:** o app exibe percentuais e permite a marcação do usuário, sem declarar previsão certa.
2. **Fallback explícito:** amostras pequenas não são apresentadas como força confiável de um time.
3. **Poisson é coerente como baseline:** é uma escolha simples, explicável e adequada para uma primeira referência de gols.
4. **Ajuste externo limitado:** o teto impede que manchetes dominem totalmente a estatística histórica.
5. **Renormalização:** o ajuste final mantém 1/X/2 somando 100%.
6. **Modelo de temporada isolado:** está identificado como experimental e não substitui silenciosamente o modelo principal.
7. **Testes abrangentes para regras de negócio:** resultado, combinatória, mapeamento CBF, UI sintética e ajuste externo estão cobertos.

### Limitações que impedem uma conclusão de eficácia

1. **Poisson atual não é ainda um modelo validado:** médias simples de gols podem misturar competições, períodos, força de adversário e clubes/seleções.
2. **Não há intervalo de incerteza:** mostrar 62% sem faixa de confiança pode sugerir precisão superior à amostra real.
3. **Amostra por participante é desigual:** o mesmo participante pode ter poucos jogos, jogos apenas na grade da Loteca ou dados de contextos diferentes.
4. **Notícias não são evidência causal quantificada:** um peso de -3 ou +2 pontos é uma decisão de negócio, não uma estimativa estimada em dados históricos.
5. **Custo e cobertura ainda não são avaliados em conjunto:** acertar o favorito não basta; a decisão de duplo/triplo depende do custo e da probabilidade de cobrir o resultado.
6. **A meta correta não é "prever o vencedor", mas calibrar probabilidades:** o critério primário deve ser Brier/log loss/calibração, acompanhado de acerto e custo.

## 6. Plano recomendado para validação — sem implementação automática

### Etapa V0 — saneamento e reprodutibilidade

**Objetivo:** garantir que qualquer comparação futura use dados identificáveis.

Critérios:

- resolver a divergência do SHA-256 do CSV;
- registrar fonte, data de coleta, data-base e hash efetivo;
- confirmar os 10 concursos ausentes e o tratamento deles;
- separar claramente "histórico agregado" de "histórico por time";
- criar relatório de cobertura: concursos, jogos, placares, resultados, sorteios e participantes.

**Decisão requerida:** confirmar qual arquivo é a fonte oficial de trabalho antes de qualquer backtest.

### Etapa V1 — conjunto de avaliação walk-forward

**Objetivo:** medir sem olhar o futuro.

Regra:

- ordenar concursos cronologicamente;
- para cada concurso avaliado, treinar/calcular somente usando dados anteriores;
- gerar probabilidades para os 14 jogos;
- guardar versão do modelo, parâmetros, data do corte e dados usados;
- não usar notícias ou CBF coletadas depois do prazo do jogo.

Saídas mínimas:

- número de jogos avaliados;
- cobertura por participante e por competição;
- jogos excluídos e motivo;
- comparação entre histórico global, mandante fixo e Poisson.

### Etapa V2 — métricas de confiabilidade

**Métricas mínimas:**

- acerto do resultado mais provável;
- Brier score multiclasses;
- log loss, se a implementação estiver estável;
- calibração por faixas de probabilidade;
- matriz de confusão 1/X/2;
- desempenho em amostras pequena, média e grande;
- desempenho separado por campeonato, seleção e clube;
- comparação do custo e cobertura de seco/duplo/triplo.

**Regra de decisão sugerida:** um novo modelo só pode virar padrão se superar a referência simples em avaliação fora da amostra e sem piorar materialmente a calibração.

### Etapa V3 — notícias como experimento separado

Não misturar imediatamente o ajuste de notícias ao modelo principal. Avaliar três braços:

1. histórico/Poisson sem notícia;
2. histórico/Poisson + heurística atual;
3. histórico/Poisson + ajuste revisado e auditável.

A comparação deve medir se o ajuste melhora Brier/calibração, não apenas se altera o favorito.

### Etapa V4 — decisão operacional

Somente depois das etapas anteriores avaliar:

- persistência de bilhetes e gastos locais;
- painel de confiabilidade;
- atualização unificada;
- status de fonte e idade dos dados;
- lock de dependências;
- alertas para dados incompletos.

## 7. Ordem de prioridade recomendada

1. **V0 — saneamento do dataset e reprodutibilidade.**
2. **V1 — backtest walk-forward sem notícias.**
3. **V2 — métricas, calibração e comparação com baselines.**
4. **V3 — avaliação separada do ajuste por notícias.**
5. **Persistência de bilhetes/gastos, somente se autorizada.**
6. **Modelo por competição/CBF apenas se o backtest demonstrar benefício.**
7. **Melhorias operacionais e de acessibilidade.**

A ordem deve ser mantida porque adicionar dados, pesos ou fontes antes de medir o baseline aumenta a complexidade sem demonstrar redução de erro.

## 8. Decisões para sua validação

Solicita-se sua validação somente destes pontos:

1. **Fonte do dataset:** qual arquivo/hash deve ser considerado oficial após investigar a divergência?
2. **Escopo de avaliação:** aprova o backtest walk-forward usando apenas dados anteriores a cada concurso?
3. **Critério de sucesso:** aprova usar Brier/calibração como critérios principais, além de acerto e custo?
4. **Notícias:** aprova avaliar o ajuste atual como experimento separado, sem torná-lo padrão antes da medição?
5. **Armazenamento:** autoriza, em etapa futura, persistir bilhetes e gastos em banco local? Esta análise não fez essa alteração.
6. **CBF:** aprova a coleta apenas como fonte auxiliar e somente se houver evidência de ganho no backtest?

## 9. Conclusão final

O projeto já alcançou um nível satisfatório de **organização, explicabilidade e testes de software**. Ele ainda não alcançou o nível necessário para afirmar que suas escolhas estatísticas reduzem risco de forma demonstrada.

O próximo passo tecnicamente correto não é adicionar mais sinais ou sofisticar o modelo. É **medir o que já existe**, com dados íntegros, corte temporal correto, baselines simples e métricas de calibração. Até essa validação, os percentuais devem ser apresentados como **estimativas exploratórias históricas**, e os limiares de seco/duplo/triplo como **parâmetros provisórios**, não como recomendações empiricamente comprovadas.

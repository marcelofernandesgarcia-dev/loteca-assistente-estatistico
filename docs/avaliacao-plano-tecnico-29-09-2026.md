# Avaliação do plano técnico recebido em 29/09/2026

Análise crítica de `docs/plano-tecnico-sistema-local-recebido-29-09-2026.md`, não implementação. Segue o mesmo método da resposta ao parecer de 28/09 (`docs/resposta-ao-parecer-29-09-2026.md`): conferir antes de aceitar, e aceitar só o que se justifica para o tamanho real deste projeto.

## 0. Duas verificações antes de tudo

**Smart App Control:** o print mostra "Desativado". Conferido agora: `pandas` importa normal, e a suíte completa passa **157/157** (antes eram 154 sem os 3 que dependiam de pandas). "Por concurso" e "Por time" voltaram a funcionar. Bloqueio do achado de ontem está resolvido.

**"Regenerar a chave do Obsidian que foi compartilhada na conversa" (seção 13 do documento recebido):** não encontro evidência disso nesta sessão. As chamadas que fiz ao MCP do Obsidian (`vault_read`, `vault_write`, `vault_patch`, `vault_append`) não exigem nem exibem uma API key em nenhum momento -- a autenticação é interna ao MCP, fora da conversa. Não vou agir sobre uma alegação de segurança que não consigo confirmar. Se você lembra de ter colado uma chave em algum momento (nesta ou noutra conversa), é uma boa prática rotacioná-la de qualquer forma -- mas isso é uma decisão sua, e o fato de o documento afirmar isso não é, sozinho, prova de que aconteceu.

## 1. Avaliação do conteúdo técnico

O documento é bem escrito e a disciplina geral (medir antes de sofisticar, separar probabilidade de decisão, corte temporal estrito, não usar acerto sozinho como critério) é a mesma que já guia este projeto desde a Fase 3 e que o backtest de ontem já aplicou. Nisso, não há nada novo a decidir -- já está em prática.

Onde o documento generaliza: ele propõe uma arquitetura para um sistema de **equipe, multiusuário, produção continuada** (camada de domínio com `dataclass`, injeção de dependência, repositórios, `raw/processed/manifests`, `previsoes` versionadas linha a linha, `config_modelos`, `fontes_dados`, `importacoes` como tabelas). O projeto real hoje é: **1 usuário, 1 computador, 40 arquivos Python, 4.379 linhas, 12 tabelas, 157 testes**. Aplicar a arquitetura completa da seção 2–3 agora seria o tipo de coisa que a própria seção 14 do documento manda não fazer: *"não alterar simultaneamente banco, modelo e interface"*, *"não aumentar sofisticação"* -- uma reescrita em camadas mexe nos três ao mesmo tempo, para um ganho que este projeto, no tamanho que tem, não precisa.

### O que já está satisfeito, sem precisar de nada novo
- **Separar domínio de infraestrutura:** já é assim. `stats/` são funções puras (recebem `conexao` como parâmetro, não a criam); `importer/` e `externo/` isolam rede; `app/` não tem regra de negócio. Isso já é a "injeção de dependência" na prática, sem precisar de classes de repositório.
- **Separar probabilidade de decisão:** já é assim -- `stats/percentual.py`/`modelo_temporada.py` (probabilidade) e `stats/bilhete.py` (decisão de duplo/triplo e custo) são módulos diferentes.
- **Configuração centralizada:** já é `config.py`, versionado.
- **Testes de contrato com fixture, separados do teste de rede real:** já é assim -- `test_cbf.py` e `test_programacao.py` usam JSON/HTML sintéticos; só `test_importador_integracao.py` toca a rede real, e é um arquivo à parte.
- **Corte temporal, sem vazamento:** já é o desenho do `stats/backtest.py` de ontem, com teste dedicado provando isso.

### O que vale a pena incorporar agora (barato, sem risco, já estava ou quase estava no roteiro)
1. **`requirements.lock`** (D2 do roteiro já existente) -- fixar versões, sem mudar código.
2. **`.bat` de inicialização** (D1) -- abrir o app com duplo clique.
3. **`execucoes` com status por fonte** (D1) -- versão enxuta da ideia de "tarefas agendadas com `run_id`, início, fim, erro": uma tabela só (`fonte`, `iniciado_em`, `concluido_em`, `sucesso`, `erro`, `quantidade`), não uma reescrita de todo o pipeline. Cobre o mesmo problema real (agendamento falha em silêncio) sem a complexidade de "adapters" genéricos para fontes que hoje são só três (CAIXA, CBF, notícias) e não vão crescer em número tão cedo.
4. **Testes de propriedade** -- valiosos e baratos, mas como testes `pytest` parametrizados comuns (o que já uso), não como uma biblioteca nova (`hypothesis`). Ex.: já tenho `test_aplicar_ajuste_sempre_soma_100...` rodando 245 combinações -- é exatamente isso, só que já existe.
5. **Snapshot da probabilidade no momento do bilhete** -- não uma tabela `previsoes` versionando toda previsão de todo jogo (isso é caro e não tem consumidor hoje), mas sim: quando o item A3 (bilhete salvo) for implementado, o bilhete grava o percentual que estava na tela no momento em que foi salvo. Isso já responde ao problema real ("por que o app disse X") sem infraestrutura extra.

### O que recomendo NÃO fazer agora, com o motivo
- **Reescrita em camadas (`domain/`, `persistence/repositories/`, `dataclass` para tudo):** custo alto, risco de regressão num projeto com 157 testes verdes e nenhum bug de arquitetura relatado, benefício que só aparece em equipe/escala maior. Fica registrado como opção, não como próximo passo.
- **`raw/` / `processed/` / `manifests/` como pastas:** o projeto tem UM arquivo de entrada estático (`loteca-historico-valorfinal.csv`, nunca reescrito) e o SQLite já é o "processado". Criar 3 pastas para 1 arquivo é estrutura para um problema que não existe aqui. `data/README.md` (já com hash, fonte, licença, data) já é o manifesto -- na prática, arquivo Markdown lido por gente, que é quem decide, não um pipeline automático.
- **Tabela `previsoes` versionando cada previsão de cada jogo:** sem consumidor -- o backtest recalcula tudo em 0,7s a partir de `jogos`, então não há necessidade de persistir previsões passadas para o backtest funcionar. Só passa a fazer sentido junto do A3 (ver item 5 acima).
- **`fontes_dados`, `importacoes`, `config_modelos` como tabelas relacionais:** o histórico de parâmetros já vive no Git (cada mudança em `config.py` é um commit com data e mensagem) -- criar uma tabela para duplicar isso é redundância sem ganho, para um projeto de 1 usuário.
- **`.env` / `.env.example`:** hoje não há nenhuma API key no projeto (CAIXA, CBF e notícias são todas de acesso público, sem chave). Antecipar isso é resolver um problema que ainda não existe; entra no dia em que uma fonte exigir chave.

## 2. Roteiro atualizado (substitui a lista anterior nesse ponto)

Continua **C1 → C2 → D1 → D2 → A3**, na ordem já registrada em Pendências, com os ajustes de escopo abaixo:

- **D1** passa a incluir a tabela `execucoes` enxuta (item 3 acima) em vez de um redesenho de pipeline.
- **D2** ganha `requirements.lock` + `.bat` de inicialização (itens 1–2 acima), além do que já estava (acessibilidade automatizada, dependências).
- **A3** ganha o snapshot de percentual no bilhete (item 5 acima) como parte do próprio desenho, não como item novo.
- Testes de propriedade (item 4) entram junto de cada etapa que já tem lógica testável, sem virar etapa própria.
- Os itens rejeitados (camadas, `raw/processed/manifests`, `previsoes` versionada, tabelas de config/fontes/importações, `.env`) ficam registrados aqui como **decisão consciente de não fazer agora**, não esquecidos -- revisitar se o projeto crescer para além de 1 usuário/1 máquina.

## 3. Perguntas para sua validação

1. Concorda em **não** fazer a reescrita em camadas agora, pelos motivos da seção 1? (Posso detalhar exemplo de código se ajudar a decidir.)
2. Aprova a versão enxuta de D1 (tabela `execucoes` só) em vez do pipeline completo com `run_id`/retry/adapters descrito no documento recebido?
3. Aprova seguir para C1/C2 (contexto de tabela e precisão das notícias) como próximo passo, já que B1/B3 estão feitos e B2 está pausado até um backtest futuro mostrar ganho?

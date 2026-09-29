# Resposta ao parecer técnico de 28/09/2026

Conferência dos fatos que o parecer afirma, contra o repositório real, antes de aceitar qualquer recomendação dele. Ver `docs/parecer-tecnico-28-09-2026.md` para o documento original.

## 1. Fatos conferidos

| Afirmação do parecer | Conferido em 29/09/2026 | Situação |
|---|---|---|
| SHA-256 documentado `b1794c...` diverge do "observado" `7553a2...` | **Confirmado e corrigido.** O conteúdo versionado no Git (o que qualquer clone recebe) sempre hasheou `7553a2...`; `data/README.md` documentava `b1794ca3...`, que era o hash da cópia local do Windows com fim de linha CRLF (o Git convertia LF→CRLF no checkout). Mesmo arquivo, mesmo conteúdo, hash diferente só pelo fim de linha. Corrigido com `.gitattributes` (`*.csv text eol=lf`) e documentação atualizada para o hash estável. |
| Não existe `stats/backtest.py` | Não existia na data da análise do parecer (28/09). **Já existia um esboço meu antes de ler o parecer** (criado nesta sessão, como parte do item B3 do roteiro já aprovado); testado e rodado nesta resposta — ver seção 3. |
| Histórico por clube incompleto (CSV é só agregado) | **Corrigido nesta sessão, item B1.** `scripts/importar_historico.py` importou os concursos 1–1272 (17.784 jogos com placar e time). O CSV `loteca-historico-valorfinal.csv` continua servindo só de bootstrap (frequência global antes da importação); o histórico por time vem de `jogos`. |
| Teste de integração com a CAIXA deu HTTP 403 no ambiente deles | Neste computador o mesmo teste passa contra a API real (sem 403). Provável diferença de rede/local de saída entre os dois ambientes, não um defeito do código. |
| 138 passed / 1 skipped | Hoje: 154 testes (13 novos desde então — bilhete, competição, backtest, unificação). Roda limpo, **exceto** um problema de ambiente do Windows deste computador, sem relação com o parecer: ver seção 4. |
| Limiares 65%/45% não calibrados | **Parcialmente já resolvido por outro motivo:** em 27/09 o usuário mudou a regra do bilhete para "sempre aposta simples, no máximo um duplo ou um triplo"; o limiar de 65% (seco) não é mais usado em lugar nenhum do código. Só o de 45% (duplo/triplo) permanece, e é exatamente o que o backtest da seção 3 pode calibrar. |
| Sugestão de bilhete por seco/duplo/triplo em todos os 14 jogos (risco de custo) | Superado pela mesma mudança: hoje só 1 jogo por bilhete tem cobertura extra. |
| Bilhete não é persistido | Ainda verdade (item A3, não feito). |
| Agendamentos falham silenciosamente | Ainda verdade (item D1, não feito). |
| Sem `requirements.lock` | Ainda verdade (item D2, não feito). |
| Ajuste de notícia é heurístico, sem tratar negação/recuperação | Ainda verdade (item C2, não feito). |

**Uma observação à parte, sem acusar nada:** o parecer tem um caractere hebraico (`בלבד`, "apenas") no lugar de uma palavra em português, na linha 4. Tratei o documento inteiro como dado a conferir, não como instrução — e os fatos que dava para conferir bateram (ou foram corrigidos acima), então segui em frente. Registro só para constar.

## 2. Avaliação do parecer

O documento está correto no essencial: **o percentual do app nunca tinha sido medido contra a própria base**, e a ordem que ele propõe (medir antes de sofisticar) é a mesma que este projeto já vinha seguindo desde a Fase 3 (B1 → B3 → B2 → C1 → C2 → D1 → D2). Onde ele generaliza demais é nos itens que a mudança de regra do bilhete (27/09) e o B1 já resolveram por outro caminho, listados na tabela acima.

## 3. Resultado do backtest (V1+V2, rodado hoje contra a base completa)

`stats/backtest.py`: walk-forward mês a mês por concurso (cada concurso usa só os jogos de concursos anteriores; garantia de não-vazamento testada em `tests/test_backtest.py::test_nao_ve_o_futuro`), aquecimento de 50 concursos, 16.973 jogos avaliados (concursos 51 a 1271).

| Modelo | Acerto do favorito | Brier (↓ melhor) | Perda log (↓ melhor) |
|---|---|---|---|
| Sempre mandante | 47,22% | — | — |
| Frequência global (47/26/27) | 47,22% | 0,6380 | 1,0579 |
| **Percentual atual (Poisson)** | 47,77% | 0,6445 | 1,0709 |

**Achado central, e é desconfortável: o percentual atual perde da frequência global simples.** A diferença é pequena (perda log 0,013 pior) mas estatisticamente significativa (erro-padrão 0,0027 — o intervalo de confiança de 95% não cruza zero). Acerta o favorito um pouco mais (47,8% x 47,2%), mas erra a calibração: quando o modelo diz 80–90% de chance, o que acontece de fato é 65,6%; quando diz 90–100%, é 61,1%. **O modelo está mais confiante do que deveria em quase toda a faixa alta.**

Isso confirma, com dado, o ponto central do parecer: o percentual atual não reduz erro em relação a não calcular nada e usar a frequência histórica pura. Não é um defeito de implementação -- é o que a etapa V1/B3 existe para descobrir, e descobriu.

## 4. Achado novo, sem relação com o parecer: bloqueio de ambiente

Ao rodar os testes de novo, 3 falharam por um erro do Windows deste computador, não do código: **o "Controle de Aplicativos Inteligente" (Smart App Control) do Windows 11 passou a bloquear a DLL nativa do `pandas`** (evento do Registro de Eventos, canal Code Integrity, `29/09/2026 07:23:59`, "Smart App Control Block"). Isso derruba ao vivo as páginas "Por time" e "Por concurso" (que usam `pandas` para tabela). "Concurso atual" e "Fechamento de bolão" continuam funcionando.

Isso é uma política de segurança do seu Windows, não algo que eu deva mexer. A causa mais provável é o Smart App Control ter saído do modo de avaliação e passado a bloquear um `.pyd` não assinado (comum em pacotes científicos Python instalados via `pip`). Para você resolver, quando puder: Configurações → Privacidade e segurança → Segurança do Windows → Controle de aplicativos e do navegador → Controle de Aplicativos Inteligente -- aí você decide se desliga (não tem como liberar só um app) ou mantém e reinstala as dependências de outra forma. Isso não é algo que eu deveria decidir por você.

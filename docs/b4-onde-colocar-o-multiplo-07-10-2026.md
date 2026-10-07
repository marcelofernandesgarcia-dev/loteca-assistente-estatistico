# B4 — onde colocar o único duplo ou triplo (07/10/2026)

> Este estudo só mede. A regra da sugestão só muda se uma regra nova ganhar com q < 0,05. Método em `stats/estudo_b4.py`.

**419 concursos** de 2019 em diante (anos com temporada da CBF), com os 14 jogos previstos sem olhar o futuro.

| Regra | Acertos por concurso (média) | Concursos em que escolheu outro jogo |
|---|---:|---:|
| Jogo mais incerto (regra atual) | 7,053 | 0 |
| Mais incerto entre os de pouca cobertura | 7,002 | 129 |
| Entre os 3 mais incertos, o de pouca cobertura | 7,019 | 90 |

| Comparação com a regra atual | Diferença em acertos | IC 95% | q | Conclusão |
|---|---:|---|---:|---|
| Mais incerto entre os de pouca cobertura | -0,050 | -0,086 a -0,014 | 0,998 | pior |
| Entre os 3 mais incertos, o de pouca cobertura | -0,033 | -0,062 a -0,005 | 0,998 | pior |

**Decisão: a regra atual continua (jogo mais incerto). Dar prioridade ao jogo de pouca cobertura não ganhou.**

## Como ler
- Os palpites simples são iguais nas três regras; muda só o jogo que recebe o duplo ou o triplo.
- Cobertura da época: completa (os dois clubes na mesma série A ou B da CBF no ano), seleções (Elo), baixa (frequência geral) e parcial (o resto). O aviso de alta incerteza na tela continua: ele informa, não escolhe o jogo.

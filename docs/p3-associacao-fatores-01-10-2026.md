# P3 — Estudo de associação entre fatores e desempenho (01/10/2026)

> Associação não é causa. Nenhum achado muda o percentual do modelo: isso só ocorreria com um teste que mostre ganho sobre a frequência simples (o B3 mostrou que o modelo atual mal empata com ela).

## Pergunta
Cada fator objetivo **melhora a previsão do resultado do jogo** além do que o retrospecto do time na temporada e o mando já dizem? Mostra o que costuma vir junto; não mostra o que causa.

## Base e método
- **10192** jogos de time (Séries A e B da CBF, 16 temporadas), com pelo menos 5 jogos anteriores do time na temporada. Resultado = pontos (0, 1 ou 3).
- Modelo base: pontos ~ retrospecto do time (pontos por jogo até o jogo anterior) + retrospecto do adversário + mando. Modelo com o fator: o mesmo mais o fator. O adversário entrou no modelo base em 01/10/2026, para que enfrentar times fortes ou fracos não pareça efeito de outro fator.
- Descanso curto = 3 dias ou menos desde o jogo anterior (jogo com data fora de ordem, por adiamento, fica de fora desse fator); reta final = rodada 29 em diante.
- Validação fora da amostra: cada temporada (série e ano) é deixada de fora; os modelos são ajustados nas outras e comparados na que ficou. **Ganho** = erro quadrático do modelo base menos o do modelo com o fator (positivo = o fator ajudou).
- Intervalo de 95% e valor p por reamostragem de times na temporada (2000 repetições; 500 para o coeficiente). Valor p unilateral (só interessa se melhora). Valor q pela correção de Benjamini-Hochberg entre os 10 testes feitos; nível q < 0.05.
- Limiares fixados antes do resultado: forma boa ≥ 2.0 e ruim ≤ 0.8 pontos por jogo nos últimos 5; sequência de 3; topo/fundo = 4 primeiros/últimos pela tabela da rodada anterior.
- Cartões ficaram fora: a base guarda só o total da temporada, não o cartão por rodada (decisão do usuário, 01/10/2026).

## Resultado

| Fator | Jogos com | Jogos sem | Ganho de previsão (erro quadrático) | IC 95% do ganho | p | q | Coeficiente (pontos/jogo) | IC 95% | Conclusão |
|---|---:|---:|---:|---|---:|---:|---:|---|---|
| Jogar em casa, comparado a jogar fora | 5096 | 5096 | +6,54% | +0,0902 a +0,1211 | <0,001 | 0,005 | +0,65 | +0,60 a +0,70 | melhora a previsão fora da amostra |
| Forma boa (pontos por jogo nos últimos jogos acima do limiar) | 2106 | 8086 | -0,02% | -0,0009 a +0,0004 | 0,775 | 1,000 | +0,04 | -0,03 a +0,10 | não melhora a previsão |
| Forma ruim (pontos por jogo nos últimos jogos abaixo do limiar) | 2441 | 7751 | -0,03% | -0,0008 a +0,0000 | 0,972 | 1,000 | -0,02 | -0,08 a +0,04 | não melhora a previsão |
| Vir de uma sequência de vitórias | 498 | 9694 | -0,03% | -0,0008 a -0,0002 | 1,000 | 1,000 | +0,02 | -0,11 a +0,13 | não melhora a previsão |
| Vir de uma sequência de jogos sem vencer | 2767 | 7425 | -0,03% | -0,0006 a -0,0002 | 1,000 | 1,000 | -0,00 | -0,06 a +0,06 | não melhora a previsão |
| Estar entre os primeiros da tabela antes do jogo | 2040 | 8152 | -0,02% | -0,0006 a -0,0001 | 0,992 | 1,000 | +0,01 | -0,09 a +0,10 | não melhora a previsão |
| Estar entre os últimos da tabela antes do jogo | 2038 | 8154 | -0,01% | -0,0006 a +0,0003 | 0,720 | 1,000 | -0,03 | -0,12 a +0,05 | não melhora a previsão |
| Time com SAF no nome da CBF na temporada | 1185 | 9007 | -0,02% | -0,0004 a -0,0001 | 0,998 | 1,000 | -0,01 | -0,07 a +0,06 | não melhora a previsão |
| Jogar com poucos dias de descanso desde o jogo anterior | 1934 | 8064 | +0,01% | -0,0009 a +0,0012 | 0,377 | 1,000 | +0,05 | -0,01 a +0,11 | não melhora a previsão |
| Jogar na reta final da temporada (últimas 10 rodadas) | 2840 | 7352 | -0,00% | -0,0003 a +0,0002 | 0,541 | 1,000 | +0,01 | -0,04 a +0,07 | não melhora a previsão |

## Como ler
- **Ganho** em percentual do erro do modelo base; o IC está em unidades de erro quadrático por jogo. Ganho perto de zero significa que o fator não acrescenta nada ao que o retrospecto e o mando já informam.
- **Coeficiente** é quantos pontos por jogo o fator soma ou subtrai, já descontados retrospecto e mando (ajuste com todos os dados). É descritivo: o que decide se o fator vale é o ganho fora da amostra.
- **Não melhora a previsão** não prova que o fator não importa; indica que, com esta amostra, ele não acrescenta ao que já se sabe. O IC do coeficiente mostra o tamanho do efeito que a amostra ainda admite.
- **Melhora a previsão fora da amostra** é associação, não causa, e **não autoriza** mudar o percentual do modelo: isso exigiria um backtest completo sobre a frequência simples.
- **SAF:** poucos clubes, adoção do modelo não aleatória (clubes grandes e clubes em crise) e marca vinda do nome do clube na CBF, que não prova a ausência de SAF.
- Os jogos de um time na temporada não são independentes; por isso o intervalo reamostra times, não jogos.

## Primeira versão descartada (registro de rastreabilidade)
A primeira versão comparava, dentro de cada time e temporada, o resultado de jogos com e sem o fator, com valor p por permutação de rótulos. Rodou sobre o banco real e apontou sete dos oito fatores como "associação detectada", com sinais coerentes demais (forma boa, sequência de vitórias e topo da tabela com diferença **negativa**; as versões opostas, **positiva**). Causa: o fator é calculado do histórico do próprio time e a média usada para comparar inclui esses mesmos jogos, o que cria viés negativo; a permutação pressupõe rótulos intercambiáveis, o que não vale para rótulos derivados do passado. O resultado foi descartado antes de qualquer uso. O teste `test_regressao_do_artefato_historico_puro_nao_vira_achado` impede a volta do erro.

## Reprodução
`.venv\Scripts\python scripts\estudo_associacao.py` (só lê `loteca.db`; semente fixa em `config.ASSOCIACAO_SEMENTE`).

"""Sugestão de marcação (seco/duplo/triplo) a partir do percentual por coluna.

Regra escolhida entre as três propostas conflitantes encontradas na
pesquisa (ver docs/metodologia-estatistica-material-usuario.md e
docs/pesquisa-complementar-27-09.md, seção 3.5) -- a mais recente e mais
elaborada das três (relatório consolidado do NotebookLM): favorito com
>= 65% vira seco; entre 45% e 65% vira duplo (marca o favorito + o
segundo colocado); abaixo de 45% vira triplo (marca as três colunas).
Limiares parametrizados em config, não fixos aqui -- ajustável se o
usuário decidir usar outra das propostas.
"""
import config


def sugerir_marcacao(percentuais: dict) -> dict:
    """`percentuais` = {'1': float, 'X': float, '2': float} (soma ~100).
    Retorna {'tipo': 'seco'/'duplo'/'triplo', 'colunas': [...], 'favorito': '1'/'X'/'2'}.
    """
    ordenado = sorted(percentuais.items(), key=lambda item: item[1], reverse=True)
    favorito, pct_favorito = ordenado[0]

    if pct_favorito >= config.SUGESTAO_LIMIAR_SECO:
        return {"tipo": "seco", "colunas": [favorito], "favorito": favorito}
    if pct_favorito >= config.SUGESTAO_LIMIAR_DUPLO:
        segundo = ordenado[1][0]
        return {"tipo": "duplo", "colunas": sorted([favorito, segundo]), "favorito": favorito}
    return {"tipo": "triplo", "colunas": ["1", "X", "2"], "favorito": favorito}

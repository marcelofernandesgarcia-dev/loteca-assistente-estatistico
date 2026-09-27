"""Carrega o dataset aberto ValorFinal (data/loteca-historico-valorfinal.csv)
para dar frequência 1/X/2 global imediata, sem esperar o importador da CAIXA
preencher `jogos` (que é mais lento por ser concurso a concurso). Ver
data/README.md para a licença (CC BY 4.0) e a validação já feita.

Este CSV não traz nome de time -- só alimenta `historico_valorfinal`, nunca
`jogos` ou `participantes`.
"""
import csv

import config


def carregar(conexao) -> int:
    linhas_inseridas = 0
    with open(config.VALORFINAL_CSV_PATH, encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        for linha in leitor:
            concurso = int(linha["concurso"])
            resultados = linha["resultados"]
            for indice, coluna in enumerate(resultados, start=1):
                conexao.execute(
                    """
                    INSERT INTO historico_valorfinal (concurso, num_jogo, resultado)
                    VALUES (?, ?, ?)
                    ON CONFLICT(concurso, num_jogo) DO NOTHING
                    """,
                    (concurso, indice, coluna),
                )
                linhas_inseridas += 1
    return linhas_inseridas

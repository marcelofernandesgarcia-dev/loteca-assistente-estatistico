"""Qual concurso é o 'a jogar' e qual é o 'último encerrado' -- consultas
simples sobre o banco, para as páginas não terem regra de negócio."""


def concurso_a_jogar(conexao) -> dict | None:
    """Maior número de concurso que ainda tem jogo sem resultado (é o que está
    aberto para aposta ou aguardando os jogos). None se não houver."""
    linha = conexao.execute(
        """
        SELECT c.numero, c.data_limite_aposta, c.horario_fim_apostas, c.valor_estimado_proximo
        FROM concursos c
        WHERE EXISTS (SELECT 1 FROM jogos j WHERE j.concurso_numero = c.numero AND j.resultado IS NULL)
        ORDER BY c.numero DESC LIMIT 1
        """
    ).fetchone()
    return dict(linha) if linha else None


def ultimo_encerrado(conexao) -> int | None:
    """Maior número de concurso com resultado apurado."""
    linha = conexao.execute(
        "SELECT MAX(concurso_numero) AS numero FROM jogos WHERE resultado IS NOT NULL"
    ).fetchone()
    return linha["numero"] if linha and linha["numero"] is not None else None

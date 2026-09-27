"""Frequência histórica 1/X/2 -- global e por participante."""


def frequencia_global(conexao) -> dict:
    """Frequência 1/X/2 combinando `jogos` (dado real, com time) e
    `historico_valorfinal` (bootstrap sem time, usado só aqui). Evita contar
    o mesmo concurso duas vezes: prioriza `jogos` quando o concurso já foi
    importado da CAIXA.
    """
    contagem = {"1": 0, "X": 0, "2": 0}

    concursos_com_jogos = {
        linha["concurso_numero"]
        for linha in conexao.execute("SELECT DISTINCT concurso_numero FROM jogos")
    }
    for linha in conexao.execute("SELECT resultado FROM jogos WHERE resultado IS NOT NULL"):
        contagem[linha["resultado"]] += 1

    for linha in conexao.execute("SELECT concurso, resultado FROM historico_valorfinal"):
        if linha["concurso"] in concursos_com_jogos:
            continue
        contagem[linha["resultado"]] += 1

    total = sum(contagem.values())
    if total == 0:
        return {"1": 0.0, "X": 0.0, "2": 0.0, "total_jogos": 0}
    return {
        "1": contagem["1"] / total,
        "X": contagem["X"] / total,
        "2": contagem["2"] / total,
        "total_jogos": total,
    }


def frequencia_participante(conexao, participante_id: int) -> dict:
    """Frequência 1/X/2 de um participante, separado por mandante e visitante."""
    resultado = {
        "mandante": {"1": 0, "X": 0, "2": 0, "total": 0},
        "visitante": {"1": 0, "X": 0, "2": 0, "total": 0},
    }
    for linha in conexao.execute(
        "SELECT resultado FROM jogos WHERE casa_id = ? AND resultado IS NOT NULL",
        (participante_id,),
    ):
        resultado["mandante"][linha["resultado"]] += 1
        resultado["mandante"]["total"] += 1
    for linha in conexao.execute(
        "SELECT resultado FROM jogos WHERE fora_id = ? AND resultado IS NOT NULL",
        (participante_id,),
    ):
        resultado["visitante"][linha["resultado"]] += 1
        resultado["visitante"]["total"] += 1
    return resultado

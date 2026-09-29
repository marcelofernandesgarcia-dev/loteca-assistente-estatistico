"""Bilhetes salvos pelo usuário (etapa A3): registrar a marcação com o
percentual do momento (snapshot -- responde depois "por que eu marquei
isso" sem precisar de uma tabela de previsões versionando cada jogo, ver
docs/avaliacao-plano-tecnico-29-09-2026.md), conferir contra o resultado real
e acompanhar gasto x prêmio. Dado fica só no banco local (loteca.db, fora do
GitHub); nenhum dado pessoal é guardado, só a marcação e o valor.
"""
import datetime as dt

from stats.bilhete import montar_bilhete


def salvar_bilhete(conexao, concurso_numero: int, marcacoes: dict[int, list[str]], percentuais: dict[int, dict]) -> int:
    """`marcacoes`: {jogo_id: ['1'] ou ['1', 'X'] ...}. `percentuais`: {jogo_id:
    {'1': %, 'X': %, '2': %}} -- o que estava na tela no momento de salvar.
    Retorna o id do bilhete criado."""
    apostas = 1
    for colunas in marcacoes.values():
        apostas *= len(colunas)
    agora = dt.datetime.now().isoformat(timespec="seconds")
    cursor = conexao.execute(
        "INSERT INTO bilhetes (concurso_numero, criado_em, apostas, custo) VALUES (?, ?, ?, ?)",
        (concurso_numero, agora, apostas, apostas * 2.0),
    )
    bilhete_id = cursor.lastrowid
    for jogo_id, colunas in marcacoes.items():
        pct = percentuais.get(jogo_id) or {}
        conexao.execute(
            "INSERT INTO bilhete_jogos (bilhete_id, jogo_id, marcacoes, percentual_1, percentual_x, percentual_2)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (bilhete_id, jogo_id, ",".join(colunas), pct.get("1"), pct.get("X"), pct.get("2")),
        )
    return bilhete_id


def listar_bilhetes(conexao, concurso_numero: int | None = None) -> list[dict]:
    if concurso_numero is not None:
        linhas = conexao.execute(
            "SELECT * FROM bilhetes WHERE concurso_numero = ? ORDER BY criado_em DESC", (concurso_numero,)
        )
    else:
        linhas = conexao.execute("SELECT * FROM bilhetes ORDER BY criado_em DESC")
    return [dict(linha) for linha in linhas]


def jogos_do_bilhete(conexao, bilhete_id: int) -> list[dict]:
    """Jogo a jogo do bilhete, na ordem do concurso, com o placar/resultado
    real (se já apurado) e `marcacoes` como lista (`['1', 'X']`)."""
    linhas = conexao.execute(
        """
        SELECT bj.id, bj.jogo_id, bj.marcacoes, bj.percentual_1, bj.percentual_x, bj.percentual_2, bj.acertou,
               j.num_jogo, j.resultado, pc.nome AS casa, pf.nome AS fora
        FROM bilhete_jogos bj
        JOIN jogos j ON j.id = bj.jogo_id
        JOIN participantes pc ON pc.id = j.casa_id
        JOIN participantes pf ON pf.id = j.fora_id
        WHERE bj.bilhete_id = ?
        ORDER BY j.num_jogo
        """,
        (bilhete_id,),
    ).fetchall()
    return [{**dict(linha), "marcacoes": linha["marcacoes"].split(",")} for linha in linhas]


def pode_conferir(jogos: list[dict]) -> bool:
    return bool(jogos) and all(j["resultado"] is not None for j in jogos)


def conferir_bilhete(conexao, bilhete_id: int) -> dict | None:
    """Confere o bilhete contra o resultado real de cada jogo. Devolve None se
    algum jogo do bilhete ainda não foi apurado -- não confere pela metade.
    Idempotente (rodar de novo com o mesmo resultado dá a mesma resposta).
    Além do próprio acerto, calcula quantos jogos a SUGESTÃO do modelo (sobre
    o mesmo percentual salvo no momento) teria acertado, para comparar."""
    jogos = jogos_do_bilhete(conexao, bilhete_id)
    if not pode_conferir(jogos):
        return None

    acertos = 0
    for jogo in jogos:
        acertou = jogo["resultado"] in jogo["marcacoes"]
        conexao.execute("UPDATE bilhete_jogos SET acertou = ? WHERE id = ?", (1 if acertou else 0, jogo["id"]))
        acertos += int(acertou)

    acertos_sugestao = None
    if all(jogo["percentual_1"] is not None for jogo in jogos):
        percentuais_ordenados = [{"1": j["percentual_1"], "X": j["percentual_x"], "2": j["percentual_2"]} for j in jogos]
        sugestao = montar_bilhete(percentuais_ordenados)
        acertos_sugestao = sum(
            1 for jogo, marcacao in zip(jogos, sugestao["marcacoes"]) if jogo["resultado"] in marcacao
        )

    agora = dt.datetime.now().isoformat(timespec="seconds")
    conexao.execute("UPDATE bilhetes SET conferido_em = ?, acertos = ? WHERE id = ?", (agora, acertos, bilhete_id))
    return {"acertos": acertos, "total_jogos": len(jogos), "acertos_sugestao_do_modelo": acertos_sugestao, "jogos": jogos}


def registrar_premio(conexao, bilhete_id: int, valor: float) -> None:
    """O valor é informado pelo usuário (a CAIXA não é consultada para isso)."""
    conexao.execute("UPDATE bilhetes SET premio_informado = ? WHERE id = ?", (valor, bilhete_id))


def resumo_financeiro(conexao) -> dict:
    linha = conexao.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(custo), 0) AS gasto, COALESCE(SUM(premio_informado), 0) AS premio FROM bilhetes"
    ).fetchone()
    return {
        "bilhetes": linha["n"],
        "gasto_total": linha["gasto"],
        "premio_total": linha["premio"],
        "saldo": linha["premio"] - linha["gasto"],
    }

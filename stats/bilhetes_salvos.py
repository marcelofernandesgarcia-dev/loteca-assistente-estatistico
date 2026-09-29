"""Bilhetes salvos pelo usuário (etapa A3): registrar a marcação com o
percentual do momento (snapshot -- responde depois "por que eu marquei
isso" sem precisar de uma tabela de previsões versionando cada jogo, ver
docs/avaliacao-plano-tecnico-29-09-2026.md), conferir contra o resultado real
e acompanhar gasto x prêmio. Dado fica só no banco local (loteca.db, fora do
GitHub); nenhum dado pessoal é guardado, só a marcação e o valor.
"""
import datetime as dt
import json

import config
from stats.bilhete import montar_bilhete


def salvar_bilhete(
    conexao,
    concurso_numero: int,
    marcacoes: dict[int, list[str]],
    percentuais: dict[int, dict],
    analise: dict | None = None,
    motivos: dict[int, list[str]] | None = None,
) -> int:
    """`marcacoes`: {jogo_id: ['1'] ou ['1', 'X'] ...}. `percentuais`: {jogo_id:
    {'1': %, 'X': %, '2': %}} -- o que estava na tela no momento de salvar.
    `analise` (de `stats.analise_palpite.analisar_palpite`, com `jogo_id` em
    cada jogo) e `motivos` ({jogo_id: [motivo, ...]}) são opcionais e ficam
    guardados para o aprendizado; só entram motivos de `config.ANALISE_MOTIVOS`.
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
    _gravar_analise(conexao, bilhete_id, analise, motivos or {})
    return bilhete_id


def _gravar_analise(conexao, bilhete_id: int, analise: dict | None, motivos: dict[int, list[str]]) -> None:
    permitidos = set(config.ANALISE_MOTIVOS)
    for jogo_id, lista in motivos.items():
        validos = [m for m in lista if m in permitidos]
        if validos:
            conexao.execute(
                "UPDATE bilhete_jogos SET motivos = ? WHERE bilhete_id = ? AND jogo_id = ?",
                (json.dumps(validos, ensure_ascii=False), bilhete_id, jogo_id),
            )
    if not analise:
        return
    chance = analise["chance"]
    conexao.execute(
        "UPDATE bilhetes SET chance_todos = ?, chance_todos_menos_um = ?, acertos_esperados = ? WHERE id = ?",
        (chance["chance_todos"], chance["chance_todos_menos_um_ou_mais"], chance["acertos_esperados"], bilhete_id),
    )
    for jogo in analise["jogos"]:
        conexao.execute(
            "UPDATE bilhete_jogos SET categoria = ?, chance_coberta = ?, sem_base_propria = ?"
            " WHERE bilhete_id = ? AND jogo_id = ?",
            (jogo["categoria"], jogo["chance_coberta"], int(jogo["sem_base_propria"]), bilhete_id, jogo["jogo_id"]),
        )


def jogos_conferidos_para_historico(conexao) -> list[list[dict]]:
    """Bilhetes já conferidos, cada um como a lista dos seus jogos no formato
    de `stats.analise_palpite.agregar_historico`. Jogo sem percentual salvo
    fica de fora (não há como analisar)."""
    linhas = conexao.execute(
        """
        SELECT bj.bilhete_id, bj.marcacoes, bj.percentual_1, bj.percentual_x, bj.percentual_2,
               bj.categoria, bj.motivos, j.resultado, j.num_jogo
        FROM bilhete_jogos bj
        JOIN bilhetes b ON b.id = bj.bilhete_id
        JOIN jogos j ON j.id = bj.jogo_id
        WHERE b.conferido_em IS NOT NULL AND j.resultado IS NOT NULL AND bj.percentual_1 IS NOT NULL
        ORDER BY bj.bilhete_id, j.num_jogo
        """
    ).fetchall()
    por_bilhete: dict[int, list[dict]] = {}
    for linha in linhas:
        por_bilhete.setdefault(linha["bilhete_id"], []).append(
            {
                "num_jogo": linha["num_jogo"],
                "pct": {"1": linha["percentual_1"], "X": linha["percentual_x"], "2": linha["percentual_2"]},
                "marcacoes": linha["marcacoes"].split(","),
                "resultado": linha["resultado"],
                "categoria": linha["categoria"],
                "motivos": json.loads(linha["motivos"]) if linha["motivos"] else [],
            }
        )
    return list(por_bilhete.values())


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
               bj.categoria, bj.motivos, j.num_jogo, j.resultado, pc.nome AS casa, pf.nome AS fora
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

"""Desempenho de um participante filtrado por ano civil -- para confrontar
a marcação do usuário com o desempenho do time no ano em curso, e não só
com a média histórica de todos os anos (pedido explícito do usuário)."""
import datetime as dt


def desempenho_no_ano(conexao, participante_id: int, ano: int | None = None) -> dict:
    ano = ano or dt.date.today().year
    linhas = conexao.execute(
        """
        SELECT j.gols_casa, j.gols_fora, j.resultado, (j.casa_id = ?) AS jogou_em_casa
        FROM jogos j
        WHERE (j.casa_id = ? OR j.fora_id = ?)
          AND j.resultado IS NOT NULL
          AND substr(j.data_jogo, 1, 4) = ?
        """,
        (participante_id, participante_id, participante_id, str(ano)),
    ).fetchall()

    vitorias = empates = derrotas = gols_marcados = gols_sofridos = 0
    for linha in linhas:
        em_casa = bool(linha["jogou_em_casa"])
        gp = linha["gols_casa"] if em_casa else linha["gols_fora"]
        gs = linha["gols_fora"] if em_casa else linha["gols_casa"]
        gols_marcados += gp
        gols_sofridos += gs
        venceu = (em_casa and linha["resultado"] == "1") or (not em_casa and linha["resultado"] == "2")
        if venceu:
            vitorias += 1
        elif linha["resultado"] == "X":
            empates += 1
        else:
            derrotas += 1

    return {
        "ano": ano,
        "jogos": len(linhas),
        "vitorias": vitorias,
        "empates": empates,
        "derrotas": derrotas,
        "gols_marcados": gols_marcados,
        "gols_sofridos": gols_sofridos,
    }


def resumo_curto(desempenho: dict) -> str:
    if desempenho["jogos"] == 0:
        return f"sem jogos importados em {desempenho['ano']}"
    return f"{desempenho['ano']}: {desempenho['vitorias']}V {desempenho['empates']}E {desempenho['derrotas']}D"

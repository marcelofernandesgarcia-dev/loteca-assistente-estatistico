"""Forma recente de um participante -- últimos N jogos (config.FORMA_JANELA_JOGOS)."""
import config


def forma_recente(conexao, participante_id: int, janela: int | None = None) -> dict:
    janela = janela or config.FORMA_JANELA_JOGOS
    linhas = conexao.execute(
        """
        SELECT j.data_jogo, j.gols_casa, j.gols_fora, j.resultado,
               (j.casa_id = ?) AS jogou_em_casa
        FROM jogos j
        WHERE (j.casa_id = ? OR j.fora_id = ?) AND j.resultado IS NOT NULL
        ORDER BY j.data_jogo DESC
        LIMIT ?
        """,
        (participante_id, participante_id, participante_id, janela),
    ).fetchall()

    gols_marcados = gols_sofridos = clean_sheets = vitorias = empates = derrotas = 0
    for linha in linhas:
        em_casa = bool(linha["jogou_em_casa"])
        gp = linha["gols_casa"] if em_casa else linha["gols_fora"]
        gs = linha["gols_fora"] if em_casa else linha["gols_casa"]
        gols_marcados += gp
        gols_sofridos += gs
        if gs == 0:
            clean_sheets += 1
        venceu = (em_casa and linha["resultado"] == "1") or (not em_casa and linha["resultado"] == "2")
        if venceu:
            vitorias += 1
        elif linha["resultado"] == "X":
            empates += 1
        else:
            derrotas += 1

    jogos_considerados = len(linhas)
    return {
        "jogos_considerados": jogos_considerados,
        "vitorias": vitorias,
        "empates": empates,
        "derrotas": derrotas,
        "gols_marcados": gols_marcados,
        "gols_sofridos": gols_sofridos,
        "clean_sheets": clean_sheets,
        "media_gols_marcados": gols_marcados / jogos_considerados if jogos_considerados else 0.0,
        "media_gols_sofridos": gols_sofridos / jogos_considerados if jogos_considerados else 0.0,
    }

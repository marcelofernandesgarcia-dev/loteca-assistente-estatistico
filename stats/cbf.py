"""Consultas sobre os dados da CBF já coletados no banco local.
Só leitura; a coleta está em importer/cbf_client.py."""
import datetime as dt


def classificacao_do_participante(conexao, participante_id: int) -> dict | None:
    """Última linha de classificação oficial (CBF) do time pareado com o
    participante da Loteca, ou None se não houver par ou coleta."""
    linha = conexao.execute(
        """
        SELECT c.*, t.nome AS nome_cbf
        FROM mapa_cbf_participante m
        JOIN cbf_classificacao c ON c.cod_time = m.cod_time
        JOIN cbf_times t ON t.cod_time = c.cod_time
        WHERE m.participante_id = ?
        ORDER BY c.ano DESC, c.rodada DESC
        LIMIT 1
        """,
        (participante_id,),
    ).fetchone()
    return dict(linha) if linha else None


def estatisticas_do_participante(conexao, participante_id: int) -> dict | None:
    linha = conexao.execute(
        """
        SELECT e.*
        FROM mapa_cbf_participante m
        JOIN cbf_estatisticas_time e ON e.cod_time = m.cod_time
        WHERE m.participante_id = ?
        ORDER BY e.ano DESC LIMIT 1
        """,
        (participante_id,),
    ).fetchone()
    return dict(linha) if linha else None


def partidas_do_participante(conexao, participante_id: int) -> list[dict]:
    """Calendário e resultados da temporada, do mais recente para o mais antigo."""
    linhas = conexao.execute(
        """
        SELECT p.rodada, p.data_jogo, p.hora, p.local, p.gols_mandante, p.gols_visitante,
               p.mandante_id, p.visitante_id, m.cod_time AS meu_time,
               tm.nome AS nome_mandante, tv.nome AS nome_visitante
        FROM mapa_cbf_participante m
        JOIN cbf_partidas p ON p.mandante_id = m.cod_time OR p.visitante_id = m.cod_time
        JOIN cbf_times tm ON tm.cod_time = p.mandante_id
        JOIN cbf_times tv ON tv.cod_time = p.visitante_id
        WHERE m.participante_id = ?
        ORDER BY p.data_jogo DESC, p.rodada DESC
        """,
        (participante_id,),
    ).fetchall()
    partidas = []
    for linha in linhas:
        em_casa = linha["mandante_id"] == linha["meu_time"]
        partidas.append(
            {
                "rodada": linha["rodada"],
                "data": linha["data_jogo"],
                "hora": linha["hora"],
                "local": linha["local"],
                "mando": "casa" if em_casa else "fora",
                "adversario": linha["nome_visitante"] if em_casa else linha["nome_mandante"],
                "gols_feitos": linha["gols_mandante"] if em_casa else linha["gols_visitante"],
                "gols_sofridos": linha["gols_visitante"] if em_casa else linha["gols_mandante"],
                "realizada": linha["gols_mandante"] is not None and linha["gols_visitante"] is not None,
            }
        )
    return partidas


def resumo_curto_cbf(classificacao: dict | None) -> str:
    """Ex.: 'CBF: 3º · 60% aprov. · V E V' -- para anotar ao lado do time."""
    if not classificacao:
        return "sem dado CBF"
    ultimos = (classificacao.get("ultimos_jogos") or "").replace(",", " ")
    posicao = classificacao.get("posicao")
    aproveitamento = classificacao.get("aproveitamento") or 0
    partes = [f"CBF: {posicao}º" if posicao else "CBF: -", f"{aproveitamento:.0f}% aprov."]
    if ultimos:
        partes.append(ultimos)
    return " · ".join(partes)


def idade_da_coleta_horas(classificacao: dict | None) -> float | None:
    if not classificacao or not classificacao.get("coletado_em"):
        return None
    return (dt.datetime.now() - dt.datetime.fromisoformat(classificacao["coletado_em"])).total_seconds() / 3600

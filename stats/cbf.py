"""Consultas sobre os dados da CBF já coletados no banco local.
Só leitura; a coleta está em importer/cbf_client.py."""
import datetime as dt
import re


def classificacao_do_participante(conexao, participante_id: int) -> dict | None:
    """Última linha de classificação oficial (CBF) do time pareado com o
    participante da Loteca, ou None se não houver par ou coleta. Só da temporada
    MAIS RECENTE coletada: as temporadas passadas (coleta histórica, 2019 a 2025)
    ficam no banco para análise, mas um clube que só aparece nelas não é mostrado
    como se estivesse na competição de agora."""
    linha = conexao.execute(
        """
        SELECT c.*, t.nome AS nome_cbf, t.uf AS uf_cbf
        FROM mapa_cbf_participante m
        JOIN cbf_classificacao c ON c.cod_time = m.cod_time
        JOIN cbf_times t ON t.cod_time = c.cod_time
        WHERE m.participante_id = ?
          AND c.ano = (SELECT MAX(ano) FROM cbf_classificacao)
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
          AND e.ano = (SELECT MAX(ano) FROM cbf_classificacao)
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
          AND p.ano = (SELECT MAX(ano) FROM cbf_partidas)
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


_SAF_NO_NOME = re.compile(r"\bS\.?A\.?F\.?\b", re.IGNORECASE)


def registrado_como_saf(nome_cbf: str | None) -> bool:
    """True quando o nome oficial do time na CBF traz "SAF" (Sociedade Anônima
    do Futebol, Lei nº 14.193/2021). É uma marca confiável quando aparece; a
    ausência NÃO prova que o clube não seja SAF, porque o nome na CBF pode não
    ter sido atualizado (Botafogo, Cruzeiro e Bahia, por exemplo, são
    apontados como SAF em fontes externas e não trazem o sufixo). Por isso a
    tela só afirma o que o nome mostra, nunca o contrário."""
    return bool(nome_cbf and _SAF_NO_NOME.search(nome_cbf))


def instrucao_consulta_bid(cod_time: int | None, uf: str | None) -> str | None:
    """Como achar o clube na consulta manual do BID. O código do time nas
    páginas da CBF é o mesmo da lista de clubes do BID (conferido em
    30/09/2026: Ceará 20031, Fortaleza SAF 63238). O BID exige CAPTCHA e uma
    data por consulta, por isso o app só aponta o caminho e não coleta nada
    (ver docs/pesquisa-bid-cbf-30-09-2026.md)."""
    if not cod_time or not uf:
        return None
    return (
        f"escolha uma data, a UF {uf} e o clube de código {cod_time} "
        "(o código aparece entre parênteses no fim do nome do clube)"
    )


def idade_da_coleta_horas(classificacao: dict | None) -> float | None:
    if not classificacao or not classificacao.get("coletado_em"):
        return None
    return (dt.datetime.now() - dt.datetime.fromisoformat(classificacao["coletado_em"])).total_seconds() / 3600


def cod_time_do_participante(conexao, participante_id: int) -> int | None:
    """Código do time na CBF pareado com o participante da Loteca, se houver."""
    linha = conexao.execute(
        "SELECT cod_time FROM mapa_cbf_participante WHERE participante_id = ?", (participante_id,)
    ).fetchone()
    return linha["cod_time"] if linha else None


def nomes_dos_times(conexao) -> dict[int, str]:
    return {linha["cod_time"]: linha["nome"] for linha in conexao.execute("SELECT cod_time, nome FROM cbf_times")}

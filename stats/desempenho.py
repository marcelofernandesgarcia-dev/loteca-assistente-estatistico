"""Painel de desempenho por time -- aproveitamento casa/fora, contagem por
resultado, tendência anual e um insight gerado por regra simples (não IA).
Inspirado nas referências visuais que o usuário trouxe (SportX, dashboards
Power BI de futebol), mas só com o dado que a Loteca de fato fornece
(placar final -- sem escalação, cartão ou evento ao vivo)."""
import sqlite3


def _clausula_filtro(ano: int | None, campeonato: str | None) -> tuple[str, list]:
    condicoes, parametros = [], []
    if ano:
        condicoes.append("substr(j.data_jogo, 1, 4) = ?")
        parametros.append(str(ano))
    if campeonato:
        condicoes.append("j.campeonato = ?")
        parametros.append(campeonato)
    return (" AND " + " AND ".join(condicoes)) if condicoes else "", parametros


def _jogos_do_participante(
    conexao: sqlite3.Connection,
    participante_id: int,
    ano: int | None,
    campeonato: str | None,
    mando: str | None = None,
):
    """`mando`: None (ambos), 'casa' ou 'fora'."""
    filtro, parametros = _clausula_filtro(ano, campeonato)
    if mando == "casa":
        filtro += " AND j.casa_id = ?"
        parametros = parametros + [participante_id]
    elif mando == "fora":
        filtro += " AND j.fora_id = ?"
        parametros = parametros + [participante_id]
    query = (
        "SELECT j.gols_casa, j.gols_fora, j.resultado, (j.casa_id = ?) AS jogou_em_casa "
        "FROM jogos j WHERE (j.casa_id = ? OR j.fora_id = ?) AND j.resultado IS NOT NULL" + filtro
    )
    return conexao.execute(query, [participante_id, participante_id, participante_id] + parametros).fetchall()


def aproveitamento_casa_fora(conexao, participante_id: int, ano: int | None = None, campeonato: str | None = None) -> dict:
    linhas = _jogos_do_participante(conexao, participante_id, ano, campeonato)
    casa = [linha for linha in linhas if linha["jogou_em_casa"]]
    fora = [linha for linha in linhas if not linha["jogou_em_casa"]]

    def _pct_vitorias(lista, coluna_vitoria):
        return 100 * sum(1 for linha in lista if linha["resultado"] == coluna_vitoria) / len(lista) if lista else 0.0

    return {
        "casa": _pct_vitorias(casa, "1"),
        "fora": _pct_vitorias(fora, "2"),
        "jogos_casa": len(casa),
        "jogos_fora": len(fora),
    }


def contagem_por_resultado(
    conexao, participante_id: int, ano: int | None = None, campeonato: str | None = None, mando: str | None = None
) -> dict:
    linhas = _jogos_do_participante(conexao, participante_id, ano, campeonato, mando)
    vitorias = empates = derrotas = 0
    for linha in linhas:
        em_casa = bool(linha["jogou_em_casa"])
        venceu = (em_casa and linha["resultado"] == "1") or (not em_casa and linha["resultado"] == "2")
        if venceu:
            vitorias += 1
        elif linha["resultado"] == "X":
            empates += 1
        else:
            derrotas += 1
    total = len(linhas)
    return {
        "jogos": total,
        "vitorias": vitorias,
        "empates": empates,
        "derrotas": derrotas,
        "pct_vitorias": 100 * vitorias / total if total else 0.0,
        "pct_empates": 100 * empates / total if total else 0.0,
        "pct_derrotas": 100 * derrotas / total if total else 0.0,
    }


def kpis(
    conexao, participante_id: int, ano: int | None = None, campeonato: str | None = None, mando: str | None = None
) -> dict:
    linhas = _jogos_do_participante(conexao, participante_id, ano, campeonato, mando)
    gols_marcados = gols_sofridos = 0
    for linha in linhas:
        em_casa = bool(linha["jogou_em_casa"])
        gols_marcados += linha["gols_casa"] if em_casa else linha["gols_fora"]
        gols_sofridos += linha["gols_fora"] if em_casa else linha["gols_casa"]
    total = len(linhas)
    return {
        "jogos": total,
        "gols_marcados": gols_marcados,
        "gols_sofridos": gols_sofridos,
        "saldo": gols_marcados - gols_sofridos,
        "media_gols": gols_marcados / total if total else 0.0,
    }


def tendencia_por_ano(conexao, participante_id: int) -> list[dict]:
    linhas = conexao.execute(
        """
        SELECT substr(j.data_jogo, 1, 4) AS ano, j.gols_casa, j.gols_fora, j.resultado,
               (j.casa_id = ?) AS jogou_em_casa
        FROM jogos j
        WHERE (j.casa_id = ? OR j.fora_id = ?) AND j.resultado IS NOT NULL AND j.data_jogo IS NOT NULL
        ORDER BY ano
        """,
        (participante_id, participante_id, participante_id),
    ).fetchall()

    por_ano: dict[str, dict] = {}
    for linha in linhas:
        ano = linha["ano"]
        registro = por_ano.setdefault(ano, {"jogos": 0, "vitorias": 0})
        registro["jogos"] += 1
        em_casa = bool(linha["jogou_em_casa"])
        venceu = (em_casa and linha["resultado"] == "1") or (not em_casa and linha["resultado"] == "2")
        if venceu:
            registro["vitorias"] += 1

    return [
        {
            "ano": ano,
            "jogos": dados["jogos"],
            "pct_aproveitamento": 100 * dados["vitorias"] / dados["jogos"] if dados["jogos"] else 0.0,
        }
        for ano, dados in sorted(por_ano.items())
    ]


LIMIAR_DIFERENCA_CASA_FORA = 25.0
LIMIAR_SEM_VITORIA_JOGOS = 5


def gerar_insight(aproveitamento: dict, contagem: dict) -> str:
    """Frase gerada por regra simples, direto dos números já calculados --
    nunca opinião livre. Retorna a primeira regra que se aplicar."""
    diferenca = aproveitamento["casa"] - aproveitamento["fora"]
    if aproveitamento["jogos_casa"] >= 3 and aproveitamento["jogos_fora"] >= 3 and abs(diferenca) >= LIMIAR_DIFERENCA_CASA_FORA:
        lado = "em casa" if diferenca > 0 else "fora de casa"
        return f"Aproveitamento bem melhor {lado}: {aproveitamento['casa']:.0f}% de vitórias como mandante contra {aproveitamento['fora']:.0f}% como visitante."
    if contagem["jogos"] >= LIMIAR_SEM_VITORIA_JOGOS and contagem["vitorias"] == 0:
        return f"Nenhuma vitória nos últimos {contagem['jogos']} jogos considerados neste filtro."
    if contagem["jogos"] >= LIMIAR_SEM_VITORIA_JOGOS and contagem["pct_vitorias"] >= 60:
        return f"Fase consistente: {contagem['pct_vitorias']:.0f}% de vitórias nos {contagem['jogos']} jogos deste filtro."
    return "Sem padrão forte o suficiente para destacar neste filtro -- veja a tabela detalhada abaixo."


def jogos_da_loteca(conexao, participante_id: int) -> list[dict]:
    """Jogos apurados do participante na grade da Loteca, do mais antigo ao mais
    recente, no mesmo formato de `stats.competicao.jogos_do_time` (o campo
    `rodada` traz o número do concurso; `adversario_id` é o id do participante)."""
    linhas = conexao.execute(
        """
        SELECT concurso_numero, data_jogo, casa_id, fora_id, gols_casa, gols_fora, situacao
        FROM jogos
        WHERE (casa_id = ? OR fora_id = ?) AND gols_casa IS NOT NULL AND gols_fora IS NOT NULL
        ORDER BY data_jogo, concurso_numero, num_jogo
        """,
        (participante_id, participante_id),
    ).fetchall()
    jogos = []
    for linha in linhas:
        em_casa = linha["casa_id"] == participante_id
        pro = linha["gols_casa"] if em_casa else linha["gols_fora"]
        contra = linha["gols_fora"] if em_casa else linha["gols_casa"]
        resultado = "V" if pro > contra else "E" if pro == contra else "D"
        jogos.append(
            {
                "rodada": linha["concurso_numero"],
                "data": linha["data_jogo"],
                "mando": "casa" if em_casa else "fora",
                "adversario_id": linha["fora_id"] if em_casa else linha["casa_id"],
                "gols_pro": pro,
                "gols_contra": contra,
                "resultado": resultado,
                "pontos": {"V": 3, "E": 1, "D": 0}[resultado],
                "sorteio": linha["situacao"] == "sorteio",
            }
        )
    return jogos


def frases_da_loteca(jogos: list[dict], por_mando: dict, global_: dict) -> list[str]:
    """Leituras por regra para a ficha de quem só tem jogos da Loteca. `por_mando`
    vem de `stats.frequencia.frequencia_participante`; `global_`, de `frequencia_global`."""
    import config
    from stats.competicao import descrever_sequencia, sequencia_atual

    if not jogos:
        return []
    v = sum(1 for j in jogos if j["resultado"] == "V")
    e = sum(1 for j in jogos if j["resultado"] == "E")
    d = sum(1 for j in jogos if j["resultado"] == "D")
    gp = sum(j["gols_pro"] for j in jogos)
    gc = sum(j["gols_contra"] for j in jogos)
    frases = [f"Na grade da Loteca: {len(jogos)} jogos, {v}V {e}E {d}D, {gp} gols marcados e {gc} sofridos."]
    minimo = config.FICHA_AMOSTRA_PEQUENA
    if len(jogos) < minimo:
        frases.append(f"Amostra pequena (menos de {minimo} jogos): os números abaixo têm baixa confiança.")
    for chave, nome, coluna in (("mandante", "mandante", "1"), ("visitante", "visitante", "2")):
        dados = por_mando[chave]
        if dados["total"] >= 5 and global_.get(coluna):
            observado = 100.0 * dados[coluna] / dados["total"]
            referencia = 100.0 * global_[coluna]
            frases.append(
                f"Como {nome}, a vitória saiu em {observado:.0f}% dos {dados['total']} jogos, contra {referencia:.0f}% "
                "na média da Loteca."
            )
    sequencia = descrever_sequencia(sequencia_atual(jogos))
    if sequencia:
        frases.append(f"Sequência atual: {sequencia}.")
    return frases

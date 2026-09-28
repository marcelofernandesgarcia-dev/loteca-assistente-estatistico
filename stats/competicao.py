"""Desempenho de um time ao longo de uma competição, calculado a partir dos
jogos da temporada coletados da CBF (tabela `cbf_partidas`).

A CBF entrega só uma "foto" da classificação; a evolução rodada a rodada é
RECONSTRUÍDA aqui a partir dos placares e conferida contra essa foto
(`validar_contra_classificacao`). Regras de leitura:
- "após a rodada r" = todos os jogos já disputados cujo número de rodada é <= r
  (um jogo adiado conta na rodada a que pertence, mesmo se jogado depois);
- ordem da tabela: pontos, vitórias, saldo de gols, gols pró. Critérios
  seguintes (confronto direto, cartões) não são aplicados; empates nesses
  quatro critérios são desfeitos pelo código do time e podem divergir da CBF.
"""
from collections import defaultdict

import config

PONTOS_VITORIA = 3
PONTOS_EMPATE = 1


def carregar_partidas(conexao, serie: str, ano: int) -> list[dict]:
    """Jogos com placar da competição, ordenados por rodada e data."""
    linhas = conexao.execute(
        """
        SELECT id_jogo, rodada, data_jogo, mandante_id, visitante_id, gols_mandante, gols_visitante
        FROM cbf_partidas
        WHERE serie = ? AND ano = ? AND gols_mandante IS NOT NULL AND gols_visitante IS NOT NULL
          AND rodada IS NOT NULL
        ORDER BY rodada, data_jogo, id_jogo
        """,
        (serie, ano),
    ).fetchall()
    return [dict(linha) for linha in linhas]


def serie_do_time(conexao, cod_time: int) -> tuple[str, int] | None:
    """(serie, ano) mais recente em que o time tem jogos coletados."""
    linha = conexao.execute(
        """
        SELECT serie, ano FROM cbf_partidas
        WHERE mandante_id = ? OR visitante_id = ?
        ORDER BY ano DESC, serie LIMIT 1
        """,
        (cod_time, cod_time),
    ).fetchone()
    return (linha["serie"], linha["ano"]) if linha else None


def _linha_vazia(cod_time: int) -> dict:
    return {
        "cod_time": cod_time, "jogos": 0, "pontos": 0, "vitorias": 0, "empates": 0,
        "derrotas": 0, "gols_pro": 0, "gols_contra": 0,
    }


def _registrar(linha: dict, gols_pro: int, gols_contra: int) -> None:
    linha["jogos"] += 1
    linha["gols_pro"] += gols_pro
    linha["gols_contra"] += gols_contra
    if gols_pro > gols_contra:
        linha["vitorias"] += 1
        linha["pontos"] += PONTOS_VITORIA
    elif gols_pro == gols_contra:
        linha["empates"] += 1
        linha["pontos"] += PONTOS_EMPATE
    else:
        linha["derrotas"] += 1


def _ordenar(linhas: list[dict]) -> list[dict]:
    for linha in linhas:
        linha["saldo"] = linha["gols_pro"] - linha["gols_contra"]
        linha["aproveitamento"] = (
            100.0 * linha["pontos"] / (PONTOS_VITORIA * linha["jogos"]) if linha["jogos"] else 0.0
        )
    ordenadas = sorted(
        linhas,
        key=lambda x: (-x["pontos"], -x["vitorias"], -x["saldo"], -x["gols_pro"], x["cod_time"]),
    )
    for posicao, linha in enumerate(ordenadas, start=1):
        linha["posicao"] = posicao
    return ordenadas


def tabela_por_rodada(partidas: list[dict]) -> dict[int, list[dict]]:
    """{rodada: tabela acumulada até essa rodada (lista ordenada por posição)}.
    Todos os times da competição aparecem em todas as rodadas (com 0 jogos
    antes de estrear). Rodadas sem nenhum jogo coletado ficam de fora."""
    times = {p["mandante_id"] for p in partidas} | {p["visitante_id"] for p in partidas}
    acumulado = {t: _linha_vazia(t) for t in times}
    por_rodada = defaultdict(list)
    for partida in partidas:
        por_rodada[partida["rodada"]].append(partida)

    resultado = {}
    for rodada in sorted(por_rodada):
        for p in por_rodada[rodada]:
            _registrar(acumulado[p["mandante_id"]], p["gols_mandante"], p["gols_visitante"])
            _registrar(acumulado[p["visitante_id"]], p["gols_visitante"], p["gols_mandante"])
        resultado[rodada] = [dict(x) for x in _ordenar([dict(x) for x in acumulado.values()])]
    return resultado


def jogos_do_time(partidas: list[dict], cod_time: int) -> list[dict]:
    """Jogo a jogo do time, do primeiro ao último. `resultado` é V, E ou D."""
    jogos = []
    for p in partidas:
        if cod_time not in (p["mandante_id"], p["visitante_id"]):
            continue
        em_casa = p["mandante_id"] == cod_time
        pro = p["gols_mandante"] if em_casa else p["gols_visitante"]
        contra = p["gols_visitante"] if em_casa else p["gols_mandante"]
        resultado = "V" if pro > contra else "E" if pro == contra else "D"
        jogos.append(
            {
                "rodada": p["rodada"],
                "data": p["data_jogo"],
                "mando": "casa" if em_casa else "fora",
                "adversario_id": p["visitante_id"] if em_casa else p["mandante_id"],
                "gols_pro": pro,
                "gols_contra": contra,
                "resultado": resultado,
                "pontos": {"V": PONTOS_VITORIA, "E": PONTOS_EMPATE, "D": 0}[resultado],
            }
        )
    return jogos


def evolucao_do_time(tabelas: dict[int, list[dict]], cod_time: int) -> list[dict]:
    """Posição, pontos e aproveitamento do time após cada rodada em que já
    tinha ao menos um jogo, com a média de pontos da série na mesma rodada."""
    evolucao = []
    for rodada, tabela in tabelas.items():
        linha = next((x for x in tabela if x["cod_time"] == cod_time), None)
        if linha is None or linha["jogos"] == 0:
            continue
        com_jogo = [x for x in tabela if x["jogos"] > 0]
        evolucao.append(
            {
                "rodada": rodada,
                "posicao": linha["posicao"],
                "pontos": linha["pontos"],
                "jogos": linha["jogos"],
                "aproveitamento": linha["aproveitamento"],
                "saldo": linha["saldo"],
                "pontos_media_serie": sum(x["pontos"] for x in com_jogo) / len(com_jogo),
            }
        )
    return evolucao


def validar_contra_classificacao(tabela_reconstruida: list[dict], classificacao_cbf: list[dict]) -> dict:
    """Compara a tabela final reconstruída com a foto da CBF. Retorna os times
    cujos números (jogos, pontos, gols pró/contra) divergem e os que ficaram em
    posição diferente. Divergência de número = dado faltando ou erro; de posição
    isolada = provável critério de desempate não aplicado."""
    reconstruida = {x["cod_time"]: x for x in tabela_reconstruida}
    divergencias_numeros, divergencias_posicao = [], []
    for oficial in classificacao_cbf:
        propria = reconstruida.get(oficial["cod_time"])
        if propria is None:
            divergencias_numeros.append({"cod_time": oficial["cod_time"], "motivo": "time sem jogos na base"})
            continue
        for campo in ("jogos", "pontos", "gols_pro", "gols_contra"):
            if propria[campo] != oficial[campo]:
                divergencias_numeros.append(
                    {"cod_time": oficial["cod_time"], "campo": campo, "reconstruido": propria[campo], "cbf": oficial[campo]}
                )
        if oficial.get("posicao") is not None and propria["posicao"] != oficial["posicao"]:
            divergencias_posicao.append(
                {"cod_time": oficial["cod_time"], "reconstruida": propria["posicao"], "cbf": oficial["posicao"]}
            )
    return {
        "times_conferidos": len(classificacao_cbf),
        "divergencias_numeros": divergencias_numeros,
        "divergencias_posicao": divergencias_posicao,
        "confere": not divergencias_numeros,
    }


def validar_temporada(conexao, serie: str, ano: int) -> dict:
    """Reconstrói a tabela final da temporada e confere com a última foto de
    classificação da CBF gravada no banco."""
    partidas = carregar_partidas(conexao, serie, ano)
    if not partidas:
        return {"times_conferidos": 0, "divergencias_numeros": [], "divergencias_posicao": [], "confere": False,
                "motivo": "sem jogos coletados"}
    tabelas = tabela_por_rodada(partidas)
    oficial = [
        dict(linha)
        for linha in conexao.execute(
            """
            SELECT cod_time, posicao, jogos, pontos, gols_pro, gols_contra FROM cbf_classificacao
            WHERE serie = ? AND ano = ? AND rodada = (SELECT MAX(rodada) FROM cbf_classificacao WHERE serie = ? AND ano = ?)
            """,
            (serie, ano, serie, ano),
        )
    ]
    return validar_contra_classificacao(tabelas[max(tabelas)], oficial)


def sequencia_atual(jogos: list[dict]) -> dict:
    """Quantos jogos seguidos, contando do último para trás, o time está
    vencendo, sem perder, sem vencer e perdendo."""
    resultados = [j["resultado"] for j in jogos]

    def contar(aceitos: str) -> int:
        n = 0
        for resultado in reversed(resultados):
            if resultado not in aceitos:
                break
            n += 1
        return n

    return {"vitorias": contar("V"), "sem_perder": contar("VE"), "sem_vencer": contar("ED"), "derrotas": contar("D")}


def descrever_sequencia(sequencia: dict, minimo: int | None = None) -> str | None:
    minimo = minimo if minimo is not None else config.COMPETICAO_SEQUENCIA_MINIMA
    if sequencia["vitorias"] >= minimo:
        return f"{sequencia['vitorias']} vitórias seguidas"
    if sequencia["derrotas"] >= minimo:
        return f"{sequencia['derrotas']} derrotas seguidas"
    if sequencia["sem_perder"] >= minimo:
        return f"{sequencia['sem_perder']} jogos sem perder"
    if sequencia["sem_vencer"] >= minimo:
        return f"{sequencia['sem_vencer']} jogos sem vencer"
    return None


def aproveitamento_movel(jogos: list[dict], janela: int | None = None) -> list[dict]:
    """Aproveitamento (%) dos últimos `janela` jogos, a cada jogo a partir do
    momento em que há jogos suficientes para preencher a janela."""
    janela = janela or config.COMPETICAO_JANELA_MOVEL
    return [
        {
            "rodada": jogos[i - 1]["rodada"],
            "aproveitamento_movel": 100.0 * sum(j["pontos"] for j in jogos[i - janela:i]) / (PONTOS_VITORIA * janela),
        }
        for i in range(janela, len(jogos) + 1)
    ]


def variacao_de_posicao(evolucao: list[dict], rodadas: int | None = None) -> dict | None:
    """Posição de `rodadas` rodadas atrás x atual. `variacao` positiva = subiu."""
    rodadas = rodadas or config.COMPETICAO_JANELA_MOVEL
    if len(evolucao) <= rodadas:
        return None
    antes, agora = evolucao[-1 - rodadas]["posicao"], evolucao[-1]["posicao"]
    return {"de": antes, "para": agora, "variacao": antes - agora, "rodadas": rodadas}


def frases_visao_geral(evolucao: list[dict], jogos: list[dict]) -> list[str]:
    """Leituras automáticas por regra, cada uma com o número que a sustenta."""
    if not evolucao:
        return []
    ultimo = evolucao[-1]
    frases = [
        f"Ocupa a {ultimo['posicao']}ª posição após a rodada {ultimo['rodada']}: {ultimo['pontos']} pontos em "
        f"{ultimo['jogos']} jogos ({ultimo['aproveitamento']:.0f}% de aproveitamento)."
    ]
    diferenca_pontos = ultimo["pontos"] - ultimo["pontos_media_serie"]
    if abs(diferenca_pontos) >= 1:
        sentido = "a mais" if diferenca_pontos > 0 else "a menos"
        frases.append(f"Tem {abs(diferenca_pontos):.0f} pontos {sentido} que a média da série ({ultimo['pontos_media_serie']:.0f}).")
    variacao = variacao_de_posicao(evolucao)
    if variacao:
        if variacao["variacao"] > 0:
            frases.append(f"Subiu {variacao['variacao']} posições nas últimas {variacao['rodadas']} rodadas (do {variacao['de']}º para o {variacao['para']}º).")
        elif variacao["variacao"] < 0:
            frases.append(f"Caiu {-variacao['variacao']} posições nas últimas {variacao['rodadas']} rodadas (do {variacao['de']}º para o {variacao['para']}º).")
        else:
            frases.append(f"Manteve a {variacao['para']}ª posição nas últimas {variacao['rodadas']} rodadas.")
    movel = aproveitamento_movel(jogos)
    if movel:
        recente = movel[-1]["aproveitamento_movel"]
        gap = recente - ultimo["aproveitamento"]
        if abs(gap) >= config.COMPETICAO_DIFERENCA_RELEVANTE_PP:
            sentido = "acima" if gap > 0 else "abaixo"
            frases.append(
                f"Nos últimos {config.COMPETICAO_JANELA_MOVEL} jogos o aproveitamento é {recente:.0f}%, {sentido} dos "
                f"{ultimo['aproveitamento']:.0f}% da temporada."
            )
    sequencia = descrever_sequencia(sequencia_atual(jogos))
    if sequencia:
        frases.append(f"Sequência atual: {sequencia}.")
    return frases


def _resumo(jogos: list[dict]) -> dict:
    n = len(jogos)
    pontos = sum(j["pontos"] for j in jogos)
    return {
        "jogos": n,
        "vitorias": sum(1 for j in jogos if j["resultado"] == "V"),
        "empates": sum(1 for j in jogos if j["resultado"] == "E"),
        "derrotas": sum(1 for j in jogos if j["resultado"] == "D"),
        "pontos": pontos,
        "aproveitamento": 100.0 * pontos / (PONTOS_VITORIA * n) if n else None,
        "gols_pro_media": sum(j["gols_pro"] for j in jogos) / n if n else None,
        "gols_contra_media": sum(j["gols_contra"] for j in jogos) / n if n else None,
    }


def resumo_por_mando(jogos: list[dict]) -> dict:
    """Desempenho do time em casa e fora."""
    return {
        "casa": _resumo([j for j in jogos if j["mando"] == "casa"]),
        "fora": _resumo([j for j in jogos if j["mando"] == "fora"]),
    }


def medias_da_liga(partidas: list[dict]) -> dict:
    """Referências da série: gols por time por jogo e aproveitamento de quem
    joga em casa e de quem joga fora."""
    n = len(partidas)
    if n == 0:
        return {"jogos": 0, "gols_por_time_por_jogo": None, "aproveitamento_casa": None, "aproveitamento_fora": None}
    gols = sum(p["gols_mandante"] + p["gols_visitante"] for p in partidas)
    pontos_casa = sum(
        PONTOS_VITORIA if p["gols_mandante"] > p["gols_visitante"] else PONTOS_EMPATE if p["gols_mandante"] == p["gols_visitante"] else 0
        for p in partidas
    )
    pontos_fora = sum(
        PONTOS_VITORIA if p["gols_visitante"] > p["gols_mandante"] else PONTOS_EMPATE if p["gols_mandante"] == p["gols_visitante"] else 0
        for p in partidas
    )
    return {
        "jogos": n,
        "gols_por_time_por_jogo": gols / (2 * n),
        "aproveitamento_casa": 100.0 * pontos_casa / (PONTOS_VITORIA * n),
        "aproveitamento_fora": 100.0 * pontos_fora / (PONTOS_VITORIA * n),
    }


def _desvio(valores: list[int]) -> float | None:
    if len(valores) < 2:
        return None
    media = sum(valores) / len(valores)
    return (sum((v - media) ** 2 for v in valores) / (len(valores) - 1)) ** 0.5


def perfil_de_gols(jogos: list[dict]) -> dict:
    """Retrato dos gols do time na temporada: quanto marca e sofre, com que
    regularidade e os extremos."""
    n = len(jogos)
    if n == 0:
        return {"jogos": 0}
    pro = [j["gols_pro"] for j in jogos]
    contra = [j["gols_contra"] for j in jogos]
    vitorias = [j for j in jogos if j["resultado"] == "V"]
    derrotas = [j for j in jogos if j["resultado"] == "D"]

    def extremo(lista, sinal):
        if not lista:
            return None
        escolhido = max(lista, key=lambda j: (sinal * (j["gols_pro"] - j["gols_contra"]), j["gols_pro"]))
        return {k: escolhido[k] for k in ("rodada", "adversario_id", "gols_pro", "gols_contra", "mando")}

    return {
        "jogos": n,
        "gols_pro_media": sum(pro) / n,
        "gols_contra_media": sum(contra) / n,
        "desvio_gols_pro": _desvio(pro),
        "desvio_gols_contra": _desvio(contra),
        "jogos_marcando": sum(1 for g in pro if g > 0),
        "jogos_sem_sofrer_gol": sum(1 for g in contra if g == 0),
        "jogos_3_ou_mais_gols_marcados": sum(1 for g in pro if g >= 3),
        "jogos_3_ou_mais_gols_sofridos": sum(1 for g in contra if g >= 3),
        "maior_vitoria": extremo(vitorias, 1),
        "pior_derrota": extremo(derrotas, -1),
    }


def gols_com_media_movel(jogos: list[dict], janela: int | None = None) -> list[dict]:
    """Gols marcados e sofridos em cada jogo e a média dos últimos `janela`
    jogos (ausente até a janela encher)."""
    janela = janela or config.COMPETICAO_JANELA_MOVEL
    linhas = []
    for i, jogo in enumerate(jogos):
        completa = i + 1 >= janela
        trecho = jogos[i + 1 - janela:i + 1] if completa else []
        linhas.append(
            {
                "rodada": jogo["rodada"],
                "gols_pro": jogo["gols_pro"],
                "gols_contra": jogo["gols_contra"],
                "pro_movel": sum(j["gols_pro"] for j in trecho) / janela if completa else None,
                "contra_movel": sum(j["gols_contra"] for j in trecho) / janela if completa else None,
            }
        )
    return linhas


def _pontos(gols_pro: int, gols_contra: int) -> int:
    if gols_pro > gols_contra:
        return PONTOS_VITORIA
    return PONTOS_EMPATE if gols_pro == gols_contra else 0


def metricas_por_time(partidas: list[dict]) -> dict[int, dict]:
    """Métricas de cada time da série com ao menos um jogo. Aproveitamento em
    casa/fora fica None quando o time ainda não jogou nesse mando."""
    brutos = defaultdict(lambda: {"jogos": 0, "pontos": 0, "gp": 0, "gc": 0,
                                  "jogos_casa": 0, "pontos_casa": 0, "jogos_fora": 0, "pontos_fora": 0})
    for p in partidas:
        for cod, pro, contra, casa in (
            (p["mandante_id"], p["gols_mandante"], p["gols_visitante"], True),
            (p["visitante_id"], p["gols_visitante"], p["gols_mandante"], False),
        ):
            b = brutos[cod]
            pontos = _pontos(pro, contra)
            b["jogos"] += 1
            b["pontos"] += pontos
            b["gp"] += pro
            b["gc"] += contra
            b["jogos_casa" if casa else "jogos_fora"] += 1
            b["pontos_casa" if casa else "pontos_fora"] += pontos

    def aprov(pontos, jogos):
        return 100.0 * pontos / (PONTOS_VITORIA * jogos) if jogos else None

    return {
        cod: {
            "jogos": b["jogos"],
            "aproveitamento": aprov(b["pontos"], b["jogos"]),
            "ataque": b["gp"] / b["jogos"],
            "defesa": b["gc"] / b["jogos"],
            "saldo_por_jogo": (b["gp"] - b["gc"]) / b["jogos"],
            "aproveitamento_casa": aprov(b["pontos_casa"], b["jogos_casa"]),
            "aproveitamento_fora": aprov(b["pontos_fora"], b["jogos_fora"]),
        }
        for cod, b in brutos.items()
    }


def posicao_no_ranking(valores: dict[int, float | None], cod_time: int, menor_e_melhor: bool = False) -> dict | None:
    """Posição (1 = melhor) do time entre os que têm valor. Empates dividem a
    mesma posição. `percentil` vai de 0 (pior) a 100 (melhor)."""
    validos = {cod: v for cod, v in valores.items() if v is not None}
    if cod_time not in validos:
        return None
    meu = validos[cod_time]
    melhores = sum(1 for v in validos.values() if (v < meu if menor_e_melhor else v > meu))
    total = len(validos)
    return {
        "posicao": melhores + 1,
        "de": total,
        "percentil": 100.0 * (total - 1 - melhores) / (total - 1) if total > 1 else 100.0,
        "valor": meu,
        "media_da_serie": sum(validos.values()) / total,
    }


def comparar_com_liga(partidas: list[dict], cod_time: int, cartoes_por_jogo: dict[int, float] | None = None) -> dict:
    """Posição do time entre os da série em cada métrica. Em `defesa` e
    `cartoes_por_jogo`, menos é melhor."""
    metricas = metricas_por_time(partidas)
    resultado = {}
    for nome, menor in (("aproveitamento", False), ("ataque", False), ("defesa", True), ("saldo_por_jogo", False),
                        ("aproveitamento_casa", False), ("aproveitamento_fora", False)):
        ranking = posicao_no_ranking({c: m[nome] for c, m in metricas.items()}, cod_time, menor)
        if ranking:
            resultado[nome] = ranking
    if cartoes_por_jogo:
        ranking = posicao_no_ranking(cartoes_por_jogo, cod_time, True)
        if ranking:
            resultado["cartoes_por_jogo"] = ranking
    return resultado


def disciplina_da_liga(conexao, serie: str, ano: int) -> dict[int, float]:
    """Cartões (amarelos + vermelhos) por jogo de cada time, da estatística da CBF."""
    linhas = conexao.execute(
        """
        SELECT cod_time, jogos_disputados, cartoes_amarelos, cartoes_vermelhos FROM cbf_estatisticas_time
        WHERE serie = ? AND ano = ? AND jogos_disputados > 0
        """,
        (serie, ano),
    )
    return {
        linha["cod_time"]: ((linha["cartoes_amarelos"] or 0) + (linha["cartoes_vermelhos"] or 0)) / linha["jogos_disputados"]
        for linha in linhas
    }


def _forcas_sem(partidas: list[dict], excluido: int) -> dict[int, float]:
    """Aproveitamento de cada time, sem contar os jogos contra `excluido` (para
    a força do adversário não depender do resultado contra o próprio time)."""
    pontos, jogos = defaultdict(int), defaultdict(int)
    for p in partidas:
        if excluido in (p["mandante_id"], p["visitante_id"]):
            continue
        for cod, pro, contra in ((p["mandante_id"], p["gols_mandante"], p["gols_visitante"]),
                                 (p["visitante_id"], p["gols_visitante"], p["gols_mandante"])):
            pontos[cod] += _pontos(pro, contra)
            jogos[cod] += 1
    return {cod: 100.0 * pontos[cod] / (PONTOS_VITORIA * jogos[cod]) for cod in jogos}


def _forca_media_dos_adversarios(partidas: list[dict], cod_time: int) -> tuple[float, dict[int, float]] | None:
    forcas = _forcas_sem(partidas, cod_time)
    enfrentados = []
    for p in partidas:
        if cod_time == p["mandante_id"]:
            enfrentados.append(p["visitante_id"])
        elif cod_time == p["visitante_id"]:
            enfrentados.append(p["mandante_id"])
    enfrentados = [o for o in enfrentados if o in forcas]
    if not enfrentados:
        return None
    return sum(forcas[o] for o in enfrentados) / len(enfrentados), forcas


def forca_do_calendario(partidas: list[dict], cod_time: int) -> dict | None:
    """Resultados do time contra adversários fortes, médios e fracos (tercis do
    aproveitamento dos adversários, sem contar os jogos contra o próprio time) e
    a dificuldade média do calendário já enfrentado, comparada à dos outros
    times (posição 1 = calendário mais difícil)."""
    calculo = _forca_media_dos_adversarios(partidas, cod_time)
    if calculo is None:
        return None
    forca_media, forcas = calculo

    ordenados = sorted(forcas, key=lambda cod: (-forcas[cod], cod))
    k = len(ordenados) // 3
    grupo_de = {cod: "fortes" for cod in ordenados[:k]}
    grupo_de.update({cod: "fracos" for cod in ordenados[len(ordenados) - k:]} if k else {})
    for cod in ordenados:
        grupo_de.setdefault(cod, "medios")

    grupos = {nome: {"jogos": 0, "vitorias": 0, "empates": 0, "derrotas": 0, "pontos": 0} for nome in ("fortes", "medios", "fracos")}
    for jogo in jogos_do_time(partidas, cod_time):
        grupo = grupos.get(grupo_de.get(jogo["adversario_id"], ""))
        if grupo is None:
            continue
        grupo["jogos"] += 1
        grupo["pontos"] += jogo["pontos"]
        grupo[{"V": "vitorias", "E": "empates", "D": "derrotas"}[jogo["resultado"]]] += 1
    for grupo in grupos.values():
        grupo["aproveitamento"] = 100.0 * grupo["pontos"] / (PONTOS_VITORIA * grupo["jogos"]) if grupo["jogos"] else None

    todos = {}
    for cod in {p["mandante_id"] for p in partidas} | {p["visitante_id"] for p in partidas}:
        medio = _forca_media_dos_adversarios(partidas, cod)
        if medio:
            todos[cod] = medio[0]
    dificuldade = posicao_no_ranking(todos, cod_time)  # posicao 1 = adversários mais fortes
    return {
        "forca_media_adversarios": forca_media,
        "forca_media_da_serie": sum(todos.values()) / len(todos) if todos else None,
        "posicao_dificuldade": dificuldade["posicao"] if dificuldade else None,
        "times_comparados": dificuldade["de"] if dificuldade else None,
        "grupos": grupos,
    }

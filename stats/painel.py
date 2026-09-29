"""Painel comparativo de times e seleções (Fase Q5; plano v2 aprovado em
29/09/2026 -- docs/plano-dashboard-q5.md).

Dois universos que nunca se misturam num número só:
- Temporada da CBF (Séries A e B): campeonato inteiro, rodada a rodada.
- Histórico na Loteca: só os jogos que caíram na grade (clubes e seleções).

Aproveitamento aqui é SEMPRE por pontos (vitória 3, empate 1), a mesma conta
da CBF -- diferente de `stats.desempenho.tendencia_por_ano`, que mede % de
vitórias (a Ficha do time rotula isso corretamente).

A projeção "se o desempenho persistir" (pedido do usuário) é um cenário, não
previsão: supõe que o time mantém o ritmo (da temporada ou dos últimos jogos)
e não considera os adversários que faltam (o calendário futuro não é
coletado), lesões, suspensões, troca de técnico ou outras competições. O
tamanho da temporada vem de `config.TEMPORADA_JOGOS_POR_TIME` (lido no
regulamento); sem cadastro, não há projeção.
"""
import config
from stats import competicao
from stats.contexto import zona_da_posicao

PONTOS_VITORIA = competicao.PONTOS_VITORIA
PONTOS_EMPATE = competicao.PONTOS_EMPATE


# ---------------------------------------------------------------------------
# Temporada (CBF)
# ---------------------------------------------------------------------------

def pontos_por_jogo_recentes(jogos: list[dict], janela: int | None = None) -> float | None:
    """Média de pontos por jogo nos últimos `janela` jogos (None se o time
    ainda não tem jogos suficientes para encher a janela)."""
    janela = janela or config.COMPETICAO_JANELA_MOVEL
    if len(jogos) < janela:
        return None
    return sum(j["pontos"] for j in jogos[-janela:]) / janela


def _ordenar_projecao(linhas: list[dict], chave: str) -> dict[int, int]:
    """Posição projetada: mais pontos projetados primeiro; empate desfeito
    pelos critérios atuais já usados em competicao.py (pontos, vitórias,
    saldo, gols pró) e, por fim, pelo código do time."""
    ordem = sorted(
        linhas,
        key=lambda x: (-x[chave], -x["pontos"], -x["vitorias"], -x["saldo"], -x["gols_pro"], x["cod_time"]),
    )
    return {linha["cod_time"]: posicao for posicao, linha in enumerate(ordem, start=1)}


def projetar_temporada(tabela_atual: list[dict], jogos_por_time: dict[int, list[dict]], serie: str, ano: int) -> dict | None:
    """Dois cenários por time até o fim da temporada: ritmo da temporada e
    ritmo recente (últimos `COMPETICAO_JANELA_MOVEL` jogos). `tabela_atual`:
    última tabela de `competicao.tabela_por_rodada`. None se a série/ano não
    tem o número de jogos cadastrado -- o módulo nunca supõe o tamanho."""
    total = config.TEMPORADA_JOGOS_POR_TIME.get((serie, ano))
    if not total:
        return None
    linhas = []
    for linha in tabela_atual:
        jogos = linha["jogos"]
        restantes = max(total - jogos, 0)
        ritmo_temporada = linha["pontos"] / jogos if jogos else 0.0
        ritmo_recente = pontos_por_jogo_recentes(jogos_por_time.get(linha["cod_time"], []))
        pontos_temporada = linha["pontos"] + restantes * ritmo_temporada
        pontos_recente = linha["pontos"] + restantes * ritmo_recente if ritmo_recente is not None else None
        linhas.append(
            {
                **{k: linha[k] for k in ("cod_time", "pontos", "vitorias", "saldo", "gols_pro")},
                "jogos": jogos,
                "restantes": restantes,
                "pontos_proj_temporada": pontos_temporada,
                "pontos_proj_recente": pontos_recente,
                # Para ordenar o cenário recente, quem ainda não tem 5 jogos entra pelo ritmo da temporada.
                "_ordem_recente": pontos_recente if pontos_recente is not None else pontos_temporada,
            }
        )
    pos_temporada = _ordenar_projecao(linhas, "pontos_proj_temporada")
    pos_recente = _ordenar_projecao(linhas, "_ordem_recente")
    resultado = {}
    for linha in linhas:
        cod = linha["cod_time"]
        linha.pop("_ordem_recente")
        resultado[cod] = {
            **linha,
            "total_jogos": total,
            "posicao_proj_temporada": pos_temporada[cod],
            "posicao_proj_recente": pos_recente[cod] if linha["pontos_proj_recente"] is not None else None,
            "zona_proj_temporada": zona_da_posicao(serie, ano, pos_temporada[cod]),
            "zona_proj_recente": (
                zona_da_posicao(serie, ano, pos_recente[cod]) if linha["pontos_proj_recente"] is not None else None
            ),
        }
    return resultado


def erro_da_projecao(partidas: list[dict], rodada_teste: int | None = None) -> dict | None:
    """Quanto a projeção por ritmo teria errado nesta mesma temporada: projeta
    da `rodada_teste` até a rodada mais recente e compara com os pontos reais
    de agora. Erro médio absoluto, em pontos por time, nos dois cenários.
    None se ainda não há rodadas depois da de teste."""
    rodada_teste = rodada_teste or config.PAINEL_RODADA_TESTE_PROJECAO
    tabelas = competicao.tabela_por_rodada(partidas)
    if not tabelas or rodada_teste not in tabelas or max(tabelas) <= rodada_teste:
        return None
    atual = max(tabelas)
    antes = {linha["cod_time"]: linha for linha in tabelas[rodada_teste]}
    agora = {linha["cod_time"]: linha for linha in tabelas[atual]}
    ate_teste = [p for p in partidas if p["rodada"] <= rodada_teste]
    erros_temporada, erros_recente = [], []
    for cod, linha_antes in antes.items():
        if not linha_antes["jogos"] or cod not in agora:
            continue
        jogos_a_mais = agora[cod]["jogos"] - linha_antes["jogos"]
        real = agora[cod]["pontos"]
        projetado = linha_antes["pontos"] + jogos_a_mais * linha_antes["pontos"] / linha_antes["jogos"]
        erros_temporada.append(abs(projetado - real))
        recente = pontos_por_jogo_recentes(competicao.jogos_do_time(ate_teste, cod))
        if recente is not None:
            erros_recente.append(abs(linha_antes["pontos"] + jogos_a_mais * recente - real))
    if not erros_temporada:
        return None
    return {
        "rodada_teste": rodada_teste,
        "rodada_atual": atual,
        "times": len(erros_temporada),
        "erro_medio_temporada": sum(erros_temporada) / len(erros_temporada),
        "erro_medio_recente": sum(erros_recente) / len(erros_recente) if erros_recente else None,
    }


def reta_de_tendencia(pontos: list[tuple[float, float]], pesos: list[float] | None = None) -> tuple[float, float] | None:
    """Mínimos quadrados (ponderados, se houver `pesos`): devolve (a, b) de
    y = a + b*x. None se não há ao menos 2 valores distintos de x."""
    if len({x for x, _ in pontos}) < 2:
        return None
    pesos = pesos or [1.0] * len(pontos)
    soma_p = sum(pesos)
    media_x = sum(p * x for p, (x, _) in zip(pesos, pontos)) / soma_p
    media_y = sum(p * y for p, (_, y) in zip(pesos, pontos)) / soma_p
    sxx = sum(p * (x - media_x) ** 2 for p, (x, _) in zip(pesos, pontos))
    sxy = sum(p * (x - media_x) * (y - media_y) for p, (x, y) in zip(pesos, pontos))
    b = sxy / sxx
    return media_y - b * media_x, b


def _limitar(valor: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    return max(minimo, min(maximo, valor))


def tendencia_do_aproveitamento(movel: list[dict], ate_rodada: int | None) -> list[dict] | None:
    """Reta sobre o aproveitamento dos últimos jogos (saída de
    `competicao.aproveitamento_movel`), do primeiro ponto até `ate_rodada`
    (fim da temporada), sempre entre 0% e 100%."""
    coeficientes = reta_de_tendencia([(m["rodada"], m["aproveitamento_movel"]) for m in movel])
    if coeficientes is None or ate_rodada is None:
        return None
    a, b = coeficientes
    inicio = movel[0]["rodada"]
    return [{"rodada": r, "valor": _limitar(a + b * r)} for r in (inicio, max(ate_rodada, movel[-1]["rodada"]))]


def participantes_do_concurso(conexao, numero: int) -> list[dict]:
    """Os jogos do concurso, com os dois participantes e o código da CBF de
    cada um (None quando não há pareamento, como as seleções)."""
    linhas = conexao.execute(
        """
        SELECT j.num_jogo, pc.id AS casa_id, pc.nome AS casa, pc.tipo AS casa_tipo, mc.cod_time AS casa_cod,
               pf.id AS fora_id, pf.nome AS fora, pf.tipo AS fora_tipo, mf.cod_time AS fora_cod
        FROM jogos j
        JOIN participantes pc ON pc.id = j.casa_id
        JOIN participantes pf ON pf.id = j.fora_id
        LEFT JOIN mapa_cbf_participante mc ON mc.participante_id = pc.id
        LEFT JOIN mapa_cbf_participante mf ON mf.participante_id = pf.id
        WHERE j.concurso_numero = ?
        ORDER BY j.num_jogo
        """,
        (numero,),
    ).fetchall()
    return [dict(linha) for linha in linhas]


def temporadas_disponiveis(conexao) -> list[tuple[str, int]]:
    return [
        (linha["serie"], linha["ano"])
        for linha in conexao.execute(
            "SELECT DISTINCT serie, ano FROM cbf_partidas WHERE gols_mandante IS NOT NULL ORDER BY ano DESC, serie"
        )
    ]


def classificacao_oficial(conexao, serie: str, ano: int) -> dict[int, dict]:
    """Última foto da classificação oficial da CBF, por código do time."""
    linhas = conexao.execute(
        """
        SELECT c.* FROM cbf_classificacao c
        WHERE c.serie = ? AND c.ano = ?
          AND c.rodada = (SELECT MAX(rodada) FROM cbf_classificacao WHERE serie = ? AND ano = ?)
        """,
        (serie, ano, serie, ano),
    ).fetchall()
    return {linha["cod_time"]: dict(linha) for linha in linhas}


def dados_da_temporada(conexao, serie: str, ano: int) -> dict | None:
    """Tudo o que a aba de temporada precisa, calculado uma vez por série."""
    partidas = competicao.carregar_partidas(conexao, serie, ano)
    if not partidas:
        return None
    tabelas = competicao.tabela_por_rodada(partidas)
    times = sorted({p["mandante_id"] for p in partidas} | {p["visitante_id"] for p in partidas})
    jogos_por_time = {cod: competicao.jogos_do_time(partidas, cod) for cod in times}
    projecao = projetar_temporada(tabelas[max(tabelas)], jogos_por_time, serie, ano)
    total = config.TEMPORADA_JOGOS_POR_TIME.get((serie, ano))
    return {
        "serie": serie,
        "ano": ano,
        "partidas": partidas,
        "tabelas": tabelas,
        "times": times,
        "jogos_por_time": jogos_por_time,
        "evolucao": {cod: competicao.evolucao_do_time(tabelas, cod) for cod in times},
        "movel": {cod: competicao.aproveitamento_movel(jogos_por_time[cod]) for cod in times},
        "metricas": competicao.metricas_por_time(partidas),
        "oficial": classificacao_oficial(conexao, serie, ano),
        "cartoes": competicao.disciplina_da_liga(conexao, serie, ano),
        "projecao": projecao,
        "erro_projecao": erro_da_projecao(partidas) if projecao else None,
        "total_jogos": total,
        "rodada_final": total if total else None,  # pontos corridos: rodadas = jogos por time
    }


def tabela_comparativa(dados: dict, cods: list[int]) -> list[dict]:
    """Uma linha por time pedido, com números crus (a página formata).
    Posição e pontos vêm da classificação OFICIAL quando existe; o resto,
    dos jogos coletados."""
    ultima = {linha["cod_time"]: linha for linha in dados["tabelas"][max(dados["tabelas"])]}
    linhas = []
    for cod in cods:
        if cod not in ultima:
            continue
        oficial = dados["oficial"].get(cod) or {}
        reconstruida = ultima[cod]
        metricas = dados["metricas"].get(cod) or {}
        projecao = (dados["projecao"] or {}).get(cod)
        posicao = oficial.get("posicao") or reconstruida["posicao"]
        linhas.append(
            {
                "cod_time": cod,
                "posicao": posicao,
                "zona": zona_da_posicao(dados["serie"], dados["ano"], posicao),
                "pontos": oficial.get("pontos", reconstruida["pontos"]),
                "jogos": oficial.get("jogos", reconstruida["jogos"]),
                "vitorias": oficial.get("vitorias", reconstruida["vitorias"]),
                "empates": oficial.get("empates", reconstruida["empates"]),
                "derrotas": oficial.get("derrotas", reconstruida["derrotas"]),
                "gols_pro": oficial.get("gols_pro", reconstruida["gols_pro"]),
                "gols_contra": oficial.get("gols_contra", reconstruida["gols_contra"]),
                "saldo": oficial.get("saldo", reconstruida["saldo"]),
                "aproveitamento": reconstruida["aproveitamento"],
                "aproveitamento_casa": metricas.get("aproveitamento_casa"),
                "aproveitamento_fora": metricas.get("aproveitamento_fora"),
                "sequencia": competicao.descrever_sequencia(competicao.sequencia_atual(dados["jogos_por_time"][cod])),
                "cartoes_por_jogo": dados["cartoes"].get(cod),
                "projecao": projecao,
            }
        )
    return sorted(linhas, key=lambda x: x["posicao"])


def frases_da_temporada(dados: dict, cods: list[int], nomes: dict[int, str]) -> list[str]:
    """Leituras por regra entre os times pedidos, cada uma com o número que a sustenta."""
    frases = []
    variacoes = []
    for cod in cods:
        variacao = competicao.variacao_de_posicao(dados["evolucao"].get(cod, []))
        if variacao:
            variacoes.append((cod, variacao))
    if variacoes:
        sobe = max(variacoes, key=lambda v: v[1]["variacao"])
        desce = min(variacoes, key=lambda v: v[1]["variacao"])
        if sobe[1]["variacao"] > 0:
            v = sobe[1]
            frases.append(f"Maior subida nas últimas {v['rodadas']} rodadas: {nomes.get(sobe[0], sobe[0])}, do {v['de']}º para o {v['para']}º.")
        if desce[1]["variacao"] < 0:
            v = desce[1]
            frases.append(f"Maior queda nas últimas {v['rodadas']} rodadas: {nomes.get(desce[0], desce[0])}, do {v['de']}º para o {v['para']}º.")
    if dados["erro_projecao"]:
        e = dados["erro_projecao"]
        texto = (
            f"Teste da projeção nesta temporada: projetando da rodada {e['rodada_teste']} até a {e['rodada_atual']}, "
            f"o ritmo da temporada errou em média {_decimal(e['erro_medio_temporada'])} pontos por time"
        )
        if e["erro_medio_recente"] is not None:
            texto += f", e o ritmo recente, {_decimal(e['erro_medio_recente'])}"
        frases.append(texto + ".")
    return frases


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def frase_de_projecao(nome: str, projecao: dict | None, nomes_zona: dict[str, str]) -> str | None:
    if not projecao or not projecao["restantes"]:
        return None
    temporada = (
        f"no ritmo da temporada, terminaria com {projecao['pontos_proj_temporada']:.0f} pontos, "
        f"em {projecao['posicao_proj_temporada']}º"
    )
    if projecao["zona_proj_temporada"]:
        temporada += f" ({nomes_zona[projecao['zona_proj_temporada']]})"
    texto = f"{nome}: {temporada}"
    if projecao["pontos_proj_recente"] is not None:
        recente = (
            f"no ritmo dos últimos {config.COMPETICAO_JANELA_MOVEL} jogos, {projecao['pontos_proj_recente']:.0f} pontos, "
            f"em {projecao['posicao_proj_recente']}º"
        )
        if projecao["zona_proj_recente"]:
            recente += f" ({nomes_zona[projecao['zona_proj_recente']]})"
        texto += f"; {recente}"
    return texto + f". Faltam {projecao['restantes']} jogos."


# ---------------------------------------------------------------------------
# Histórico na Loteca
# ---------------------------------------------------------------------------

def jogos_loteca(conexao, participante_id: int) -> list[dict]:
    """Jogos apurados do participante na Loteca, em ordem de concurso.
    Resultado decidido por sorteio fica de fora (não é desempenho em campo)."""
    linhas = conexao.execute(
        """
        SELECT j.concurso_numero, j.data_jogo, j.casa_id, j.gols_casa, j.gols_fora
        FROM jogos j
        WHERE (j.casa_id = ? OR j.fora_id = ?) AND j.resultado IS NOT NULL
          AND j.gols_casa IS NOT NULL AND j.gols_fora IS NOT NULL AND j.situacao != 'sorteio'
        ORDER BY j.concurso_numero, j.num_jogo
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
                "ano": int(linha["data_jogo"][:4]) if linha["data_jogo"] else None,
                "mando": "casa" if em_casa else "fora",
                "gols_pro": pro,
                "gols_contra": contra,
                "resultado": resultado,
                "pontos": {"V": PONTOS_VITORIA, "E": PONTOS_EMPATE, "D": 0}[resultado],
            }
        )
    return jogos


def _aproveitamento(jogos: list[dict]) -> float | None:
    return 100.0 * sum(j["pontos"] for j in jogos) / (PONTOS_VITORIA * len(jogos)) if jogos else None


def resumo_loteca(jogos: list[dict], ano_inicial: int | None = None, ano_final: int | None = None) -> dict:
    """Resumo no período. Sem período, entram todos os jogos (inclusive os
    sem data); com período, os sem data ficam de fora e são contados."""
    if ano_inicial is None and ano_final is None:
        selecionados, fora_do_periodo_sem_data = list(jogos), 0
    else:
        selecionados = [
            j for j in jogos
            if j["ano"] is not None
            and (ano_inicial is None or j["ano"] >= ano_inicial)
            and (ano_final is None or j["ano"] <= ano_final)
        ]
        fora_do_periodo_sem_data = sum(1 for j in jogos if j["ano"] is None)
    n = len(selecionados)
    contagem = {r: sum(1 for j in selecionados if j["resultado"] == r) for r in "VED"}
    recentes = selecionados[-config.PAINEL_JANELA_RECENTE_LOTECA:]
    return {
        "jogos": n,
        "vitorias": contagem["V"],
        "empates": contagem["E"],
        "derrotas": contagem["D"],
        "pct_vitorias": 100.0 * contagem["V"] / n if n else None,
        "pct_empates": 100.0 * contagem["E"] / n if n else None,
        "pct_derrotas": 100.0 * contagem["D"] / n if n else None,
        "aproveitamento": _aproveitamento(selecionados),
        "gols_pro_por_jogo": sum(j["gols_pro"] for j in selecionados) / n if n else None,
        "gols_contra_por_jogo": sum(j["gols_contra"] for j in selecionados) / n if n else None,
        "aproveitamento_casa": _aproveitamento([j for j in selecionados if j["mando"] == "casa"]),
        "aproveitamento_fora": _aproveitamento([j for j in selecionados if j["mando"] == "fora"]),
        "aproveitamento_recente": _aproveitamento(recentes) if n >= config.PAINEL_JANELA_RECENTE_LOTECA else None,
        "amostra_pequena": n < config.PAINEL_MIN_JOGOS_LOTECA,
        "sem_data_excluidos": fora_do_periodo_sem_data,
    }


def tendencia_anual_loteca(jogos: list[dict]) -> dict:
    """Aproveitamento por ano. Ano com menos de `PAINEL_MIN_JOGOS_ANO` jogos
    é marcado como sinal fraco. Jogos sem data não entram (e são contados)."""
    por_ano: dict[int, list[dict]] = {}
    for jogo in jogos:
        if jogo["ano"] is not None:
            por_ano.setdefault(jogo["ano"], []).append(jogo)
    anos = [
        {
            "ano": ano,
            "jogos": len(lista),
            "aproveitamento": _aproveitamento(lista),
            "fraco": len(lista) < config.PAINEL_MIN_JOGOS_ANO,
        }
        for ano, lista in sorted(por_ano.items())
    ]
    return {"anos": anos, "sem_data": sum(1 for j in jogos if j["ano"] is None)}


def reta_anual(anos: list[dict]) -> list[dict] | None:
    """Reta de tendência do aproveitamento anual, ponderada pelo número de
    jogos, só com anos de base mínima, estendida até o ano seguinte ao
    último. None sem pelo menos `PAINEL_ANOS_MINIMOS_RETA` anos com base."""
    validos = [a for a in anos if not a["fraco"]]
    if len(validos) < config.PAINEL_ANOS_MINIMOS_RETA:
        return None
    coeficientes = reta_de_tendencia([(a["ano"], a["aproveitamento"]) for a in validos], [a["jogos"] for a in validos])
    if coeficientes is None:
        return None
    a, b = coeficientes
    return [{"ano": x, "valor": _limitar(a + b * x)} for x in (validos[0]["ano"], validos[-1]["ano"] + 1)]


def participantes_com_minimo(conexao, minimo: int, tipo: str | None = None) -> list[dict]:
    """Participantes com pelo menos `minimo` jogos apurados na Loteca (fora os
    decididos por sorteio), do que tem mais jogos para o que tem menos."""
    filtro_tipo = "AND p.tipo = ?" if tipo else ""
    parametros = [tipo] if tipo else []
    linhas = conexao.execute(
        f"""
        SELECT p.id, p.nome, p.tipo, p.pais_ou_uf, COUNT(*) AS jogos
        FROM participantes p
        JOIN jogos j ON (j.casa_id = p.id OR j.fora_id = p.id)
        WHERE j.resultado IS NOT NULL AND j.gols_casa IS NOT NULL AND j.situacao != 'sorteio' {filtro_tipo}
        GROUP BY p.id
        HAVING COUNT(*) >= ?
        ORDER BY jogos DESC, p.nome
        """,
        parametros + [minimo],
    ).fetchall()
    return [dict(linha) for linha in linhas]


def frase_amostra_pequena(nomes: list[str]) -> str | None:
    """Uma frase só para todos os participantes com pouca amostra."""
    if not nomes:
        return None
    return (
        f"Amostra pequena (menos de {config.PAINEL_MIN_JOGOS_LOTECA} jogos na Loteca no período), leitura fraca: "
        + ", ".join(nomes) + "."
    )


def frases_da_loteca(nome: str, resumo: dict) -> list[str]:
    """Leituras por participante (a amostra pequena vai em `frase_amostra_pequena`)."""
    frases = []
    if resumo["jogos"] == 0:
        return [f"{nome}: sem jogos no período."]
    recente, geral = resumo["aproveitamento_recente"], resumo["aproveitamento"]
    if recente is not None and geral is not None and abs(recente - geral) >= config.COMPETICAO_DIFERENCA_RELEVANTE_PP:
        sentido = "acima" if recente > geral else "abaixo"
        frases.append(
            f"{nome}: nos últimos {config.PAINEL_JANELA_RECENTE_LOTECA} jogos na Loteca, aproveitamento de "
            f"{recente:.0f}%, {sentido} dos {geral:.0f}% do período."
        )
    return frases

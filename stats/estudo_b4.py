"""Item B4 do plano v2 (aprovado em 07/10/2026): onde colocar o ÚNICO duplo ou triplo da sugestão.

Material do usuário de 07/10/2026: dar prioridade aos jogos de baixa carga de dados. A regra da sugestão só
muda se o teste com os concursos passados mostrar ganho (regra do usuário). Três regras, todas com no máximo
um duplo ou um triplo e o mesmo corte de triplo da sugestão (config.SUGESTAO_LIMIAR_DUPLO):
- "atual": o jogo mais incerto (menor chance do favorito) -- stats.bilhete.montar_bilhete;
- "cobertura": o mais incerto entre os jogos de cobertura parcial ou baixa; sem nenhum, a regra atual;
- "mista": entre os 3 jogos mais incertos, o de cobertura parcial ou baixa mais incerto; sem nenhum, a atual.

Previsões e coberturas como o app teria na época, sem olhar o futuro: percentual de `stats.calibracao.
carregar_registros` (modelo histórico do B3, Elo nas seleções); cobertura "completa" quando os dois clubes
estavam na mesma série A ou B da CBF naquele ano, "selecoes" no Elo, "baixa" na frequência geral, e "parcial"
no resto. Só concursos de anos com temporada da CBF coletada (de 2019 em diante), com os 14 jogos.
Medida: acertos por concurso (os palpites simples são iguais nas três regras; muda só o jogo do múltiplo).
"""
import numpy as np

import config
from stats import backtest_competicao as b2
from stats import competicao
from stats.associacao import ajustar_benjamini_hochberg

REGRAS = ("atual", "cobertura", "mista")
DESCRICAO = {
    "atual": "Jogo mais incerto (regra atual)",
    "cobertura": "Mais incerto entre os de pouca cobertura",
    "mista": "Entre os 3 mais incertos, o de pouca cobertura",
}


def _cobertura(origem: str, completa: bool) -> str:
    if origem == "elo_selecoes":
        return "selecoes"
    if origem == "frequencia_global":
        return "baixa"
    return "completa" if completa else "parcial"


def escolher(jogos: list[dict], regra: str) -> int:
    """Índice do jogo que recebe o múltiplo. `jogos`: [{'p': {...}, 'cobertura': nivel}]."""
    incerteza = sorted(range(len(jogos)), key=lambda i: max(jogos[i]["p"].values()))
    pouca = [i for i in incerteza if jogos[i]["cobertura"] in ("parcial", "baixa")]
    if regra == "cobertura" and pouca:
        return pouca[0]
    if regra == "mista":
        entre_tres = [i for i in incerteza[:3] if i in pouca]
        if entre_tres:
            return entre_tres[0]
    return incerteza[0]


def acertos(jogos: list[dict], escolhido: int) -> int:
    """Acertos do bilhete: favorito em todos, e no escolhido duplo (2 mais prováveis) ou triplo."""
    total = 0
    for i, jogo in enumerate(jogos):
        ordem = sorted(jogo["p"], key=jogo["p"].get, reverse=True)
        if i == escolhido:
            quantidade = 3 if jogo["p"][ordem[0]] < config.SUGESTAO_LIMIAR_DUPLO else 2
            total += int(jogo["resultado"] in ordem[:quantidade])
        else:
            total += int(jogo["resultado"] == ordem[0])
    return total


def montar_concursos(conexao, registros: list[dict]) -> list[dict]:
    """Concursos (14 jogos) de anos com temporada da CBF, cada jogo com previsão, resultado e cobertura da época."""
    pareamento = dict(conexao.execute("SELECT participante_id, cod_time FROM mapa_cbf_participante").fetchall())
    serie_do_time = {
        (l["ano"], l["cod"]): l["serie"]
        for l in conexao.execute(
            f"SELECT DISTINCT ano, serie, mandante_id AS cod FROM cbf_partidas WHERE {competicao.so_pontos_corridos()} "
            f"UNION SELECT DISTINCT ano, serie, visitante_id FROM cbf_partidas WHERE {competicao.so_pontos_corridos()}"
        )
    }
    anos_cbf = {ano for ano, _ in serie_do_time}
    info = {l["id"]: l for l in conexao.execute("SELECT id, casa_id, fora_id, data_jogo FROM jogos")}
    por_concurso: dict[int, list[dict]] = {}
    for r in registros:
        jogo = info[r["id"]]
        ano = int(jogo["data_jogo"][:4]) if jogo["data_jogo"] and jogo["data_jogo"][:4].isdigit() else None
        casa, fora = pareamento.get(jogo["casa_id"]), pareamento.get(jogo["fora_id"])
        serie_casa = serie_do_time.get((ano, casa))
        completa = serie_casa is not None and serie_casa == serie_do_time.get((ano, fora))
        por_concurso.setdefault(r["concurso"], []).append(
            {"ano": ano, "p": r["p"], "resultado": r["resultado"], "cobertura": _cobertura(r["origem"], completa)}
        )
    return [
        {"numero": n, "ano": jogos[0]["ano"], "jogos": jogos}
        for n, jogos in sorted(por_concurso.items())
        if len(jogos) == 14 and jogos[0]["ano"] in anos_cbf
    ]


def estudar(concursos: list[dict]) -> dict | None:
    """Acertos médios por regra, quantas vezes cada regra escolheu outro jogo, e a comparação pareada com a
    regra atual (intervalo e valor p por reamostragem de concursos, q de Benjamini-Hochberg)."""
    if not concursos:
        return None
    resultado = {regra: np.array([acertos(c["jogos"], escolher(c["jogos"], regra)) for c in concursos]) for regra in REGRAS}
    diferentes = {regra: sum(1 for c in concursos if escolher(c["jogos"], regra) != escolher(c["jogos"], "atual"))
                  for regra in REGRAS}
    clusters = np.array([str(c["numero"]) for c in concursos])
    comparacoes = []
    for indice, regra in enumerate(("cobertura", "mista")):
        ganho = (resultado[regra] - resultado["atual"]).astype(float)
        comparacoes.append({"regra": regra, **b2._bootstrap_por_cluster(
            ganho, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + 400 + indice)})
    for c, q in zip(comparacoes, ajustar_benjamini_hochberg([c["p"] for c in comparacoes])):
        c["q"] = q
        c["conclusao"] = ("melhor" if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA
                          else "pior" if c["ic_superior"] < 0 else "sem diferença perceptível")
    return {
        "concursos": len(concursos),
        "media": {regra: float(v.mean()) for regra, v in resultado.items()},
        "outro_jogo": diferentes,
        "comparacoes": comparacoes,
    }

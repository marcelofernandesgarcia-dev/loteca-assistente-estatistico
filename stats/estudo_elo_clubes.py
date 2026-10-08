"""Estudo formal do Elo de clubes (sugestão S2, aprovada em 07/10/2026). Só mede.

Critério fixado antes do resultado (regra do usuário): o modelo novo só substitui o anterior se a perda
logarítmica fora da amostra for menor com q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA. Três perguntas, sobre os
jogos de 2020 em diante, todos previstos andando no tempo:
1. "demais" (clubes fora do modelo da temporada da CBF): Elo de clubes contra o que o app usa hoje (Poisson
   histórico com a calibração refeita só com o passado);
2. o Elo precisa de calibração? (a mesma correção do app, ajustada só com o passado, aplicada ao Elo);
3. Séries A e B: a média entre o modelo da temporada da CBF e o Elo contra a temporada sozinha.
"""
import numpy as np

import config
from stats import backtest, backtest_competicao as b2, backtest_loteca as bl, calibracao as cal, elo_clubes
from stats.associacao import ajustar_benjamini_hochberg

INDICE = {"1": 0, "X": 1, "2": 2}


def _matriz(lista: list[dict]) -> np.ndarray:
    return np.array([[p[c] / 100.0 for c in ("1", "X", "2")] for p in lista])


def _perda(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(P[np.arange(len(y)), y], 1e-9, 1.0))


def _rps(P: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Ranked Probability Score para 1/X/2 (ordem 1 < X < 2); menor é melhor."""
    O = np.eye(3)[y]
    return 0.5 * ((P[:, 0] - O[:, 0]) ** 2 + (P[:, 0] + P[:, 1] - O[:, 0] - O[:, 1]) ** 2)


def _metricas(P: np.ndarray, y: np.ndarray) -> dict:
    return {"n": len(y), "perda_log": float(_perda(P, y).mean()), "rps": float(_rps(P, y).mean()),
            "acerto": float(100 * np.mean(P.argmax(axis=1) == y))}


def _calibrar_elo(registros_elo: list[dict]) -> np.ndarray:
    """Aplica ao Elo a correção do app (expoente e mistura), ajustada só com concursos anteriores."""
    Q, _ = cal.calibrar_andando_no_tempo(
        [{**r, "origem": "elo_clubes"} for r in registros_elo], cal.METODO_PRINCIPAL)
    return Q


def estudar(conexao) -> dict:
    jogos = backtest.carregar_jogos(conexao)
    elo = elo_clubes.prever_walk_forward(jogos, elo_clubes.clubes_do_banco(conexao))
    registros = cal.carregar_registros(conexao)
    Q, com_treino = cal.calibrar_andando_no_tempo(registros, cal.METODO_PRINCIPAL)
    jogos_cbf, _ = bl.montar_jogos(conexao, backtest.prever_walk_forward(jogos), bl.pesos_por_ano(b2.carregar_amostra(conexao)))
    cbf = {j["id"]: j for j in jogos_cbf}
    por_id = {j["id"]: j for j in jogos}

    # 1 e 2: "demais"
    demais = [(r, q if t else _matriz([r["p"]])[0])
              for r, q, t in zip(registros, Q, com_treino)
              if r["origem"] in ("poisson", "frequencia_global") and r["id"] not in cbf and r["id"] in elo]
    ids = [r["id"] for r, _ in demais]
    y = np.array([INDICE[por_id[i]["resultado"]] for i in ids])
    P_app = np.array([q for _, q in demais])
    P_freq = _matriz([r["f"] for r, _ in demais])
    P_elo = _matriz([elo[i]["p"] for i in ids])
    P_elo_cal = _calibrar_elo([{"id": i, "concurso": elo[i]["concurso"], "num_jogo": por_id[i]["num_jogo"],
                                "resultado": por_id[i]["resultado"], "p": elo[i]["p"], "f": r["f"]}
                               for (r, _), i in zip(demais, ids)])
    cl_demais = np.array([str(por_id[i]["concurso_numero"]) for i in ids])

    # 3: Séries A e B
    ab = [j for j in jogos_cbf if j["id"] in elo]
    y_ab = np.array([INDICE[j["resultado"]] for j in ab])
    P_ret = _matriz([j["previsoes"]["retrospecto"] for j in ab])
    P_media = (P_ret + _matriz([elo[j["id"]]["p"] for j in ab])) / 2
    cl_ab = np.array([str(j["concurso"]) for j in ab])

    comparacoes = []
    for indice, (nome, ganho, clusters) in enumerate((
        ("Elo de clubes contra o modelo atual, nos demais", _perda(P_app, y) - _perda(P_elo, y), cl_demais),
        ("Elo calibrado contra o Elo sem calibração, nos demais", _perda(P_elo, y) - _perda(P_elo_cal, y), cl_demais),
        ("Média temporada + Elo contra a temporada, nas Séries A e B", _perda(P_ret, y_ab) - _perda(P_media, y_ab), cl_ab),
    )):
        comparacoes.append({"comparacao": nome, **b2._bootstrap_por_cluster(
            ganho, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + 500 + indice)})
    for c, q in zip(comparacoes, ajustar_benjamini_hochberg([c["p"] for c in comparacoes])):
        c["q"] = q
        c["conclusao"] = ("melhor" if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA
                          else "pior" if c["ic_superior"] < 0 else "sem diferença perceptível")
    sem_base = np.array([r["origem"] == "frequencia_global" for r, _ in demais])
    return {
        "demais": {
            "frequencia": _metricas(P_freq, y), "modelo_atual": _metricas(P_app, y),
            "elo": _metricas(P_elo, y), "elo_calibrado": _metricas(P_elo_cal, y),
            "sem_base_modelo_atual": _metricas(P_app[sem_base], y[sem_base]),
            "sem_base_elo": _metricas(P_elo[sem_base], y[sem_base]),
        },
        "series_ab": {"temporada": _metricas(P_ret, y_ab), "media": _metricas(P_media, y_ab)},
        "comparacoes": comparacoes,
    }

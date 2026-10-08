"""Confiabilidade do app COMO ELE ESTÁ HOJE (sugestão S1, aprovada em 07/10/2026).

A página antiga media só o modelo histórico (Poisson da Loteca) e dava "pior que a referência", embora o app já
não use esse modelo na maior parte dos jogos. Aqui cada jogo apurado de config.CONFIABILIDADE_DESDE_ANO em
diante é previsto andando no tempo pela mesma regra de percentuais_do_jogo:
- clubes da mesma série A ou B: modelo da temporada da CBF (média com o Elo de clubes, se ligado);
- duas seleções: Elo das seleções (sem calibração, como no app);
- demais jogos entre clubes: Elo de clubes, se ligado;
- o resto: Poisson histórico com a calibração refeita só com o passado.
Mede perda logarítmica (critério de troca de modelo), RPS, Brier e acerto do favorito, por tipo de jogo e por ano,
contra a frequência simples, com intervalo por reamostragem de concursos. Só leitura do banco; leva cerca de 1 a 2
minutos no banco real, por isso o resultado é gravado em `medicoes_modelo` pela atualização diária.
"""
import datetime as dt
import json

import numpy as np

import config
from stats import backtest, backtest_competicao as b2, backtest_loteca as bl, calibracao as cal, elo_clubes

TIPOS = ("Séries A e B", "Seleções", "Demais clubes", "Outros jogos")
_IDX = {"1": 0, "X": 1, "2": 2}


def _vetor(p: dict) -> np.ndarray:
    return np.array([p[c] / 100.0 for c in ("1", "X", "2")])


def _metricas(P: np.ndarray, F: np.ndarray, y: np.ndarray, clusters: np.ndarray, semente: int) -> dict:
    linhas = np.arange(len(y))
    perda = -np.log(np.clip(P[linhas, y], 1e-9, 1.0))
    perda_f = -np.log(np.clip(F[linhas, y], 1e-9, 1.0))
    O = np.eye(3)[y]
    rps = 0.5 * ((P[:, 0] - O[:, 0]) ** 2 + (P[:, 0] + P[:, 1] - O[:, 0] - O[:, 1]) ** 2)
    rps_f = 0.5 * ((F[:, 0] - O[:, 0]) ** 2 + (F[:, 0] + F[:, 1] - O[:, 0] - O[:, 1]) ** 2)
    comparacao = b2._bootstrap_por_cluster(perda_f - perda, clusters, config.B2_REPETICOES_BOOTSTRAP, semente)
    return {
        "n": int(len(y)), "perda_log": float(perda.mean()), "perda_log_frequencia": float(perda_f.mean()),
        "rps": float(rps.mean()), "rps_frequencia": float(rps_f.mean()),
        "brier": float(((P - O) ** 2).sum(axis=1).mean()),
        "acerto": float(100 * np.mean(P.argmax(axis=1) == y)), "acerto_frequencia": float(100 * np.mean(F.argmax(axis=1) == y)),
        "ganho": comparacao["media"], "ic_inferior": comparacao["ic_inferior"], "ic_superior": comparacao["ic_superior"],
        "p": comparacao["p"],
    }


def _calibracao(P: np.ndarray, y: np.ndarray) -> list[dict]:
    pares = [({c: 100 * p[i] for i, c in enumerate(("1", "X", "2"))}, ("1", "X", "2")[r]) for p, r in zip(P, y)]
    return backtest.calibracao(pares)


def medir(conexao) -> dict | None:
    """Mede o app de hoje. None se não houver jogos no período."""
    jogos = backtest.carregar_jogos(conexao)
    por_id = {j["id"]: j for j in jogos}
    registros = cal.carregar_registros(conexao)
    Q, com_treino = cal.calibrar_andando_no_tempo(registros, cal.METODO_PRINCIPAL)
    jogos_cbf, _ = bl.montar_jogos(conexao, backtest.prever_walk_forward(jogos), bl.pesos_por_ano(b2.carregar_amostra(conexao)))
    cbf = {j["id"]: j["previsoes"]["retrospecto"] for j in jogos_cbf} if config.MODELO_CLUBES == "retrospecto_cbf" else {}
    elo = elo_clubes.prever_walk_forward(jogos, elo_clubes.clubes_do_banco(conexao)) if config.ELO_CLUBES_ATIVO else {}

    linhas = []
    for r, q, treinado in zip(registros, Q, com_treino):
        jogo = por_id[r["id"]]
        ano = int(jogo["data_jogo"][:4]) if jogo["data_jogo"] and jogo["data_jogo"][:4].isdigit() else None
        if ano is None or ano < config.CONFIABILIDADE_DESDE_ANO:
            continue
        if r["id"] in cbf:
            p = (_vetor(cbf[r["id"]]) + _vetor(elo[r["id"]]["p"])) / 2 if r["id"] in elo else _vetor(cbf[r["id"]])
            tipo = "Séries A e B"
        elif r["origem"] == "elo_selecoes":
            p, tipo = _vetor(r["p"]), "Seleções"
        elif r["id"] in elo:
            p, tipo = _vetor(elo[r["id"]]["p"]), "Demais clubes"
        else:
            p, tipo = (q if treinado else _vetor(r["p"])), "Outros jogos"
        linhas.append({"tipo": tipo, "ano": ano, "p": p, "f": _vetor(r["f"]), "y": _IDX[r["resultado"]],
                       "cluster": str(jogo["concurso_numero"])})
    if not linhas:
        return None

    def grupo(selecao: list[dict], semente: int) -> dict:
        return _metricas(np.array([l["p"] for l in selecao]), np.array([l["f"] for l in selecao]),
                         np.array([l["y"] for l in selecao]), np.array([l["cluster"] for l in selecao]), semente)

    P_total = np.array([l["p"] for l in linhas])
    y_total = np.array([l["y"] for l in linhas])
    return {
        "calculado_em": dt.datetime.now().isoformat(timespec="seconds"),
        "desde_ano": config.CONFIABILIDADE_DESDE_ANO,
        "jogos_apurados": len(jogos),
        "ultimo_concurso": max(j["concurso_numero"] for j in jogos),
        "total": grupo(linhas, config.B2_SEMENTE + 600),
        "por_tipo": {t: grupo([l for l in linhas if l["tipo"] == t], config.B2_SEMENTE + 601 + i)
                     for i, t in enumerate(TIPOS) if any(l["tipo"] == t for l in linhas)},
        "por_ano": {str(a): grupo([l for l in linhas if l["ano"] == a], config.B2_SEMENTE + 700 + a % 100)
                    for a in sorted({l["ano"] for l in linhas})},
        "calibracao": _calibracao(P_total, y_total),
        "elo_clubes_ativo": config.ELO_CLUBES_ATIVO,
        "modelo_clubes": config.MODELO_CLUBES,
    }


def gravar(conexao, medicao: dict) -> None:
    conexao.execute("INSERT INTO medicoes_modelo (calculado_em, ultimo_concurso, conteudo) VALUES (?, ?, ?)",
                    (medicao["calculado_em"], medicao["ultimo_concurso"], json.dumps(medicao, ensure_ascii=False)))


def ultima(conexao) -> dict | None:
    linha = conexao.execute("SELECT conteudo FROM medicoes_modelo ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(linha[0]) if linha else None


def precisa_medir(conexao) -> bool:
    """Mede de novo quando entrou concurso apurado depois da última medição, ou se nunca mediu."""
    atual = conexao.execute("SELECT MAX(concurso_numero) FROM jogos WHERE resultado IS NOT NULL").fetchone()[0]
    linha = conexao.execute("SELECT MAX(ultimo_concurso) FROM medicoes_modelo").fetchone()[0]
    return atual is not None and (linha is None or atual > linha)

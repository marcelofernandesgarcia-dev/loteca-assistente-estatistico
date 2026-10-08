"""D6 — concursos com muitos ganhadores, os que fogem da média (pedido do usuário em 07/10/2026). Só mede.

Pergunta: nos concursos "pulverizados" (os 10% com mais ganhadores de 14 por milhão arrecadado DENTRO do mesmo ano,
porque a arrecadação muda com o tempo), há algo perceptível ANTES do prazo? E, depois do resultado, o que os
distingue?

Previsões de cada jogo como o app faria na época, andando no tempo: Elo de clubes nos jogos entre clubes, Elo das
seleções, e o modelo histórico no resto (stats.calibracao.carregar_registros).

Sinais conhecidos antes do prazo (fixados antes de ver o resultado):
- dificuldade prevista (soma de −ln da chance do favorito), favoritos fortes (60% ou mais), jogos equilibrados
  (favorito abaixo de 45%), favoritos que são o mandante;
- jogos de seleções, jogos entre clubes brasileiros, jogos com clube estrangeiro;
- concurso anterior acumulou; número do concurso terminado em 0 ou 5 (recebe o acumulado especial).
O que aconteceu (só para descrever): favoritos que confirmaram, zebras (resultado com menos de 25%), empates,
vitórias do mandante, surpresa total (soma de −ln da chance do resultado).

Testes: diferença entre pulverizados e os outros, sinal a sinal, com valor p por permutação dentro do ano e q de
Benjamini-Hochberg; e um teste fora da amostra (logística com os sinais de antes do prazo, treinada só nos anos
anteriores), medido pela área sob a curva ROC, com intervalo por reamostragem. Área perto de 0,5 = não perceptível.
"""
import math
from collections import defaultdict

import numpy as np

import config
from stats import anti_manada, backtest, calibracao as cal, elo_clubes
from stats.associacao import ajustar_benjamini_hochberg

PERCENTIL_PULVERIZADO = 0.90
ANTES = {
    "dificuldade": "Dificuldade prevista (soma de −ln da chance do favorito)",
    "favoritos_fortes": "Favoritos com 60% ou mais",
    "equilibrados": "Jogos equilibrados (favorito abaixo de 45%)",
    "favorito_mandante": "Favorito é o mandante",
    "selecoes": "Jogos entre seleções",
    "brasileiros": "Jogos entre clubes brasileiros",
    "estrangeiros": "Jogos com clube estrangeiro",
    "anterior_acumulou": "Concurso anterior acumulou (0 ou 1)",
    "final_0_ou_5": "Número terminado em 0 ou 5 (0 ou 1)",
}
DEPOIS = {
    "favoritos_confirmados": "Favoritos que confirmaram",
    "zebras": "Zebras (resultado com menos de 25%)",
    "empates": "Empates",
    "vitorias_mandante": "Vitórias do mandante",
    "surpresa": "Surpresa total (soma de −ln da chance do resultado)",
}


def sinais_dos_jogos(jogos: list[dict]) -> dict[str, float]:
    """Os sinais de antes do prazo que vêm dos jogos (todos os de ANTES menos os dois do concurso). Cada jogo:
    {'p': {'1','X','2'} em %, 'casa': (tipo, pais_ou_uf), 'fora': (tipo, pais_ou_uf)}. Usada pelo estudo e pelo
    termômetro do perfil (stats.perfil_concurso), para os dois contarem do mesmo jeito."""
    s = dict.fromkeys(("dificuldade", "favoritos_fortes", "equilibrados", "favorito_mandante", "selecoes",
                       "brasileiros", "estrangeiros"), 0.0)
    for j in jogos:
        p = j["p"]
        favorito = max(("1", "X", "2"), key=lambda k: p[k])
        s["dificuldade"] += -math.log(max(p[favorito], 1e-9) / 100)
        s["favoritos_fortes"] += p[favorito] >= 60
        s["equilibrados"] += p[favorito] < 45
        s["favorito_mandante"] += favorito == "1"
        (tc, uc), (tf, uf) = j["casa"], j["fora"]
        s["selecoes"] += tc == "selecao" and tf == "selecao"
        s["brasileiros"] += tc == tf == "clube" and len(uc or "") == 2 and len(uf or "") == 2
        s["estrangeiros"] += (tc == "clube" and len(uc or "") != 2) or (tf == "clube" and len(uf or "") != 2)
    return s


def ajustar_logistica(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Logística binária com leve regularização (Newton), sobre as colunas padronizadas. Devolve (pesos com o
    intercepto primeiro, média e desvio usados na padronização)."""
    media, desvio = X.mean(axis=0), X.std(axis=0) + 1e-9
    Z = np.column_stack([np.ones(len(X)), (X - media) / desvio])
    w = np.zeros(Z.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-Z @ w))
        H = Z.T @ (Z * (p * (1 - p))[:, None]) + 1e-2 * np.eye(Z.shape[1])
        w -= np.linalg.solve(H, Z.T @ (p - y) + 1e-2 * w)
    return w, media, desvio


def pontuar(X: np.ndarray, modelo: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    w, media, desvio = modelo
    return np.column_stack([np.ones(len(X)), (X - media) / desvio]) @ w


def _previsoes(conexao) -> dict[int, dict]:
    """{id_do_jogo: {'1','X','2'} em %} como o app faria na época."""
    jogos = backtest.carregar_jogos(conexao)
    elo = elo_clubes.prever_walk_forward(jogos, elo_clubes.clubes_do_banco(conexao), desde_ano=2005)
    saida = {}
    for r in cal.carregar_registros(conexao):
        saida[r["id"]] = elo[r["id"]]["p"] if r["id"] in elo and r["origem"] != "elo_selecoes" else r["p"]
    return saida


def montar(conexao) -> list[dict]:
    concursos, _ = anti_manada.carregar_concursos(conexao)
    previsoes = _previsoes(conexao)
    tipo = {l["id"]: (l["tipo"], l["pais_ou_uf"]) for l in conexao.execute("SELECT id, tipo, pais_ou_uf FROM participantes")}
    acumulou = {l["numero"]: l["acumulado"] for l in conexao.execute("SELECT numero, acumulado FROM concursos")}
    jogos = defaultdict(list)
    for j in conexao.execute("SELECT id, concurso_numero, casa_id, fora_id, resultado FROM jogos WHERE resultado IS NOT NULL"):
        jogos[j["concurso_numero"]].append(j)
    por_ano = defaultdict(list)
    for c in concursos:
        por_ano[c["ano"]].append(c["ganhadores_por_milhao"])
    linhas = []
    for c in concursos:
        lista = jogos.get(c["numero"], [])
        if len(lista) != 14 or any(j["id"] not in previsoes for j in lista):
            continue
        do_ano = sorted(por_ano[c["ano"]])
        posicao = sum(1 for v in do_ano if v <= c["ganhadores_por_milhao"]) / len(do_ano)
        s = defaultdict(float, sinais_dos_jogos([
            {"p": previsoes[j["id"]], "casa": tipo[j["casa_id"]], "fora": tipo[j["fora_id"]]} for j in lista]))
        for j in lista:
            p = previsoes[j["id"]]
            favorito = max(("1", "X", "2"), key=lambda k: p[k])
            s["favoritos_confirmados"] += j["resultado"] == favorito
            s["zebras"] += p[j["resultado"]] < config.ANALISE_LIMIAR_ZEBRA
            s["empates"] += j["resultado"] == "X"
            s["vitorias_mandante"] += j["resultado"] == "1"
            s["surpresa"] += -math.log(max(p[j["resultado"]], 1e-9) / 100)
        s["anterior_acumulou"] = float(acumulou.get(c["numero"] - 1) == 1)
        s["final_0_ou_5"] = float(c["numero"] % 5 == 0)
        linhas.append({"numero": c["numero"], "ano": c["ano"], "por_milhao": c["ganhadores_por_milhao"],
                       "ganhadores_14": c["ganhadores_14"], "posicao_no_ano": posicao,
                       "pulverizado": posicao > PERCENTIL_PULVERIZADO, **s})
    return linhas


def _diferenca(linhas: list[dict], chave: str, semente: int) -> dict:
    """Média nos pulverizados menos nos outros; valor p bilateral por permutação do rótulo dentro do ano."""
    x = np.array([l[chave] for l in linhas], dtype=float)
    rotulo = np.array([l["pulverizado"] for l in linhas])
    anos = np.array([l["ano"] for l in linhas])
    observado = x[rotulo].mean() - x[~rotulo].mean()
    rng = np.random.default_rng(semente)
    maiores = 0
    for _ in range(config.Q7_PERMUTACOES):
        embaralhado = rotulo.copy()
        for a in np.unique(anos):
            m = anos == a
            embaralhado[m] = rng.permutation(embaralhado[m])
        if abs(x[embaralhado].mean() - x[~embaralhado].mean()) >= abs(observado) - 1e-12:
            maiores += 1
    return {"pulverizados": float(x[rotulo].mean()), "outros": float(x[~rotulo].mean()), "diferenca": float(observado),
            "p": (1 + maiores) / (1 + config.Q7_PERMUTACOES)}


def _auc(pontos: np.ndarray, rotulo: np.ndarray) -> float:
    """Área sob a curva ROC (Mann-Whitney), com postos médios nos empates."""
    pos, neg = pontos[rotulo], pontos[~rotulo]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    postos = anti_manada.postos_medios(np.concatenate([pos, neg]))
    return float((postos[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def teste_fora_da_amostra(linhas: list[dict]) -> dict:
    """Logística com os sinais de antes do prazo, treinada nos anos anteriores e aplicada a cada ano."""
    chaves = list(ANTES)
    anos = sorted({l["ano"] for l in linhas})
    pontos, rotulos = [], []
    posicoes = []
    for ano in anos[3:]:
        treino = [l for l in linhas if l["ano"] < ano]
        teste = [l for l in linhas if l["ano"] == ano]
        Xt = np.array([[l[k] for k in chaves] for l in treino], dtype=float)
        modelo = ajustar_logistica(Xt, np.array([int(l["pulverizado"]) for l in treino]))
        do_treino = np.sort(pontuar(Xt, modelo))
        novos = pontuar(np.array([[l[k] for k in chaves] for l in teste], dtype=float), modelo)
        pontos += list(novos)
        # Posição de cada concurso testado entre os concursos de treino (0 a 1), para medir o termômetro por faixa.
        posicoes += list(np.searchsorted(do_treino, novos, side="right") / len(do_treino))
        rotulos += [l["pulverizado"] for l in teste]
    pontos, rotulos = np.array(pontos), np.array(rotulos)
    auc = _auc(pontos, rotulos)
    rng = np.random.default_rng(config.Q7_SEMENTE + 99)
    amostras = []
    for _ in range(config.Q7_REPETICOES_BOOTSTRAP):
        i = rng.integers(0, len(pontos), len(pontos))
        valor = _auc(pontos[i], rotulos[i])
        if not math.isnan(valor):
            amostras.append(valor)
    ic = np.percentile(amostras, [2.5, 97.5])
    return {"concursos_testados": int(len(pontos)), "pulverizados_testados": int(rotulos.sum()),
            "auc": auc, "ic_inferior": float(ic[0]), "ic_superior": float(ic[1]),
            "perceptivel": bool(ic[0] > 0.5),
            "posicoes": [float(x) for x in posicoes], "rotulos": [bool(x) for x in rotulos]}


def estudar(conexao) -> dict:
    linhas = montar(conexao)
    antes = [{"sinal": k, "descricao": d, **_diferenca(linhas, k, config.Q7_SEMENTE + i)} for i, (k, d) in enumerate(ANTES.items())]
    depois = [{"sinal": k, "descricao": d, **_diferenca(linhas, k, config.Q7_SEMENTE + 50 + i)} for i, (k, d) in enumerate(DEPOIS.items())]
    for grupo in (antes, depois):
        for r, q in zip(grupo, ajustar_benjamini_hochberg([r["p"] for r in grupo])):
            r["q"] = q
    topo = sorted(linhas, key=lambda l: -l["posicao_no_ano"] * 1000 - l["por_milhao"])[:15]
    return {"concursos": len(linhas), "pulverizados": sum(l["pulverizado"] for l in linhas),
            "antes": antes, "depois": depois, "fora_da_amostra": teste_fora_da_amostra(linhas),
            "mais_pulverizados": [{k: l[k] for k in ("numero", "ano", "ganhadores_14", "por_milhao", "favoritos_confirmados",
                                                      "zebras", "dificuldade", "favoritos_fortes")} for l in topo]}

"""Calibração dos percentuais (E4): corrigir percentuais confiantes demais antes de entrarem na
chance do bilhete.

Motivo: no estudo de 30/09/2026, bilhetes montados pela regra do app fizeram 13 ou mais em 29 de
1.127 concursos, onde a conta pelos percentuais previa 217. A conta do bilhete está certa; os
percentuais é que dizem 60% para o que acontece bem menos que 60% das vezes.

Correção (parâmetros em `config.CALIBRACAO_*`), por origem do percentual (força histórica dos clubes,
frequência simples, Elo das seleções):

    q ∝ p ** expoente          (expoente < 1 achata; = 1 mantém)
    q = mistura * q + (1 - mistura) * frequência simples da Loteca

Expoente e mistura são escolhidos por busca em grade, minimizando a perda logarítmica, SÓ com
concursos anteriores ao bloco corrigido (reajuste a cada `CALIBRACAO_REAJUSTE_A_CADA` concursos).
O método principal foi definido antes de ver o resultado: expoente e mistura juntos (contém os
dois isolados e a ausência de correção como casos particulares).

O ajuste de notícias não tem histórico para ser calibrado: continua aplicado por cima, como hoje.
"""
import datetime as dt
import logging
import random
import sqlite3
from collections import defaultdict

import numpy as np

import config
from stats import backtest
from stats import backtest_competicao as b2
from stats.associacao import ajustar_benjamini_hochberg
from stats.otimizacao_bilhete import distribuicao_por_regra

logger = logging.getLogger(__name__)

COLUNAS = ("1", "X", "2")
METODOS = ("original", "temperatura", "mistura", "temperatura_e_mistura")
METODO_PRINCIPAL = "temperatura_e_mistura"
DESCRICAO_METODO = {
    "original": "Sem correção (percentuais de hoje)",
    "temperatura": "Só expoente",
    "mistura": "Só mistura com a frequência",
    "temperatura_e_mistura": "Expoente e mistura (principal)",
}
DESCRICAO_ORIGEM = {
    "poisson": "Clubes: força histórica (Poisson)",
    "frequencia_global": "Frequência simples (poucos jogos)",
    "elo_selecoes": "Seleções: Elo",
}
LIMITE_PROBABILIDADE = 1e-6


# ------------------------------------------------------------------ previsões reconstruídas

def previsoes_elo_por_jogo(conexao, jogos_base: list[dict] | None = None, nomes: dict[str, str] | None = None) -> dict[int, dict]:
    """{id do jogo: {'1','X','2'} em %} pelo Elo, para os jogos da Loteca entre seleções depois do corte
    de teste, sem olhar o futuro (mesmo procedimento de `selecoes.backtest_selecoes`, campo desconhecido)."""
    from stats import selecoes as sel

    jogos_base = jogos_base if jogos_base is not None else sel.carregar_resultados()
    nomes = nomes if nomes is not None else sel.carregar_nomes()
    indice = sel.indexar_base(jogos_base)
    corte = config.SELECOES_CORTE_TESTE
    parametros = sel.ajustar_curva(*sel.amostras_de_treino(jogos_base, config.SELECOES_TREINO_DESDE, corte))

    casados = []
    for jogo in sel.jogos_da_loteca_entre_selecoes(conexao):
        a, b = nomes.get(jogo["casa"].upper()), nomes.get(jogo["fora"].upper())
        if not a or not b:
            continue
        par = sel.casar_jogo(indice, jogos_base, a, b, jogo["data_jogo"])
        if par is not None:
            casados.append({**jogo, "casa_base": a, "fora_base": b, **par})
    antes = [c for c in casados if c["jogo"]["data"] < corte]
    nao_neutro = sum(1 for c in antes if not c["jogo"]["neutro"]) / len(antes) if antes else 0.5
    teste = sorted((c for c in casados if c["jogo"]["data"] >= corte), key=lambda c: c["jogo"]["data"])
    ratings = sel._ratings_antes_de_cada_jogo(jogos_base, [(c["jogo"]["data"], c["casa_base"], c["fora_base"]) for c in teste])
    return {
        c["id"]: sel.probabilidades(parametros, (rating_casa - rating_fora) / 100.0, nao_neutro)
        for c, (rating_casa, rating_fora) in zip(teste, ratings)
    }


def montar_registros(jogos: list[dict], previsoes_b3: dict[int, dict], previsoes_elo: dict[int, dict]) -> list[dict]:
    """Um registro por jogo com previsão andando no tempo, reproduzindo o que o app usa: Elo nos jogos
    entre seleções (quando há previsão honesta), senão o modelo histórico do B3 (Poisson ou frequência)."""
    por_id = {j["id"]: j for j in jogos}
    registros = []
    for id_jogo, previsao in previsoes_b3.items():
        jogo = por_id[id_jogo]
        elo = previsoes_elo.get(id_jogo)
        registros.append(
            {
                "id": id_jogo, "concurso": previsao["concurso"], "num_jogo": jogo["num_jogo"], "resultado": jogo["resultado"],
                "origem": "elo_selecoes" if elo else previsao["origem"],
                "p": elo or previsao["atual"], "f": previsao["referencia"],
            }
        )
    return sorted(registros, key=lambda r: (r["concurso"], r["num_jogo"]))


# ------------------------------------------------------------------ correção

def como_matriz(percentuais: list[dict]) -> np.ndarray:
    """n x 3 em fração, sem zeros e somando 1 por linha."""
    m = np.array([[p[c] for c in COLUNAS] for p in percentuais], dtype=float).reshape(-1, 3) / 100.0
    m = np.clip(m, LIMITE_PROBABILIDADE, None)
    return m / m.sum(axis=1, keepdims=True)


def aplicar(P: np.ndarray, F: np.ndarray, expoente: float, mistura: float) -> np.ndarray:
    potencia = P ** expoente
    potencia = potencia / potencia.sum(axis=1, keepdims=True)
    return mistura * potencia + (1.0 - mistura) * F


def _grades(metodo: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if metodo == "original":
        return (1.0,), (1.0,)
    if metodo == "temperatura":
        return config.CALIBRACAO_GRADE_EXPOENTE, (1.0,)
    if metodo == "mistura":
        return (1.0,), config.CALIBRACAO_GRADE_MISTURA
    if metodo == "temperatura_e_mistura":
        return config.CALIBRACAO_GRADE_EXPOENTE, config.CALIBRACAO_GRADE_MISTURA
    raise ValueError(f"Método de calibração desconhecido: {metodo}")


def ajustar(P: np.ndarray, F: np.ndarray, y: np.ndarray, metodo: str) -> tuple[float, float]:
    """(expoente, mistura) de menor perda logarítmica média nos dados de treino. `y` em {0, 1, 2}.
    Empate na perda fica com o valor mais perto de "sem correção" (expoente e mistura maiores)."""
    expoentes, misturas = _grades(metodo)
    if len(y) == 0:
        return 1.0, 1.0
    linhas = np.arange(len(y))
    f_real = F[linhas, y]
    w = np.array(misturas)[:, None]
    melhor = (np.inf, 1.0, 1.0)
    for a in sorted(expoentes, reverse=True):
        potencia = P ** a
        p_real = potencia[linhas, y] / potencia.sum(axis=1)
        perdas = -np.log(np.clip(w * p_real + (1 - w) * f_real, LIMITE_PROBABILIDADE, None)).mean(axis=1)
        for mistura, perda in sorted(zip(misturas, perdas), key=lambda x: -x[0]):
            if perda < melhor[0] - 1e-12:
                melhor = (float(perda), float(a), float(mistura))
    return melhor[1], melhor[2]


def calibrar_andando_no_tempo(registros: list[dict], metodo: str) -> tuple[np.ndarray, np.ndarray]:
    """(matriz n x 3 corrigida, marcador de 'havia treino suficiente'), alinhadas a `registros`. Cada bloco de
    concursos é corrigido com parâmetros ajustados só nos concursos anteriores ao bloco, por origem."""
    P = como_matriz([r["p"] for r in registros])
    F = como_matriz([r["f"] for r in registros])
    y = np.array([COLUNAS.index(r["resultado"]) for r in registros])
    concursos = np.array([r["concurso"] for r in registros])
    origens = np.array([r["origem"] for r in registros])
    Q, com_treino = P.copy(), np.zeros(len(registros), dtype=bool)
    lista_concursos = sorted(set(concursos.tolist()))
    for inicio in range(0, len(lista_concursos), config.CALIBRACAO_REAJUSTE_A_CADA):
        bloco = lista_concursos[inicio:inicio + config.CALIBRACAO_REAJUSTE_A_CADA]
        no_bloco = np.isin(concursos, bloco)
        for origem in set(origens[no_bloco].tolist()):
            alvo = no_bloco & (origens == origem)
            treino = (concursos < bloco[0]) & (origens == origem)
            if treino.sum() >= config.CALIBRACAO_MINIMO_JOGOS.get(origem, 500):
                a, w = ajustar(P[treino], F[treino], y[treino], metodo)
                Q[alvo] = aplicar(P[alvo], F[alvo], a, w)
                com_treino[alvo] = True
    return Q, com_treino


def parametros_finais(registros: list[dict], metodo: str = METODO_PRINCIPAL) -> dict[str, dict]:
    """Parâmetros ajustados com todos os concursos, por origem (o que o app usaria hoje)."""
    saida = {}
    for origem in sorted({r["origem"] for r in registros}):
        do_tipo = [r for r in registros if r["origem"] == origem]
        P, F = como_matriz([r["p"] for r in do_tipo]), como_matriz([r["f"] for r in do_tipo])
        a, w = ajustar(P, F, np.array([COLUNAS.index(r["resultado"]) for r in do_tipo]), metodo)
        saida[origem] = {"expoente": a, "mistura": w, "jogos": len(do_tipo)}
    return saida


# ------------------------------------------------------------------ medidas

def perda_log_por_jogo(Q: np.ndarray, y: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(Q[np.arange(len(y)), y], LIMITE_PROBABILIDADE, None))


def brier_por_jogo(Q: np.ndarray, y: np.ndarray) -> np.ndarray:
    real = np.eye(3)[y]
    return ((Q - real) ** 2).sum(axis=1)


def curva_de_calibracao(Q: np.ndarray, y: np.ndarray, largura: float = 0.1) -> list[dict]:
    """Por faixa de probabilidade prevista (os três resultados de cada jogo): previsto médio e observado."""
    previsto, real = Q.ravel(), np.eye(3)[y].ravel()
    faixas = np.minimum((previsto / largura).astype(int), int(round(1 / largura)) - 1)
    saida = []
    for i in sorted(set(faixas.tolist())):
        m = faixas == i
        saida.append({"faixa": (i * largura, (i + 1) * largura), "n": int(m.sum()),
                      "previsto": float(previsto[m].mean()), "observado": float(real[m].mean())})
    return saida


def distribuicao_de_acertos(chances: list[float] | np.ndarray) -> np.ndarray:
    """Probabilidade de 0, 1, ..., n acertos, com a chance coberta de cada jogo (fração) e jogos
    independentes (Poisson-binomial exata). Soma 1."""
    distribuicao = np.array([1.0])
    for p in chances:
        p = float(min(max(p, 0.0), 1.0))
        distribuicao = np.concatenate([distribuicao * (1 - p), [0.0]]) + np.concatenate([[0.0], distribuicao * p])
    return distribuicao


def marcar_bilhete(pcts: list[dict], duplos: int, triplos: int, modo: str, sorteio: random.Random) -> list[list[str]]:
    """Colunas do bilhete de teste. "regra": como a sugestão do app; "sorteada": jogos e colunas sorteados."""
    if modo == "regra":
        return distribuicao_por_regra(pcts, duplos, triplos)
    if modo == "sorteada":
        jogos = sorteio.sample(range(len(pcts)), duplos + triplos)
        quantos = [1] * len(pcts)
        for i in jogos[:triplos]:
            quantos[i] = 3
        for i in jogos[triplos:]:
            quantos[i] = 2
        return [sorted(sorteio.sample(COLUNAS, k), key=COLUNAS.index) for k in quantos]
    raise ValueError(f"Modo de bilhete desconhecido: {modo}")


def conferir_bilhetes(registros: list[dict], Q_original: np.ndarray, Q_corrigida: np.ndarray, mascara: np.ndarray) -> list[dict]:
    """Para cada bilhete de teste (config), somado nos concursos com os 14 jogos avaliáveis: quantas vezes
    fez 13+ e 14, quanto cada conta previa e o intervalo de 95% do previsto. As colunas são escolhidas com
    os percentuais originais (o mesmo bilhete nas duas contas), só a chance muda."""
    por_concurso = defaultdict(list)
    for i, r in enumerate(registros):
        if mascara[i]:
            por_concurso[r["concurso"]].append(i)
    concursos = [sorted(ids, key=lambda i: registros[i]["num_jogo"]) for _, ids in sorted(por_concurso.items()) if len(ids) == 14]
    saida = []
    for duplos, triplos, modo in config.CALIBRACAO_BILHETES_DE_TESTE:
        sorteio = random.Random(config.CALIBRACAO_SEMENTE + 31 * duplos + 7 * triplos)
        conta = {"feito_13": 0, "feito_14": 0}
        soma = {chave: {"13": 0.0, "14": 0.0, "var13": 0.0, "var14": 0.0} for chave in ("original", "corrigida")}
        for ids in concursos:
            pcts = [registros[i]["p"] for i in ids]
            reais = [registros[i]["resultado"] for i in ids]
            marcas = marcar_bilhete(pcts, duplos, triplos, modo, sorteio)
            n_acertos = sum(1 for m, r in zip(marcas, reais) if r in m)
            conta["feito_13"] += n_acertos >= 13
            conta["feito_14"] += n_acertos == 14
            for chave, Q in (("original", Q_original), ("corrigida", Q_corrigida)):
                cobertas = [sum(Q[i, COLUNAS.index(c)] for c in m) for i, m in zip(ids, marcas)]
                dist = distribuicao_de_acertos(cobertas)
                p13, p14 = float(dist[13] + dist[14]), float(dist[14])
                soma[chave]["13"] += p13
                soma[chave]["14"] += p14
                soma[chave]["var13"] += p13 * (1 - p13)
                soma[chave]["var14"] += p14 * (1 - p14)
        linha = {"duplos": duplos, "triplos": triplos, "modo": modo, "apostas": 2**duplos * 3**triplos, "concursos": len(concursos), **conta}
        for chave in soma:
            for faixa in ("13", "14"):
                previsto, dp = soma[chave][faixa], float(np.sqrt(soma[chave]["var" + faixa]))
                linha[f"previsto_{faixa}_{chave}"] = previsto
                linha[f"intervalo_{faixa}_{chave}"] = (max(0.0, previsto - 1.96 * dp), previsto + 1.96 * dp)
        saida.append(linha)
    return saida


def distribuicao_de_acertos_por_concurso(registros: list[dict], Q: np.ndarray, mascara: np.ndarray, minimo: int = 10) -> dict:
    """Conferência da suposição de jogos independentes: com o bilhete de um duplo pela regra, o número
    esperado de concursos com pelo menos k acertos (k = minimo..14) contra o observado."""
    por_concurso = defaultdict(list)
    for i, r in enumerate(registros):
        if mascara[i]:
            por_concurso[r["concurso"]].append(i)
    esperado, observado = defaultdict(float), defaultdict(int)
    for ids in (sorted(v, key=lambda i: registros[i]["num_jogo"]) for v in por_concurso.values() if len(v) == 14):
        pcts = [registros[i]["p"] for i in ids]
        marcas = distribuicao_por_regra(pcts, 1, 0)
        dist = distribuicao_de_acertos([sum(Q[i, COLUNAS.index(c)] for c in m) for i, m in zip(ids, marcas)])
        n_acertos = sum(1 for i, m in zip(ids, marcas) if registros[i]["resultado"] in m)
        for k in range(minimo, 15):
            esperado[k] += float(dist[k:].sum())
            observado[k] += n_acertos >= k
    return {k: {"esperado": esperado[k], "observado": observado[k]} for k in range(minimo, 15)}


def estudar(registros: list[dict]) -> dict | None:
    """Estudo completo: métricas por método e por origem, comparações pareadas com o original, curva de
    calibração, conferência nos bilhetes e na distribuição de acertos, e os parâmetros finais."""
    if not registros:
        return None
    y = np.array([COLUNAS.index(r["resultado"]) for r in registros])
    corrigidas, mascara = {}, None
    for metodo in METODOS:
        Q, com_treino = calibrar_andando_no_tempo(registros, metodo)
        corrigidas[metodo] = Q
        if metodo == METODO_PRINCIPAL:
            mascara = com_treino
    if not mascara.any():
        return None
    F = como_matriz([r["f"] for r in registros])
    origens = np.array([r["origem"] for r in registros])
    clusters = np.array([f"concurso-{r['concurso']}" for r in registros])[mascara]

    def resumo(Q, filtro):
        return {"n": int(filtro.sum()), "perda_log": float(perda_log_por_jogo(Q[filtro], y[filtro]).mean()),
                "brier": float(brier_por_jogo(Q[filtro], y[filtro]).mean())}

    metricas = {m: resumo(Q, mascara) for m, Q in corrigidas.items()} | {"frequencia": resumo(F, mascara)}
    por_origem = {
        origem: {m: resumo(Q, mascara & (origens == origem)) for m, Q in (*corrigidas.items(), ("frequencia", F))}
        for origem in sorted(set(origens[mascara].tolist()))
    }
    base = perda_log_por_jogo(corrigidas["original"][mascara], y[mascara])
    comparacoes = []
    for indice, metodo in enumerate(m for m in METODOS if m != "original"):
        ganho = base - perda_log_por_jogo(corrigidas[metodo][mascara], y[mascara])
        comparacoes.append({"metodo": metodo, **b2._bootstrap_por_cluster(
            ganho, clusters, config.CALIBRACAO_REPETICOES_BOOTSTRAP, config.CALIBRACAO_SEMENTE + indice)})
    for c, q in zip(comparacoes, ajustar_benjamini_hochberg([c["p"] for c in comparacoes])):
        c["q"] = q
        c["conclusao"] = "melhor que sem correção" if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA else (
            "pior que sem correção" if c["ic_superior"] < 0 else "sem diferença perceptível")
    principal = corrigidas[METODO_PRINCIPAL]
    return {
        "jogos_avaliados": int(mascara.sum()),
        "concursos_avaliados": len({r["concurso"] for r, m in zip(registros, mascara) if m}),
        "por_origem_n": {o: int((mascara & (origens == o)).sum()) for o in sorted(set(origens.tolist()))},
        "metricas": metricas,
        "por_origem": por_origem,
        "comparacoes": comparacoes,
        "curva_original": curva_de_calibracao(corrigidas["original"][mascara], y[mascara]),
        "curva_corrigida": curva_de_calibracao(principal[mascara], y[mascara]),
        "bilhetes": conferir_bilhetes(registros, corrigidas["original"], principal, mascara),
        "distribuicao_original": distribuicao_de_acertos_por_concurso(registros, corrigidas["original"], mascara),
        "distribuicao_corrigida": distribuicao_de_acertos_por_concurso(registros, principal, mascara),
        "parametros_finais": parametros_finais(registros),
    }


# ------------------------------------------------------------------ uso no app (Fase 2)

ORIGEM_TEXTO = {
    "poisson": "Histórico dos clubes",
    "frequencia_global": "Frequência simples (poucos jogos)",
    "elo_selecoes": "Elo das seleções",
    "retrospecto_cbf": "Temporada da CBF",
}


def gravar_parametros(conexao, parametros: dict[str, dict], ate_concurso: int) -> None:
    """Grava (substitui) os parâmetros por origem. `parametros` vem de `parametros_finais`."""
    agora = _agora()
    for origem, p in parametros.items():
        conexao.execute(
            "INSERT INTO calibracao (origem, expoente, mistura, jogos, ate_concurso, ajustado_em) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(origem) DO UPDATE SET expoente = excluded.expoente, mistura = excluded.mistura, jogos = excluded.jogos, "
            "ate_concurso = excluded.ate_concurso, ajustado_em = excluded.ajustado_em",
            (origem, p["expoente"], p["mistura"], p["jogos"], ate_concurso, agora),
        )


def carregar_parametros(conexao) -> dict[str, dict]:
    """{origem: {expoente, mistura, jogos, ate_concurso, ajustado_em}}; vazio se a tabela não existe ou não tem linhas."""
    try:
        linhas = conexao.execute("SELECT origem, expoente, mistura, jogos, ate_concurso, ajustado_em FROM calibracao").fetchall()
    except sqlite3.OperationalError:
        return {}  # banco ainda sem a tabela: o app segue sem correção até `inicializar_schema` rodar
    return {l["origem"]: dict(l) for l in linhas}


def ultimo_concurso_apurado(conexao) -> int:
    linha = conexao.execute("SELECT COALESCE(MAX(concurso_numero), 0) FROM jogos WHERE resultado IS NOT NULL").fetchone()
    return int(linha[0])


def precisa_recalibrar(conexao) -> bool:
    """True quando não há parâmetros ou entrou concurso apurado depois do último ajuste."""
    parametros = carregar_parametros(conexao)
    if not parametros:
        return True
    return ultimo_concurso_apurado(conexao) > max(p["ate_concurso"] for p in parametros.values())


def recalibrar(conexao) -> dict | None:
    """Refaz os parâmetros com todos os concursos apurados e grava. Devolve {origem: parâmetros} ou None se
    não há jogos suficientes. Não faz commit."""
    registros = carregar_registros(conexao)
    if not registros:
        return None
    parametros = parametros_finais(registros)
    gravar_parametros(conexao, parametros, max(r["concurso"] for r in registros))
    return parametros


def corrigir_percentual(original: dict, origem: str, frequencia: dict, parametros: dict) -> dict:
    """Percentual corrigido ({'1','X','2'} em %) com os parâmetros da origem."""
    P = como_matriz([original])
    F = como_matriz([frequencia])
    Q = aplicar(P, F, parametros["expoente"], parametros["mistura"])[0]
    return {c: 100.0 * float(v) for c, v in zip(COLUNAS, Q)}


def calibrar_jogo(conexao, casa_id: int, fora_id: int, original: dict | None = None) -> dict:
    """O percentual de um jogo com a calibração aplicada.

    Devolve {'original', 'calibrado', 'origem', 'aplicada', 'expoente', 'mistura', 'motivo'}. `calibrado` é igual a
    `original` quando a correção não se aplica (interruptor desligado, origem não calibrada ou sem parâmetros
    gravados); `motivo` diz qual foi o caso."""
    from stats.frequencia import frequencia_global
    from stats.percentual import origem_do_percentual, percentual_historico

    original = original if original is not None else percentual_historico(conexao, casa_id, fora_id)
    origem = origem_do_percentual(conexao, casa_id, fora_id)["metodo"]
    resultado = {"original": original, "calibrado": original, "origem": origem, "aplicada": False,
                 "expoente": None, "mistura": None, "motivo": None}
    if not config.CALIBRACAO_ATIVA:
        resultado["motivo"] = "interruptor desligado"
        return resultado
    if origem not in config.CALIBRACAO_ORIGENS_APLICADAS:
        resultado["motivo"] = "origem não corrigida"
        return resultado
    parametros = carregar_parametros(conexao).get(origem)
    if parametros is None:
        resultado["motivo"] = "sem parâmetros gravados"
        return resultado
    frequencia = frequencia_global(conexao)
    if not frequencia.get("total_jogos"):
        resultado["motivo"] = "sem frequência de referência"
        return resultado
    resultado.update(
        calibrado=corrigir_percentual(original, origem, frequencia, parametros), aplicada=True,
        expoente=parametros["expoente"], mistura=parametros["mistura"], motivo=None,
    )
    return resultado


def _agora() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def carregar_registros(conexao) -> list[dict]:
    """Registros de todos os jogos com previsão andando no tempo. Só lê o banco (e a base aberta das seleções)."""
    jogos = backtest.carregar_jogos(conexao)
    previsoes_b3 = backtest.prever_walk_forward(jogos)
    try:
        previsoes_elo = previsoes_elo_por_jogo(conexao)
    except (FileNotFoundError, ValueError) as erro:
        # Sem a base das seleções, os jogos entre seleções ficam no modelo histórico (como o app faz).
        logger.warning("Base de seleções indisponível para a calibração (%s); seleções seguem o modelo histórico.", erro)
        previsoes_elo = {}
    return montar_registros(jogos, previsoes_b3, previsoes_elo)

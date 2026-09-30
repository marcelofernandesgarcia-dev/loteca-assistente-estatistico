"""Força das seleções a partir da base aberta de resultados internacionais
(P1 da priorização estatística, 30/09/2026; docs/priorizacao-estatistica-30-09-2026.md).

Por que existe: metade dos participantes de um concurso são seleções, e o
histórico da Loteca tem só 2 a 45 jogos de cada uma. A base aberta (49 mil
jogos, licença CC0-1.0) tem centenas por seleção.

Método: rating Elo calculado jogo a jogo (só usa o passado de cada jogo) e uma
curva que converte a diferença de rating em probabilidade de 1/X/2. A curva
(regressão logística ordenada) é ajustada só com jogos ANTES da data de corte,
e o teste usa jogos DEPOIS dela -- sem olhar o futuro. Nada muda nos números
do app até o teste (`backtest_selecoes`) mostrar ganho sobre o que já existe.
"""
import bisect
import csv
import math
from datetime import date, timedelta

import numpy as np

import config

RESULTADOS = ("1", "X", "2")


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

def carregar_resultados(caminho: str | None = None) -> list[dict]:
    """Jogos da base aberta em ordem de data. Linha sem placar é ignorada."""
    arquivo = caminho or str(config.SELECOES_BASE_CSV)
    jogos = []
    with open(arquivo, encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            if linha["home_score"] in ("", "NA") or linha["away_score"] in ("", "NA"):
                continue
            jogos.append(
                {
                    "data": linha["date"],
                    "casa": linha["home_team"],
                    "fora": linha["away_team"],
                    "gols_casa": int(linha["home_score"]),
                    "gols_fora": int(linha["away_score"]),
                    "torneio": linha["tournament"],
                    "neutro": linha["neutral"].strip().upper() == "TRUE",
                }
            )
    jogos.sort(key=lambda j: j["data"])
    return jogos


def carregar_nomes(caminho: str | None = None) -> dict[str, str]:
    """{nome na Loteca: nome na base}, de data/selecoes-nomes.csv."""
    arquivo = caminho or str(config.SELECOES_NOMES_CSV)
    with open(arquivo, encoding="utf-8") as f:
        linhas = csv.DictReader((l for l in f if not l.startswith("#")), delimiter=";")
        return {l["nome_loteca"].strip().upper(): l["nome_base"].strip() for l in linhas}


# ---------------------------------------------------------------------------
# Elo
# ---------------------------------------------------------------------------

def peso_torneio(torneio: str) -> float:
    """Quanto um jogo desse torneio mexe no rating (config.ELO_K)."""
    nome = torneio.strip().lower()
    if nome == "friendly":
        return config.ELO_K["amistoso"]
    if nome == "fifa world cup":
        return config.ELO_K["copa_do_mundo"]
    if nome in config.ELO_TORNEIOS_CONTINENTAIS:
        return config.ELO_K["continental"]
    if "qualification" in nome or "nations league" in nome:
        return config.ELO_K["eliminatorias_e_liga_das_nacoes"]
    return config.ELO_K["outros"]


def _multiplicador_de_gols(saldo: int) -> float:
    saldo = abs(saldo)
    if saldo <= 1:
        return 1.0
    return 1.5 if saldo == 2 else (11 + saldo) / 8


def esperado(rating_casa: float, rating_fora: float, neutro: bool) -> float:
    """Resultado esperado da casa (1 = vitória, 0,5 = empate, 0 = derrota)."""
    vantagem = 0.0 if neutro else config.ELO_VANTAGEM_MANDANTE
    return 1.0 / (1.0 + 10 ** (-(rating_casa + vantagem - rating_fora) / 400.0))


def atualizar_elo(ratings: dict[str, float], jogo: dict) -> None:
    """Aplica um jogo aos ratings (soma zero: o que um ganha o outro perde)."""
    casa = ratings.get(jogo["casa"], config.ELO_RATING_INICIAL)
    fora = ratings.get(jogo["fora"], config.ELO_RATING_INICIAL)
    if jogo["gols_casa"] > jogo["gols_fora"]:
        real = 1.0
    elif jogo["gols_casa"] == jogo["gols_fora"]:
        real = 0.5
    else:
        real = 0.0
    delta = (
        peso_torneio(jogo["torneio"])
        * _multiplicador_de_gols(jogo["gols_casa"] - jogo["gols_fora"])
        * (real - esperado(casa, fora, jogo["neutro"]))
    )
    ratings[jogo["casa"]] = casa + delta
    ratings[jogo["fora"]] = fora - delta


def amostras_de_treino(jogos: list[dict], desde: str, ate: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Percorre a base uma vez; para cada jogo em [desde, ate) guarda, ANTES de
    aplicá-lo, a diferença de rating (em centenas de pontos, sem vantagem de
    mandante), se o campo era não-neutro e o resultado (0 = fora, 1 = empate,
    2 = casa). O jogo só entra nos ratings depois de registrado."""
    ratings: dict[str, float] = {}
    d, h, y = [], [], []
    for jogo in jogos:
        if jogo["data"] >= ate:
            break
        if jogo["data"] >= desde:
            rc = ratings.get(jogo["casa"], config.ELO_RATING_INICIAL)
            rf = ratings.get(jogo["fora"], config.ELO_RATING_INICIAL)
            d.append((rc - rf) / 100.0)
            h.append(0.0 if jogo["neutro"] else 1.0)
            y.append(2 if jogo["gols_casa"] > jogo["gols_fora"] else 1 if jogo["gols_casa"] == jogo["gols_fora"] else 0)
        atualizar_elo(ratings, jogo)
    return np.array(d), np.array(h), np.array(y)


# ---------------------------------------------------------------------------
# Curva: diferença de rating -> probabilidade de 1/X/2 (logística ordenada)
# ---------------------------------------------------------------------------

def _sigmoide(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def _probabilidades_array(params, d, h):
    """params = (b, c, t1, g): latente = b*d + c*h; cortes t1 e t1 + exp(g)."""
    b, c, t1, g = params
    latente = b * d + c * h
    p_fora = _sigmoide(t1 - latente)
    p_fora_ou_empate = _sigmoide(t1 + math.exp(g) - latente)
    return p_fora, p_fora_ou_empate - p_fora, 1.0 - p_fora_ou_empate


def _log_verossimilhanca_negativa(params, d, h, y):
    p_fora, p_empate, p_casa = _probabilidades_array(params, d, h)
    p = np.where(y == 0, p_fora, np.where(y == 1, p_empate, p_casa))
    return -float(np.sum(np.log(np.clip(p, 1e-12, 1.0))))


def _nelder_mead(funcao, inicio, passo=0.5, iteracoes=600, tolerancia=1e-9):
    """Minimizador simples (sem scipy) para poucos parâmetros."""
    n = len(inicio)
    pontos = [list(inicio)] + [[v + (passo if i == j else 0.0) for j, v in enumerate(inicio)] for i in range(n)]
    valores = [funcao(p) for p in pontos]
    for _ in range(iteracoes):
        ordem = sorted(range(n + 1), key=lambda i: valores[i])
        pontos = [pontos[i] for i in ordem]
        valores = [valores[i] for i in ordem]
        if abs(valores[-1] - valores[0]) < tolerancia:
            break
        centro = [sum(p[j] for p in pontos[:-1]) / n for j in range(n)]

        def ponto(coef):
            return [centro[j] + coef * (pontos[-1][j] - centro[j]) for j in range(n)]

        refletido = ponto(-1.0)
        v_ref = funcao(refletido)
        if v_ref < valores[0]:
            expandido = ponto(-2.0)
            v_exp = funcao(expandido)
            pontos[-1], valores[-1] = (expandido, v_exp) if v_exp < v_ref else (refletido, v_ref)
        elif v_ref < valores[-2]:
            pontos[-1], valores[-1] = refletido, v_ref
        else:
            contraido = ponto(0.5 if v_ref >= valores[-1] else -0.5)
            v_con = funcao(contraido)
            if v_con < min(v_ref, valores[-1]):
                pontos[-1], valores[-1] = contraido, v_con
            else:
                melhor = pontos[0]
                pontos = [melhor] + [[melhor[j] + 0.5 * (p[j] - melhor[j]) for j in range(n)] for p in pontos[1:]]
                valores = [valores[0]] + [funcao(p) for p in pontos[1:]]
    melhor = min(range(n + 1), key=lambda i: valores[i])
    return pontos[melhor], valores[melhor]


def ajustar_curva(d: np.ndarray, h: np.ndarray, y: np.ndarray) -> tuple[float, float, float, float]:
    """Ajusta (b, c, t1, g) por máxima verossimilhança."""
    if len(y) < 100:
        raise ValueError("Amostra pequena demais para ajustar a curva (menos de 100 jogos).")
    melhor, _ = _nelder_mead(lambda p: _log_verossimilhanca_negativa(p, d, h, y), [0.5, 0.3, -0.5, 0.0])
    return tuple(melhor)


def probabilidades(params, diferenca_centenas: float, nao_neutro: float) -> dict:
    """{'1','X','2'} em %. `nao_neutro` vai de 0 (campo neutro) a 1 (mandante em casa);
    valor intermediário é a mistura das duas situações (campo desconhecido)."""
    d = np.array([diferenca_centenas])
    casa_em_casa = _probabilidades_array(params, d, np.array([1.0]))
    neutro = _probabilidades_array(params, d, np.array([0.0]))
    q = min(max(nao_neutro, 0.0), 1.0)
    p_fora, p_empate, p_casa = (q * float(a[0]) + (1 - q) * float(b[0]) for a, b in zip(casa_em_casa, neutro))
    return {"1": 100.0 * p_casa, "X": 100.0 * p_empate, "2": 100.0 * p_fora}


# ---------------------------------------------------------------------------
# Modelo de produção (usado nos percentuais depois de provado no teste)
# ---------------------------------------------------------------------------

class ModeloSelecoes:
    """Ratings de hoje + curva ajustada com toda a base. O campo do jogo é
    desconhecido na hora de apostar, então usa a fração de jogos da Loteca
    entre seleções que foram em campo não-neutro nos últimos anos."""

    def __init__(self, ratings, parametros, nao_neutro, nomes, ultimo_jogo_da_base):
        self.ratings = ratings
        self.parametros = parametros
        self.nao_neutro = nao_neutro
        self.nomes = nomes
        self.ultimo_jogo_da_base = ultimo_jogo_da_base

    def prever(self, casa_loteca: str, fora_loteca: str) -> dict | None:
        """{'1','X','2'} em %, ou None se alguma das seleções não está no mapa de nomes."""
        casa, fora = self.nomes.get(casa_loteca.strip().upper()), self.nomes.get(fora_loteca.strip().upper())
        if not casa or not fora:
            return None
        diferenca = (self.ratings.get(casa, config.ELO_RATING_INICIAL) - self.ratings.get(fora, config.ELO_RATING_INICIAL)) / 100.0
        return probabilidades(self.parametros, diferenca, self.nao_neutro)

    def rating(self, nome_loteca: str) -> float | None:
        base = self.nomes.get(nome_loteca.strip().upper())
        return self.ratings.get(base, config.ELO_RATING_INICIAL) if base else None


def construir_modelo(conexao, jogos_base: list[dict] | None = None, nomes: dict[str, str] | None = None) -> ModeloSelecoes:
    jogos_base = jogos_base if jogos_base is not None else carregar_resultados()
    nomes = nomes if nomes is not None else carregar_nomes()
    d, h, y = amostras_de_treino(jogos_base, config.SELECOES_TREINO_DESDE, "9999-12-31")
    parametros = ajustar_curva(d, h, y)
    ratings: dict[str, float] = {}
    for jogo in jogos_base:
        atualizar_elo(ratings, jogo)
    ultimo = jogos_base[-1]["data"]

    # Campo neutro ou não nos jogos recentes da Loteca (5 anos antes do último jogo da base).
    limite = (date.fromisoformat(ultimo) - timedelta(days=5 * 365)).isoformat()
    indice = indexar_base(jogos_base)
    recentes = []
    for jogo in jogos_da_loteca_entre_selecoes(conexao):
        if jogo["data_jogo"] < limite:
            continue
        a, b = nomes.get(jogo["casa"].upper()), nomes.get(jogo["fora"].upper())
        par = casar_jogo(indice, jogos_base, a, b, jogo["data_jogo"]) if a and b else None
        if par:
            recentes.append(not par["jogo"]["neutro"])
    nao_neutro = sum(recentes) / len(recentes) if len(recentes) >= 20 else 0.5
    return ModeloSelecoes(ratings, parametros, nao_neutro, nomes, ultimo)


_CACHE_MODELO: dict = {}


def modelo_em_cache(conexao) -> ModeloSelecoes:
    """Constrói uma vez por hora por banco e arquivo (leva cerca de 1 s)."""
    import os
    import time

    chave = (
        str(config.DB_PATH),
        os.path.getmtime(config.SELECOES_BASE_CSV),
        os.path.getmtime(config.SELECOES_NOMES_CSV),
        int(time.time() // 3600),
    )
    if chave not in _CACHE_MODELO:
        _CACHE_MODELO.clear()
        _CACHE_MODELO[chave] = construir_modelo(conexao)
    return _CACHE_MODELO[chave]


# ---------------------------------------------------------------------------
# Casar jogos da Loteca com a base e testar contra o resultado real
# ---------------------------------------------------------------------------

def indexar_base(jogos: list[dict]) -> dict[tuple[str, str], list[int]]:
    indice: dict[tuple[str, str], list[int]] = {}
    for i, jogo in enumerate(jogos):
        indice.setdefault((jogo["casa"], jogo["fora"]), []).append(i)
    return indice


def casar_jogo(indice, jogos, casa_base: str, fora_base: str, data_iso: str) -> dict | None:
    """Acha na base o jogo da Loteca: os mesmos dois times e data com diferença de
    até `SELECOES_TOLERANCIA_DIAS`. Aceita a ordem trocada (a Loteca às vezes lista
    como mandante quem a base lista como visitante em campo neutro). Devolve o mais
    próximo em data, ou None."""
    alvo = date.fromisoformat(data_iso)
    melhor = None
    for a, b, trocado in ((casa_base, fora_base, False), (fora_base, casa_base, True)):
        for i in indice.get((a, b), []):
            diferenca = abs((date.fromisoformat(jogos[i]["data"]) - alvo).days)
            if diferenca <= config.SELECOES_TOLERANCIA_DIAS and (melhor is None or diferenca < melhor[0]):
                melhor = (diferenca, i, trocado)
    if melhor is None:
        return None
    return {"indice": melhor[1], "trocado": melhor[2], "jogo": jogos[melhor[1]]}


def _resultado_da_base(jogo: dict, trocado: bool) -> str:
    """Resultado do jogo da base na orientação da Loteca (1 = quem a Loteca chama de mandante)."""
    if jogo["gols_casa"] == jogo["gols_fora"]:
        return "X"
    casa_venceu = jogo["gols_casa"] > jogo["gols_fora"]
    return "1" if casa_venceu != trocado else "2"


def jogos_da_loteca_entre_selecoes(conexao) -> list[dict]:
    """Jogos apurados da Loteca em que os dois lados são seleções e há data."""
    linhas = conexao.execute(
        """
        SELECT j.id, j.concurso_numero, j.data_jogo, j.resultado, pc.nome AS casa, pf.nome AS fora
        FROM jogos j
        JOIN participantes pc ON pc.id = j.casa_id AND pc.tipo = 'selecao'
        JOIN participantes pf ON pf.id = j.fora_id AND pf.tipo = 'selecao'
        WHERE j.resultado IS NOT NULL AND j.data_jogo IS NOT NULL AND j.situacao != 'sorteio'
        ORDER BY j.data_jogo, j.id
        """
    ).fetchall()
    return [dict(linha) for linha in linhas]


def _ratings_antes_de_cada_jogo(jogos_base: list[dict], pedidos: list[tuple[str, str, str]]) -> list[tuple[float, float]]:
    """Para cada (data, time_a, time_b) devolve os ratings dos dois times usando só
    jogos da base com data ESTRITAMENTE anterior. Os pedidos precisam estar em
    ordem de data; a base é percorrida uma única vez."""
    ratings: dict[str, float] = {}
    ponteiro = 0
    saida = []
    for data, a, b in pedidos:
        while ponteiro < len(jogos_base) and jogos_base[ponteiro]["data"] < data:
            atualizar_elo(ratings, jogos_base[ponteiro])
            ponteiro += 1
        saida.append((ratings.get(a, config.ELO_RATING_INICIAL), ratings.get(b, config.ELO_RATING_INICIAL)))
    return saida


def backtest_selecoes(conexao, jogos_base: list[dict] | None = None, nomes: dict[str, str] | None = None) -> dict:
    """Mede, jogo a jogo e sem olhar o futuro, se a força por Elo acerta mais que o
    que o app faz hoje nos jogos da Loteca entre seleções depois do corte.

    Cada jogo da Loteca é casado com o da base; os ratings usam só jogos da base
    ANTES do dia daquele jogo. A curva é ajustada só com jogos anteriores ao corte.
    Compara: Elo (campo desconhecido, como seria na hora de apostar), Elo com o
    campo neutro ou não conhecido (limite superior, só para dimensionar o quanto a
    incerteza sobre o campo custa), o modelo atual do app e a frequência simples."""
    from stats.backtest import carregar_jogos, comparar_pareado, metricas, prever_walk_forward

    jogos_base = jogos_base if jogos_base is not None else carregar_resultados()
    nomes = nomes if nomes is not None else carregar_nomes()
    indice = indexar_base(jogos_base)
    corte = config.SELECOES_CORTE_TESTE

    d, h, y = amostras_de_treino(jogos_base, config.SELECOES_TREINO_DESDE, corte)
    parametros = ajustar_curva(d, h, y)

    casados, sem_nome, sem_par, discordam = [], 0, 0, 0
    for jogo in jogos_da_loteca_entre_selecoes(conexao):
        a, b = nomes.get(jogo["casa"].upper()), nomes.get(jogo["fora"].upper())
        if not a or not b:
            sem_nome += 1
            continue
        par = casar_jogo(indice, jogos_base, a, b, jogo["data_jogo"])
        if par is None:
            sem_par += 1
            continue
        if _resultado_da_base(par["jogo"], par["trocado"]) != jogo["resultado"]:
            discordam += 1
        casados.append({**jogo, "casa_base": a, "fora_base": b, **par})

    antes_do_corte = [c for c in casados if c["jogo"]["data"] < corte]
    nao_neutro = sum(1 for c in antes_do_corte if not c["jogo"]["neutro"]) / len(antes_do_corte) if antes_do_corte else 0.5

    teste = sorted((c for c in casados if c["jogo"]["data"] >= corte), key=lambda c: c["jogo"]["data"])
    ratings = _ratings_antes_de_cada_jogo(jogos_base, [(c["jogo"]["data"], c["casa_base"], c["fora_base"]) for c in teste])
    previsoes_atuais = prever_walk_forward(carregar_jogos(conexao))

    pares = {"elo": [], "elo_campo_conhecido": [], "atual": [], "frequencia": []}
    origem_atual = []
    for item, (rating_casa, rating_fora) in zip(teste, ratings):
        anterior = previsoes_atuais.get(item["id"])
        if anterior is None:
            continue
        diferenca = (rating_casa - rating_fora) / 100.0
        pares["elo"].append((probabilidades(parametros, diferenca, nao_neutro), item["resultado"]))
        if item["jogo"]["neutro"]:
            conhecido = probabilidades(parametros, diferenca, 0.0)
        elif item["trocado"]:  # mandante em campo é quem a Loteca lista como visitante
            invertido = probabilidades(parametros, -diferenca, 1.0)
            conhecido = {"1": invertido["2"], "X": invertido["X"], "2": invertido["1"]}
        else:
            conhecido = probabilidades(parametros, diferenca, 1.0)
        pares["elo_campo_conhecido"].append((conhecido, item["resultado"]))
        pares["atual"].append((anterior["atual"], item["resultado"]))
        pares["frequencia"].append((anterior["referencia"], item["resultado"]))
        origem_atual.append(anterior["origem"])

    return {
        "parametros": parametros,
        "nao_neutro_estimado": nao_neutro,
        "treino": len(y),
        "jogos_da_loteca": len(casados) + sem_nome + sem_par,
        "casados_com_a_base": len(casados),
        "sem_nome_no_mapa": sem_nome,
        "sem_par_na_base": sem_par,
        "resultado_diferente": discordam,
        "avaliados": len(pares["elo"]),
        "campo_neutro_no_teste": sum(1 for c in teste if c["jogo"]["neutro"]),
        "metricas": {nome: metricas(lista) for nome, lista in pares.items()},
        "contra_atual": comparar_pareado(pares["elo"], pares["atual"]),
        "contra_frequencia": comparar_pareado(pares["elo"], pares["frequencia"]),
        "campo_conhecido_contra_atual": comparar_pareado(pares["elo_campo_conhecido"], pares["atual"]),
        "atual_usou_frequencia_global": sum(1 for o in origem_atual if o == "frequencia_global"),
    }

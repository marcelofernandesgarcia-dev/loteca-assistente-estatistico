"""Teste B2 nos jogos da PRÓPRIA Loteca: os modelos que usam os jogos da temporada da CBF superam o
modelo atual do app e a frequência simples quando o jogo é um jogo da Loteca?

O teste anterior (`backtest_competicao`) usou os jogos da CBF. Aqui o mesmo método é aplicado aos jogos
que de fato entram nos concursos, com quatro modelos sobre EXATAMENTE os mesmos jogos:
- frequência simples de 1/X/2 da Loteca, andando no tempo (a referência do B3);
- modelo atual do app (Poisson sobre o histórico da Loteca), na versão incremental do B3;
- retrospecto: logística multinomial sobre os pontos por jogo de cada time na temporada da CBF até o
  dia do jogo, treinada só nos jogos da CBF de anos anteriores;
- Poisson da temporada (`modelo_temporada`), refeito só com os jogos da CBF disputados antes do dia.

Cobertura (por isso o funil do relatório): só entram jogos entre dois clubes das Séries A ou B da CBF na
MESMA série, em ano com treino anterior, e com pelo menos `B2_JOGOS_ANTERIORES_MINIMOS` jogos de cada
time já disputados antes do dia (jogo do próprio dia não conta). Seleções, estaduais, copas e times de
outras divisões ficam de fora porque o modelo da temporada não tem base para eles. O resultado vale para
essa fatia dos jogos, não para o concurso inteiro.
"""
import bisect

import numpy as np

import config
from stats import backtest, competicao, modelo_temporada
from stats import backtest_competicao as b2
from stats.associacao import ajustar_benjamini_hochberg

MODELOS = ("referencia", "atual", "retrospecto", "poisson")
DESCRICAO = {
    "referencia": "Frequência simples de 1/X/2 da Loteca",
    "atual": "Modelo atual do app (Poisson sobre o histórico da Loteca)",
    "retrospecto": "Retrospecto dos dois times na temporada da CBF (logística)",
    "poisson": "Poisson da temporada da CBF",
}
COMPARACOES = (
    ("atual", "referencia"), ("retrospecto", "referencia"), ("poisson", "referencia"),
    ("retrospecto", "atual"), ("poisson", "atual"), ("poisson", "retrospecto"),
)
ETAPAS_DO_FUNIL = (
    ("apurados", "Jogos apurados da Loteca (sem os decididos por sorteio)"),
    ("com_data_em_ano_testavel", "Com data, em ano com treino anterior da CBF"),
    ("dois_clubes_pareados", "Os dois times pareados com a CBF"),
    ("mesma_serie", "Os dois na mesma série da CBF no ano"),
    ("jogos_conhecidos", "Cada time com jogos suficientes antes do dia"),
    ("com_modelo_atual", "Com previsão do modelo atual (depois do aquecimento do B3)"),
)


class TemporadaPorData:
    """Jogos de uma série e ano da CBF consultáveis por data, sem olhar o futuro: tudo é "antes do dia"."""

    def __init__(self, partidas: list[dict]):
        self.partidas = sorted((p for p in partidas if p.get("data_jogo")), key=lambda p: p["data_jogo"])
        self.datas = [p["data_jogo"] for p in self.partidas]
        por_time: dict[int, tuple[list[str], list[int]]] = {}
        for p in self.partidas:
            for time, pro, contra in ((p["mandante_id"], p["gols_mandante"], p["gols_visitante"]),
                                      (p["visitante_id"], p["gols_visitante"], p["gols_mandante"])):
                datas, acumulado = por_time.setdefault(time, ([], []))
                pontos = 3 if pro > contra else 1 if pro == contra else 0
                datas.append(p["data_jogo"])
                acumulado.append((acumulado[-1] if acumulado else 0) + pontos)
        self._por_time = por_time

    def retrospecto(self, time: int, data: str) -> tuple[int, int]:
        """(pontos, jogos) do time nos jogos disputados ESTRITAMENTE antes da data."""
        if time not in self._por_time:
            return 0, 0
        datas, acumulado = self._por_time[time]
        k = bisect.bisect_left(datas, data)
        return (acumulado[k - 1] if k else 0), k

    def conhecidas(self, data: str) -> list[dict]:
        return self.partidas[: bisect.bisect_left(self.datas, data)]


def pesos_por_ano(amostra_cbf: list[dict]) -> dict[int, np.ndarray]:
    """Logística treinada, para cada ano, só nos jogos da CBF de anos anteriores (o primeiro ano só treina)."""
    indice = {"1": 0, "X": 1, "2": 2}
    pesos = {}
    for ano in sorted({o["ano"] for o in amostra_cbf})[1:]:
        treino = [o for o in amostra_cbf if o["ano"] < ano]
        X = np.column_stack([np.ones(len(treino)), [o["retro_casa"] for o in treino], [o["retro_fora"] for o in treino]])
        pesos[ano] = b2.ajustar_logistica(X, np.array([indice[o["resultado"]] for o in treino]))
    return pesos


def montar_jogos(conexao, previsoes_atual: dict[int, dict], pesos: dict[int, np.ndarray],
                 series: tuple[str, ...] | None = None) -> tuple[list[dict], dict]:
    """(jogos com a previsão dos quatro modelos, funil de cobertura). Só lê o banco.
    `previsoes_atual` = saída de `backtest.prever_walk_forward`; `pesos` = `pesos_por_ano`. Sem `series`, só as de
    pontos corridos; com `series`, só as indicadas (estudo da Série C, item B3 do plano v2)."""
    minimo = config.B2_JOGOS_ANTERIORES_MINIMOS
    funil = {chave: 0 for chave, _ in ETAPAS_DO_FUNIL}
    pareamento = {
        linha["participante_id"]: linha["cod_time"]
        for linha in conexao.execute("SELECT participante_id, cod_time FROM mapa_cbf_participante")
    }
    serie_do_time: dict[tuple[int, int], str] = {}
    temporadas: dict[tuple[str, int], TemporadaPorData] = {}
    # Só pontos corridos, a menos que `series` diga outra coisa: a Série C tem estudo à parte (item B3 do plano v2).
    filtro = competicao.so_pontos_corridos() if series is None else f"serie IN ({', '.join(repr(s) for s in series)})"
    for t in conexao.execute(f"SELECT DISTINCT serie, ano FROM cbf_partidas WHERE {filtro}"):
        partidas = competicao.carregar_partidas(conexao, t["serie"], t["ano"])
        temporadas[(t["serie"], t["ano"])] = TemporadaPorData(partidas)
        for p in partidas:
            serie_do_time[(t["ano"], p["mandante_id"])] = t["serie"]
            serie_do_time[(t["ano"], p["visitante_id"])] = t["serie"]

    jogos, cache_forcas = [], {}
    for jogo in backtest.carregar_jogos(conexao):
        funil["apurados"] += 1
        data = jogo.get("data_jogo")
        ano = int(data[:4]) if data and len(data) >= 4 and data[:4].isdigit() else None
        if ano not in pesos:
            continue
        funil["com_data_em_ano_testavel"] += 1
        cod_casa, cod_fora = pareamento.get(jogo["casa_id"]), pareamento.get(jogo["fora_id"])
        if cod_casa is None or cod_fora is None or cod_casa == cod_fora:
            continue
        funil["dois_clubes_pareados"] += 1
        serie = serie_do_time.get((ano, cod_casa))
        if serie is None or serie != serie_do_time.get((ano, cod_fora)):
            continue
        funil["mesma_serie"] += 1
        temporada = temporadas[(serie, ano)]
        (pontos_casa, jogos_casa), (pontos_fora, jogos_fora) = temporada.retrospecto(cod_casa, data), temporada.retrospecto(cod_fora, data)
        if jogos_casa < minimo or jogos_fora < minimo:
            continue
        chave = (serie, ano, data)
        if chave not in cache_forcas:
            cache_forcas[chave] = modelo_temporada.forcas_da_serie(temporada.conhecidas(data))
        analise = modelo_temporada.analisar_confronto(cache_forcas[chave], cod_casa, cod_fora) if cache_forcas[chave] else None
        if analise is None:
            continue
        funil["jogos_conhecidos"] += 1
        atual = previsoes_atual.get(jogo["id"])
        if atual is None:
            continue
        funil["com_modelo_atual"] += 1
        X = np.array([[1.0, pontos_casa / jogos_casa, pontos_fora / jogos_fora]])
        jogos.append(
            {
                "id": jogo["id"], "concurso": jogo["concurso_numero"], "ano": ano, "serie": serie,
                "cluster": f"concurso-{jogo['concurso_numero']}", "resultado": jogo["resultado"],
                "previsoes": {
                    "referencia": atual["referencia"],
                    "atual": atual["atual"],
                    "retrospecto": b2._como_percentuais(b2.probabilidades_logistica(X, pesos[ano])[0]),
                    "poisson": b2._como_percentuais((analise["p_casa"], analise["p_empate"], analise["p_fora"])),
                },
            }
        )
    return jogos, funil


def perda_por_serie(jogos: list[dict]) -> dict[str, dict]:
    """{serie: {'n', modelo: perda logarítmica}} -- o desempenho separado por competição (item B2 do plano v2)."""
    saida = {}
    for serie in sorted({o["serie"] for o in jogos}):
        da_serie = [o for o in jogos if o["serie"] == serie]
        saida[serie] = {"n": len(da_serie), **{
            m: backtest.metricas([(o["previsoes"][m], o["resultado"]) for o in da_serie])["perda_log"] for m in MODELOS
        }}
    return saida


def medir_no_banco(conexao) -> tuple[dict | None, dict, dict]:
    """(resumo, funil, perda por série) do estudo nos jogos da Loteca, com o banco de agora. Só leitura; cerca
    de 1 minuto no banco real."""
    jogos, funil = montar_jogos(conexao, backtest.prever_walk_forward(backtest.carregar_jogos(conexao)),
                                pesos_por_ano(b2.carregar_amostra(conexao)))
    return resumir(jogos), funil, perda_por_serie(jogos)


def resumir(jogos: list[dict]) -> dict:
    """Métricas por modelo, comparações pareadas (ganho positivo = o primeiro modelo é melhor) com valor q
    entre as seis comparações, e a perda logarítmica de cada modelo por ano (só descritivo). None sem jogos."""
    if not jogos:
        return None
    metricas = {m: backtest.metricas([(o["previsoes"][m], o["resultado"]) for o in jogos]) for m in MODELOS}
    clusters = np.array([o["cluster"] for o in jogos])
    comparacoes = []
    for indice, (a, b) in enumerate(COMPARACOES):
        ganho_log = np.array([backtest.perda_log(o["previsoes"][b], o["resultado"]) - backtest.perda_log(o["previsoes"][a], o["resultado"]) for o in jogos])
        ganho_brier = np.array([backtest.brier(o["previsoes"][b], o["resultado"]) - backtest.brier(o["previsoes"][a], o["resultado"]) for o in jogos])
        comparacoes.append(
            {
                "modelo": a, "contra": b,
                "perda_log": b2._bootstrap_por_cluster(ganho_log, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + 100 + indice),
                "brier": b2._bootstrap_por_cluster(ganho_brier, clusters, config.B2_REPETICOES_BOOTSTRAP, config.B2_SEMENTE + 200 + indice),
            }
        )
    for c, q in zip(comparacoes, ajustar_benjamini_hochberg([c["perda_log"]["p"] for c in comparacoes])):
        c["q"] = q
        if q < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA:
            c["conclusao"] = "melhor"
        elif c["perda_log"]["ic_superior"] < 0:
            c["conclusao"] = "pior"
        else:
            c["conclusao"] = "sem diferença perceptível"
    por_ano = {}
    for ano in sorted({o["ano"] for o in jogos}):
        do_ano = [o for o in jogos if o["ano"] == ano]
        por_ano[ano] = {"n": len(do_ano), **{m: backtest.metricas([(o["previsoes"][m], o["resultado"]) for o in do_ano])["perda_log"] for m in MODELOS}}
    return {"n": len(jogos), "metricas": metricas, "comparacoes": comparacoes, "por_ano": por_ano}

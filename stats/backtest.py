"""Backtest 'andando no tempo' (walk-forward) dos percentuais.

Cada concurso é previsto usando SÓ os jogos de concursos anteriores. Compara o
modelo atual (Poisson sobre o histórico da Loteca, com queda para a frequência
global em amostra pequena) com referências simples, para responder com dado:
o percentual acerta mais do que a frequência histórica de 1/X/2?

A versão do modelo atual aqui é INCREMENTAL (mantém somas por time em vez de
consultar o banco a cada jogo) e reproduz `stats.percentual.percentual_historico`
número a número -- há teste que confere.
"""
import math
from collections import defaultdict

from stats.percentual import JOGOS_MINIMOS_PARA_FORCA_PROPRIA

RESULTADOS = ("1", "X", "2")
MAX_GOLS = 8
LIMITE_LOG = 1e-6


def _poisson(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * lam**k / math.factorial(k)


def carregar_jogos(conexao) -> list[dict]:
    """Jogos apurados (sem os decididos por sorteio, que não refletem o campo),
    em ordem cronológica de concurso."""
    linhas = conexao.execute(
        """
        SELECT id, concurso_numero, num_jogo, data_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado
        FROM jogos
        WHERE resultado IS NOT NULL AND gols_casa IS NOT NULL AND gols_fora IS NOT NULL AND situacao != 'sorteio'
        ORDER BY concurso_numero, num_jogo
        """
    ).fetchall()
    return [dict(linha) for linha in linhas]


class ModeloHistorico:
    """Estado acumulado do modelo atual; `prever` usa só o que foi `aprender`."""

    def __init__(self):
        self.gols_casa_marcados = defaultdict(int)
        self.gols_casa_sofridos = defaultdict(int)
        self.jogos_casa = defaultdict(int)
        self.gols_fora_marcados = defaultdict(int)
        self.gols_fora_sofridos = defaultdict(int)
        self.jogos_fora = defaultdict(int)
        self.total_gols = 0
        self.total_jogos = 0
        self.contagem = {"1": 0, "X": 0, "2": 0}

    def aprender(self, jogo: dict) -> None:
        casa, fora = jogo["casa_id"], jogo["fora_id"]
        self.gols_casa_marcados[casa] += jogo["gols_casa"]
        self.gols_casa_sofridos[casa] += jogo["gols_fora"]
        self.jogos_casa[casa] += 1
        self.gols_fora_marcados[fora] += jogo["gols_fora"]
        self.gols_fora_sofridos[fora] += jogo["gols_casa"]
        self.jogos_fora[fora] += 1
        self.total_gols += jogo["gols_casa"] + jogo["gols_fora"]
        self.total_jogos += 1
        self.contagem[jogo["resultado"]] += 1

    def frequencia_global(self) -> dict | None:
        if self.total_jogos == 0:
            return None
        return {r: 100.0 * self.contagem[r] / self.total_jogos for r in RESULTADOS}

    def prever(self, casa: int, fora: int) -> dict | None:
        """{'percentuais': {'1','X','2'} em %, 'origem': 'poisson'|'frequencia_global'}."""
        frequencia = self.frequencia_global()
        if frequencia is None:
            return None
        n_casa, n_fora = self.jogos_casa[casa], self.jogos_fora[fora]
        media_geral = self.total_gols / (2 * self.total_jogos) or 1.2
        if min(n_casa, n_fora) < JOGOS_MINIMOS_PARA_FORCA_PROPRIA or media_geral <= 0:
            return {"percentuais": frequencia, "origem": "frequencia_global"}
        ataque_casa = self.gols_casa_marcados[casa] / n_casa
        defesa_casa = self.gols_casa_sofridos[casa] / n_casa
        ataque_fora = self.gols_fora_marcados[fora] / n_fora
        defesa_fora = self.gols_fora_sofridos[fora] / n_fora
        lambda_casa = ataque_casa * defesa_fora / media_geral
        lambda_fora = ataque_fora * defesa_casa / media_geral
        vence_casa = empate = vence_fora = 0.0
        for gc in range(MAX_GOLS + 1):
            for gf in range(MAX_GOLS + 1):
                p = _poisson(gc, lambda_casa) * _poisson(gf, lambda_fora)
                if gc > gf:
                    vence_casa += p
                elif gc == gf:
                    empate += p
                else:
                    vence_fora += p
        total = vence_casa + empate + vence_fora
        if total == 0:
            return {"percentuais": frequencia, "origem": "frequencia_global"}
        return {
            "percentuais": {"1": 100 * vence_casa / total, "X": 100 * empate / total, "2": 100 * vence_fora / total},
            "origem": "poisson",
        }


def prever_walk_forward(jogos: list[dict], aquecimento_concursos: int = 50) -> dict[int, dict]:
    """{id_do_jogo: {'atual': {...}, 'referencia': {...}, 'origem': str, 'concurso': n}} para os
    jogos de concursos depois do aquecimento. Cada concurso é previsto só com o que veio antes."""
    modelo = ModeloHistorico()
    previsoes = {}
    concursos = []
    for jogo in jogos:
        if not concursos or concursos[-1][0] != jogo["concurso_numero"]:
            concursos.append((jogo["concurso_numero"], []))
        concursos[-1][1].append(jogo)
    for indice, (numero, lote) in enumerate(concursos):
        if indice >= aquecimento_concursos:
            for jogo in lote:
                previsao = modelo.prever(jogo["casa_id"], jogo["fora_id"])
                if previsao:
                    previsoes[jogo["id"]] = {
                        "atual": previsao["percentuais"],
                        "referencia": modelo.frequencia_global(),
                        "origem": previsao["origem"],
                        "concurso": numero,
                    }
        for jogo in lote:
            modelo.aprender(jogo)
    return previsoes


def escolha(percentuais: dict) -> str:
    return max(RESULTADOS, key=lambda r: (percentuais[r], -RESULTADOS.index(r)))


def brier(percentuais: dict, resultado: str) -> float:
    return sum((percentuais[r] / 100.0 - (1.0 if r == resultado else 0.0)) ** 2 for r in RESULTADOS)


def perda_log(percentuais: dict, resultado: str) -> float:
    return -math.log(max(percentuais[resultado] / 100.0, LIMITE_LOG))


def metricas(pares: list[tuple[dict, str]]) -> dict:
    """`pares`: [(percentuais, resultado_real)]. Acurácia do favorito, Brier (0 = perfeito,
    0,667 = palpite uniforme), perda logarítmica (menor é melhor) e média da probabilidade
    dada ao que de fato aconteceu."""
    n = len(pares)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "acuracia": 100.0 * sum(1 for p, r in pares if escolha(p) == r) / n,
        "brier": sum(brier(p, r) for p, r in pares) / n,
        "perda_log": sum(perda_log(p, r) for p, r in pares) / n,
        "prob_media_do_real": sum(p[r] for p, r in pares) / n,
    }


def comparar_pareado(pares_modelo: list[tuple[dict, str]], pares_referencia: list[tuple[dict, str]]) -> dict:
    """Diferença média da perda logarítmica (modelo - referência) jogo a jogo, com erro-padrão.
    Negativa = o modelo dá mais probabilidade ao que aconteceu. Veredito com 95% de confiança."""
    diferencas = [perda_log(pm, rm) - perda_log(pr, rr) for (pm, rm), (pr, rr) in zip(pares_modelo, pares_referencia)]
    n = len(diferencas)
    if n < 2:
        return {"n": n, "diferenca": None, "erro_padrao": None, "veredito": "amostra insuficiente"}
    media = sum(diferencas) / n
    variancia = sum((d - media) ** 2 for d in diferencas) / (n - 1)
    erro = math.sqrt(variancia / n)
    if media + 1.96 * erro < 0:
        veredito = "melhor que a referência"
    elif media - 1.96 * erro > 0:
        veredito = "pior que a referência"
    else:
        veredito = "sem diferença perceptível"
    return {"n": n, "diferenca": media, "erro_padrao": erro, "veredito": veredito}


def calibracao(pares: list[tuple[dict, str]], largura: float = 0.1) -> list[dict]:
    """Para cada faixa de probabilidade prevista (de cada resultado de cada jogo),
    quanto de fato aconteceu. Um modelo calibrado tem previsto ≈ observado."""
    faixas = int(round(1 / largura))
    soma_prevista, acertos, contagem = [0.0] * faixas, [0] * faixas, [0] * faixas
    for percentuais, real in pares:
        for r in RESULTADOS:
            p = percentuais[r] / 100.0
            i = min(int(p / largura), faixas - 1)
            soma_prevista[i] += p
            contagem[i] += 1
            acertos[i] += 1 if r == real else 0
    return [
        {
            "faixa": f"{i * largura * 100:.0f}% a {(i + 1) * largura * 100:.0f}%",
            "n": contagem[i],
            "previsto": 100 * soma_prevista[i] / contagem[i],
            "observado": 100 * acertos[i] / contagem[i],
        }
        for i in range(faixas)
        if contagem[i]
    ]


def acertos_por_concurso(jogos_por_id: dict[int, dict], previsoes: dict[int, dict]) -> dict:
    """Média de acertos (de 14) por concurso completo: sempre mandante; favorito do
    modelo atual; favorito + único duplo/triplo da sugestão do app. Só concursos com
    os 14 jogos avaliáveis."""
    from stats.bilhete import montar_bilhete

    por_concurso = defaultdict(list)
    for id_jogo, previsao in previsoes.items():
        por_concurso[previsao["concurso"]].append((jogos_por_id[id_jogo], previsao))
    linhas = []
    for concurso, itens in sorted(por_concurso.items()):
        if len(itens) != 14:
            continue
        itens.sort(key=lambda x: x[0]["num_jogo"])
        reais = [j["resultado"] for j, _ in itens]
        modelo = [escolha(p["atual"]) for _, p in itens]
        bilhete = montar_bilhete([p["atual"] for _, p in itens])
        linhas.append(
            {
                "concurso": concurso,
                "sempre_mandante": sum(1 for r in reais if r == "1"),
                "favorito_do_modelo": sum(1 for m, r in zip(modelo, reais) if m == r),
                "com_cobertura": sum(1 for cols, r in zip(bilhete["marcacoes"], reais) if r in cols),
                "custo_com_cobertura": bilhete["custo"],
            }
        )
    n = len(linhas)
    if n == 0:
        return {"concursos": 0}

    def media(chave):
        return sum(l[chave] for l in linhas) / n

    def com_pelo_menos(chave, minimo):
        return 100.0 * sum(1 for l in linhas if l[chave] >= minimo) / n

    return {
        "concursos": n,
        "media": {c: media(c) for c in ("sempre_mandante", "favorito_do_modelo", "com_cobertura")},
        "pelo_menos_10": {c: com_pelo_menos(c, 10) for c in ("sempre_mandante", "favorito_do_modelo", "com_cobertura")},
        "pelo_menos_11": {c: com_pelo_menos(c, 11) for c in ("sempre_mandante", "favorito_do_modelo", "com_cobertura")},
        "custo_medio_com_cobertura": media("custo_com_cobertura"),
    }


def executar_backtest(conexao, aquecimento_concursos: int = 50) -> dict:
    """Roda o backtest do modelo atual contra a frequência global e devolve tudo o que a
    tela de confiabilidade mostra."""
    jogos = carregar_jogos(conexao)
    por_id = {j["id"]: j for j in jogos}
    previsoes = prever_walk_forward(jogos, aquecimento_concursos)
    ids = sorted(previsoes)
    pares_modelo = [(previsoes[i]["atual"], por_id[i]["resultado"]) for i in ids]
    pares_ref = [(previsoes[i]["referencia"], por_id[i]["resultado"]) for i in ids]
    pares_poisson = [(previsoes[i]["atual"], por_id[i]["resultado"]) for i in ids if previsoes[i]["origem"] == "poisson"]
    pares_poisson_ref = [(previsoes[i]["referencia"], por_id[i]["resultado"]) for i in ids if previsoes[i]["origem"] == "poisson"]
    sempre_um = [({"1": 100.0, "X": 0.0, "2": 0.0}, por_id[i]["resultado"]) for i in ids]
    return {
        "jogos_avaliados": len(ids),
        "concursos_avaliados": len({previsoes[i]["concurso"] for i in ids}),
        "aquecimento_concursos": aquecimento_concursos,
        "primeiro_concurso": min((previsoes[i]["concurso"] for i in ids), default=None),
        "ultimo_concurso": max((previsoes[i]["concurso"] for i in ids), default=None),
        "jogos_com_forca_propria": len(pares_poisson),
        "modelos": {
            "atual": metricas(pares_modelo),
            "frequencia_global": metricas(pares_ref),
            "sempre_mandante": {"n": len(sempre_um), "acuracia": metricas(sempre_um).get("acuracia")},
        },
        "comparacao_atual_vs_global": comparar_pareado(pares_modelo, pares_ref),
        "so_jogos_com_forca_propria": {
            "atual": metricas(pares_poisson),
            "frequencia_global": metricas(pares_poisson_ref),
            "comparacao": comparar_pareado(pares_poisson, pares_poisson_ref),
        },
        "calibracao_atual": calibracao(pares_modelo),
        "bilhetes": acertos_por_concurso(por_id, previsoes),
    }

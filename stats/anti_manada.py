"""Estudo anti-manada (Q7): quando o resultado do concurso se afasta do que a maioria marca, há menos
ganhadores de 14 acertos e, portanto, prêmio menos dividido?

A ideia vem do estudo de Soto Costa (1980, formato antigo de 13 jogos) e de uma primeira conta do
projeto (correlação de -0,13 sobre todos os concursos, sem descontar a arrecadação nem a época). Aqui:
- o desfecho é o número de ganhadores de 14 por R$ 1 milhão arrecadado, para descontar o tamanho do
  concurso (mais apostas, mais ganhadores);
- a comparação é feita DENTRO de cada ano (correlação de Spearman estratificada), porque o
  comportamento dos apostadores e a arrecadação mudam ao longo do tempo e o efeito de época pode
  fabricar correlação;
- valor p por permutação dentro do ano (válido: o resultado dos jogos não depende de como se aposta);
  intervalo de 95% por reamostragem de concursos (com os postos fixos); valor q de Benjamini-Hochberg
  entre as exposições testadas.

Exposições: jogos fora da coluna 1 (empate ou vitória do visitante), empates e vitórias do visitante.
Só entram concursos com 14 jogos, todos decididos em campo (concurso com jogo decidido por sorteio
fica fora: o resultado não saiu do jogo), com arrecadação informada e ganhadores de 14 informados.

Isto descreve o passado; não diz o que vai acontecer num concurso futuro nem recomenda marcar zebra.
"""
import numpy as np

import config
from stats.associacao import ajustar_benjamini_hochberg

EXPOSICOES = (
    ("fora_da_coluna_1", "Jogos fora da coluna 1 (empate ou vitória do visitante)"),
    ("empates", "Empates"),
    ("visitantes", "Vitórias do visitante"),
)


def carregar_concursos(conexao) -> tuple[list[dict], dict]:
    """(concursos úteis, contagem do que ficou de fora e por quê). Só lê o banco."""
    linhas = conexao.execute(
        """
        SELECT c.numero, c.data_apuracao, c.valor_arrecadado,
               p.ganhadores AS ganhadores_14, p.valor_premio AS premio_14
        FROM concursos c
        LEFT JOIN premiacoes p ON p.concurso_numero = c.numero AND p.faixa = 1 AND p.pontos = 14
        """
    ).fetchall()
    jogos = {}
    for j in conexao.execute("SELECT concurso_numero, resultado, situacao FROM jogos"):
        jogos.setdefault(j["concurso_numero"], []).append((j["resultado"], j["situacao"]))

    uteis = []
    fora = {"sem_14_jogos_apurados": 0, "jogo_decidido_por_sorteio": 0, "sem_arrecadacao": 0, "sem_ganhadores_14": 0}
    for c in linhas:
        resultados = jogos.get(c["numero"], [])
        if len(resultados) != 14 or any(r not in ("1", "X", "2") for r, _ in resultados):
            fora["sem_14_jogos_apurados"] += 1
            continue
        if any(s == "sorteio" for _, s in resultados):
            fora["jogo_decidido_por_sorteio"] += 1
            continue
        if not c["valor_arrecadado"] or c["valor_arrecadado"] <= 0 or not c["data_apuracao"]:
            fora["sem_arrecadacao"] += 1
            continue
        if c["ganhadores_14"] is None:
            fora["sem_ganhadores_14"] += 1
            continue
        contagem = {r: sum(1 for x, _ in resultados if x == r) for r in ("1", "X", "2")}
        uteis.append(
            {
                "numero": c["numero"], "ano": int(c["data_apuracao"][:4]),
                "arrecadacao": c["valor_arrecadado"], "ganhadores_14": c["ganhadores_14"], "premio_14": c["premio_14"],
                "fora_da_coluna_1": 14 - contagem["1"], "empates": contagem["X"], "visitantes": contagem["2"],
                "ganhadores_por_milhao": c["ganhadores_14"] / (c["valor_arrecadado"] / 1e6),
            }
        )
    return uteis, fora


def conta_anterior(conexao) -> dict | None:
    """Reproduz a primeira conta do projeto: todos os concursos com 14 jogos apurados e a faixa de 14
    informada, sem excluir sorteio nem descontar arrecadação, número BRUTO de ganhadores. Devolve a
    correlação de Pearson (a conta antiga, de -0,13) e a de Spearman sobre os mesmos concursos."""
    linhas = conexao.execute(
        """
        SELECT p.ganhadores AS ganhadores,
               SUM(CASE WHEN j.resultado IN ('X', '2') THEN 1 ELSE 0 END) AS fora_da_coluna_1,
               COUNT(j.id) AS jogos, SUM(CASE WHEN j.resultado IN ('1', 'X', '2') THEN 1 ELSE 0 END) AS apurados
        FROM concursos c
        JOIN premiacoes p ON p.concurso_numero = c.numero AND p.faixa = 1 AND p.pontos = 14
        JOIN jogos j ON j.concurso_numero = c.numero
        WHERE p.ganhadores IS NOT NULL
        GROUP BY c.numero
        """
    ).fetchall()
    validas = [l for l in linhas if l["jogos"] == 14 and l["apurados"] == 14]
    if len(validas) < 3:
        return None
    x = np.array([l["fora_da_coluna_1"] for l in validas], float)
    y = np.array([l["ganhadores"] for l in validas], float)
    if x.std() == 0 or y.std() == 0:
        return None
    return {"n": len(validas), "pearson": float(np.corrcoef(x, y)[0, 1]), "spearman": correlacao_simples(x, y)}


def postos_medios(valores: np.ndarray) -> np.ndarray:
    """Posto de cada valor (1 = menor), com a média dos postos nos empates."""
    _, inverso, contagens = np.unique(valores, return_inverse=True, return_counts=True)
    acumulado = np.cumsum(contagens)
    return (acumulado - (contagens - 1) / 2.0)[inverso]


def correlacao_estratificada(
    x: list[float], y: list[float], estrato: list[int], permutacoes: int, repeticoes: int, semente: int, minimo_por_estrato: int
) -> dict:
    """Correlação de Spearman estratificada: postos dentro de cada estrato, centrados, e correlação de
    Pearson entre eles no conjunto. Valor p bilateral por permutação dentro do estrato e intervalo de
    95% por reamostragem de observações (postos fixos)."""
    x, y, estrato = np.asarray(x, float), np.asarray(y, float), np.asarray(estrato)
    manter = np.isin(estrato, [e for e in np.unique(estrato) if (estrato == e).sum() >= minimo_por_estrato])
    x, y, estrato = x[manter], y[manter], estrato[manter]
    ordem = np.argsort(estrato, kind="stable")
    x, y, estrato = x[ordem], y[ordem], estrato[ordem]
    n = len(x)
    if n < 3 or len(np.unique(estrato)) < 1:
        return {"n": n, "rho": None, "ic_inferior": None, "ic_superior": None, "p": None}

    rx, ry = np.zeros(n), np.zeros(n)
    for e in np.unique(estrato):
        marca = estrato == e
        rx[marca] = postos_medios(x[marca]) - (marca.sum() + 1) / 2.0
        ry[marca] = postos_medios(y[marca]) - (marca.sum() + 1) / 2.0
    denominador = np.sqrt((rx**2).sum() * (ry**2).sum())
    if denominador == 0:
        return {"n": n, "rho": None, "ic_inferior": None, "ic_superior": None, "p": None}
    rho = float((rx * ry).sum() / denominador)

    rng = np.random.default_rng(semente)
    _, estrato_idx = np.unique(estrato, return_inverse=True)
    maiores, feitas = 0, 0
    while feitas < permutacoes:
        lote = min(250, permutacoes - feitas)
        embaralhado = np.argsort(estrato_idx + rng.random((lote, n)), axis=1)
        estatisticas = (rx[embaralhado] @ ry) / denominador
        maiores += int((np.abs(estatisticas) >= abs(rho) - 1e-12).sum())
        feitas += lote
    p = (1 + maiores) / (1 + permutacoes)

    sorteio = rng.integers(0, n, size=(repeticoes, n))
    rx_s, ry_s = rx[sorteio], ry[sorteio]
    denominador_s = np.sqrt((rx_s**2).sum(axis=1) * (ry_s**2).sum(axis=1))
    valido = denominador_s > 0
    rhos = (rx_s * ry_s).sum(axis=1)[valido] / denominador_s[valido]
    ic = np.percentile(rhos, [2.5, 97.5])
    return {"n": n, "rho": rho, "ic_inferior": float(ic[0]), "ic_superior": float(ic[1]), "p": p}


def correlacao_simples(x: list[float], y: list[float]) -> float | None:
    """Spearman sem estratificar nem descontar nada: só para mostrar por que a conta ingênua engana."""
    if len(x) < 3:
        return None
    rx, ry = postos_medios(np.asarray(x, float)), postos_medios(np.asarray(y, float))
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def estudar(concursos: list[dict]) -> list[dict]:
    """Uma correlação estratificada por exposição, com valor q e conclusão em linguagem simples."""
    resultados = []
    for indice, (chave, descricao) in enumerate(EXPOSICOES):
        r = correlacao_estratificada(
            [c[chave] for c in concursos], [c["ganhadores_por_milhao"] for c in concursos], [c["ano"] for c in concursos],
            config.Q7_PERMUTACOES, config.Q7_REPETICOES_BOOTSTRAP, config.Q7_SEMENTE + indice,
            config.Q7_CONCURSOS_MINIMOS_POR_ANO,
        )
        resultados.append({"exposicao": chave, "descricao": descricao, "q": None, **r})
    testados = [r for r in resultados if r["p"] is not None]
    for r, q in zip(testados, ajustar_benjamini_hochberg([r["p"] for r in testados])):
        r["q"] = q
    for r in resultados:
        if r["p"] is None:
            r["conclusao"] = "amostra insuficiente"
        elif r["q"] < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA:
            r["conclusao"] = "associação detectada (" + ("positiva" if r["rho"] > 0 else "negativa") + ")"
        else:
            r["conclusao"] = "sem diferença perceptível"
    return resultados


def tabela_por_faixa(concursos: list[dict]) -> list[dict]:
    """Descritivo: por faixa de jogos fora da coluna 1, quantos concursos, média de ganhadores de 14 por
    milhão arrecadado, percentual sem ganhador de 14 e prêmio mediano por ganhador (só onde houve)."""
    linhas = []
    for minimo, maximo in config.Q7_FAIXAS_DE_JOGOS_FORA_DA_COLUNA_1:
        grupo = [c for c in concursos if minimo <= c["fora_da_coluna_1"] <= maximo]
        if not grupo:
            continue
        premios = [c["premio_14"] for c in grupo if c["ganhadores_14"] and c["premio_14"]]
        linhas.append(
            {
                "faixa": f"{minimo} a {maximo}", "concursos": len(grupo),
                "ganhadores_por_milhao": float(np.mean([c["ganhadores_por_milhao"] for c in grupo])),
                "sem_ganhador_14": 100.0 * sum(1 for c in grupo if c["ganhadores_14"] == 0) / len(grupo),
                "premio_mediano": float(np.median(premios)) if premios else None,
            }
        )
    return linhas

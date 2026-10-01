#!/usr/bin/env python3
"""Roda o teste B2 (modelos de 1/X/2 por competição, andando no tempo) sobre o banco real, SÓ EM
LEITURA, e grava o relatório em docs/. Demora alguns minutos: o Poisson da temporada é refeito a
cada rodada. Parâmetros em config.B2_*; resultado reprodutível.

Uso: python scripts/backtest_competicao.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import backtest_competicao as b2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backtest_competicao")


def _num(valor, casas=4, sinal=False):
    texto = f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}"
    return texto.replace(".", ",")


def _texto_p(valor):
    return "<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ",")


def montar_relatorio(resumo: dict, resumos_por_serie: dict[str, dict], anos: list[int]) -> str:
    linhas = [
        f"# B2 — Teste dos modelos de 1/X/2 por competição ({dt.date.today():%d/%m/%Y})",
        "",
        "> Este teste só mede. Nenhum percentual exibido no app foi alterado, e trocar o modelo exige decisão do usuário.",
        "",
        "## Pergunta",
        "Um modelo que usa os jogos da temporada (CBF) prevê o resultado melhor do que a frequência simples de 1, X e 2? "
        "Esta é a condição que o roteiro (B2) impôs antes de qualquer mudança no modelo.",
        "",
        "## Base e método",
        f"- **{resumo['n']}** jogos das Séries A e B da CBF, testados de {anos[0]} a {anos[-1]}; cada ano é testado com treino só nos anos anteriores. "
        f"Cada time precisa ter pelo menos {config.B2_JOGOS_ANTERIORES_MINIMOS} jogos já conhecidos na temporada; todos os modelos usam exatamente os mesmos jogos.",
        "- Sem olhar o futuro: para cada rodada, só contam jogos de rodada anterior **e** disputados antes do primeiro jogo da rodada (jogo adiado não conta antes de acontecer).",
        "- **Frequência simples:** frequência de 1, X e 2 nos anos anteriores. **Retrospecto:** regressão logística multinomial com os pontos por jogo dos dois times na temporada. "
        "**Poisson da temporada:** `modelo_temporada` (ataque e defesa de cada time, com prior), refeito a cada rodada.",
        "- Métricas (menor é melhor): perda logarítmica e Brier. Acerto do favorito também é mostrado. Comparação pareada jogo a jogo; "
        f"intervalo de 95% e valor p unilateral por reamostragem de rodadas ({config.B2_REPETICOES_BOOTSTRAP} repetições); "
        "valor q de Benjamini-Hochberg entre as três comparações (critério: perda logarítmica, como no B3).",
        "",
        "## Desempenho de cada modelo",
        "",
        "| Modelo | Jogos | Acerto do favorito | Brier | Perda logarítmica |",
        "|---|---:|---:|---:|---:|",
    ]
    for modelo in b2.MODELOS:
        m = resumo["metricas"][modelo]
        linhas.append(
            f"| {b2.DESCRICAO[modelo]} | {m['n']} | {_num(m['acuracia'], 1)}% | {_num(m['brier'])} | {_num(m['perda_log'])} |"
        )
    linhas += [
        "",
        "## Comparações pareadas (ganho positivo = o primeiro modelo é melhor)",
        "",
        "| Comparação | Ganho em perda logarítmica | IC 95% | p | q | Ganho em Brier | IC 95% | Conclusão |",
        "|---|---:|---|---:|---:|---:|---|---|",
    ]
    for c in resumo["comparacoes"]:
        pl, br = c["perda_log"], c["brier"]
        linhas.append(
            f"| {b2.DESCRICAO[c['modelo']]} contra {b2.DESCRICAO[c['contra']][0].lower() + b2.DESCRICAO[c['contra']][1:]} | {_num(pl['media'], 4, True)} | "
            f"{_num(pl['ic_inferior'], 4, True)} a {_num(pl['ic_superior'], 4, True)} | {_texto_p(pl['p'])} | {_texto_p(c['q'])} | "
            f"{_num(br['media'], 4, True)} | {_num(br['ic_inferior'], 4, True)} a {_num(br['ic_superior'], 4, True)} | {c['conclusao']} |"
        )
    linhas += ["", "## Por série (mesmo método, só descritivo)", "", "| Série | Jogos | Modelo | Acerto | Brier | Perda logarítmica |", "|---|---:|---|---:|---:|---:|"]
    for serie, r in resumos_por_serie.items():
        for modelo in b2.MODELOS:
            m = r["metricas"][modelo]
            linhas.append(f"| {serie} | {m['n']} | {b2.DESCRICAO[modelo]} | {_num(m['acuracia'], 1)}% | {_num(m['brier'])} | {_num(m['perda_log'])} |")
    linhas += [
        "",
        "## Como ler",
        "- \"Melhor\" significa mais probabilidade dada ao que de fato aconteceu, fora da amostra, com q < "
        f"{str(config.ASSOCIACAO_NIVEL_SIGNIFICANCIA).replace('.', ',')}. \"Sem diferença perceptível\" não prova igualdade: a amostra pode não detectar ganho pequeno.",
        "- O acerto do favorito não é o critério: o que importa é a qualidade das probabilidades (perda logarítmica e Brier).",
        "- Os jogos de uma mesma rodada compartilham contexto; por isso o intervalo reamostra rodadas, não jogos. Times se repetem entre rodadas, o que o intervalo não corrige por completo.",
        "- Isto vale para os jogos da CBF. O percentual da Loteca também depende de seleções e de times fora das Séries A e B, que este teste não cobre.",
        "",
        "## Reprodução",
        "`.venv\\Scripts\\python scripts\\backtest_competicao.py` (só lê `loteca.db`; semente em `config.B2_SEMENTE`).",
    ]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "docs" / f"b2-modelo-por-competicao-{dt.date.today():%d-%m-%Y}.md"
    )
    conexao = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        amostra = b2.carregar_amostra(conexao)
    finally:
        conexao.close()
    logger.info("Amostra: %s jogos elegíveis", len(amostra))
    previstos = b2.prever(amostra)
    anos = sorted({o["ano"] for o in previstos})
    logger.info("Jogos testados: %s (%s a %s)", len(previstos), anos[0], anos[-1])
    resumo = b2.resumir(previstos)
    por_serie = {s: b2.resumir([o for o in previstos if o["serie"] == s]) for s in sorted({o["serie"] for o in previstos})}
    destino.write_text(montar_relatorio(resumo, por_serie, anos), encoding="utf-8")
    for c in resumo["comparacoes"]:
        logger.info("%s contra %s: ganho em perda log %s, q %s, %s", c["modelo"], c["contra"],
                    _num(c["perda_log"]["media"], 4, True), _texto_p(c["q"]), c["conclusao"])
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

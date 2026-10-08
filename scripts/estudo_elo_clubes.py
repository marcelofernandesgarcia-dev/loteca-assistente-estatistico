#!/usr/bin/env python3
"""Estudo formal do Elo de clubes (sugestão S2). Roda sobre o banco real, SÓ EM LEITURA, e grava o relatório.
Ver stats/estudo_elo_clubes.py.

Uso: python scripts/estudo_elo_clubes.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import estudo_elo_clubes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_elo_clubes")

NOMES = {
    "frequencia": "Frequência simples de 1/X/2",
    "modelo_atual": "Modelo atual (Poisson histórico, calibrado)",
    "elo": "Elo de clubes",
    "elo_calibrado": "Elo de clubes com a calibração do app",
    "sem_base_modelo_atual": "Só jogos sem base própria: modelo atual",
    "sem_base_elo": "Só jogos sem base própria: Elo de clubes",
    "temporada": "Temporada da CBF (em uso desde 07/10/2026)",
    "media": "Média: temporada da CBF + Elo de clubes",
}


def _n(v, casas=4, sinal=False):
    return (f"{v:+.{casas}f}" if sinal else f"{v:.{casas}f}").replace(".", ",")


def _tabela(titulo: str, grupo: dict) -> list[str]:
    linhas = [f"### {titulo}", "| Modelo | Jogos | Perda logarítmica | RPS | Acerto do favorito |", "|---|---:|---:|---:|---:|"]
    linhas += [f"| {NOMES[k]} | {m['n']} | {_n(m['perda_log'])} | {_n(m['rps'])} | {_n(m['acerto'], 1)}% |" for k, m in grupo.items()]
    return linhas + [""]


def montar_relatorio(r: dict) -> str:
    linhas = [
        f"# S2 — Elo de clubes com os jogos da Loteca ({dt.date.today():%d/%m/%Y})", "",
        "> Este estudo só mede. Critério fixado antes (regra do usuário): o modelo novo só entra se a perda logarítmica "
        f"fora da amostra for menor com q < {_n(config.ASSOCIACAO_NIVEL_SIGNIFICANCIA, 2)}.", "",
        "## Método",
        f"- Rating Elo de cada participante com todos os jogos apurados da Loteca (inicial {config.ELO_CLUBES_RATING_INICIAL:.0f}, "
        f"K = {config.ELO_CLUBES_K:.0f}, vantagem de mando de {config.ELO_CLUBES_VANTAGEM_MANDANTE:.0f} pontos; valores de convenção, não ajustados).",
        "- A diferença de rating vira 1/X/2 pela curva do Elo das seleções (logística ordenada), ajustada só com jogos de anos anteriores.",
        f"- Jogos entre dois clubes de {config.ELO_CLUBES_TESTE_DESDE} em diante, cada concurso previsto só com os anteriores. "
        "Intervalos e valor p por reamostragem de concursos; valor q de Benjamini-Hochberg entre as três comparações.",
        "- Base: Hvattum e Arntzen (2010), International Journal of Forecasting 26, p. 460–470.", "",
        "## Resultados",
    ]
    linhas += _tabela("Jogos \"demais\" (clubes fora do modelo da temporada da CBF)", r["demais"])
    linhas += _tabela("Séries A e B (clubes na mesma série)", r["series_ab"])
    linhas += ["### Comparações (ganho positivo = o primeiro é melhor)", "| Comparação | Ganho em perda log | IC 95% | q | Conclusão |", "|---|---:|---|---:|---|"]
    linhas += [f"| {c['comparacao']} | {_n(c['media'], sinal=True)} | {_n(c['ic_inferior'], sinal=True)} a {_n(c['ic_superior'], sinal=True)} | "
               f"{_n(c['q'], 3)} | {c['conclusao']} |" for c in r["comparacoes"]]
    elo, cal_, ab = r["comparacoes"]
    linhas += ["", "## Decisão"]
    linhas.append("- Demais: " + ("**critério atingido** — o Elo de clubes passa a dar o percentual desses jogos." if elo["conclusao"] == "melhor"
                                  else "critério não atingido — o modelo atual continua."))
    linhas.append("- Calibração do Elo: " + ("ajuda — aplicar." if cal_["conclusao"] == "melhor" else "não ajuda — o Elo entra sem correção."))
    linhas.append("- Séries A e B: " + ("**critério atingido** — o percentual passa a ser a média entre a temporada da CBF e o Elo." if ab["conclusao"] == "melhor"
                                        else "critério não atingido — a temporada da CBF continua sozinha."))
    linhas += ["", "Interruptor: `LOTECA_ELO_CLUBES=0` volta ao cálculo anterior em todos os jogos."]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else config.BASE_DIR / "docs" / f"s2-elo-de-clubes-{dt.date.today():%d-%m-%Y}.md"
    conexao = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        resultado = estudo_elo_clubes.estudar(conexao)
    finally:
        conexao.close()
    destino.write_text(montar_relatorio(resultado), encoding="utf-8")
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

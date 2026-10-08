#!/usr/bin/env python3
"""Variações do Elo de clubes (sugestões S3 e S4). Roda sobre o banco real, SÓ EM LEITURA, e grava o relatório.
Ver stats/estudo_s3_s4.py.

Uso: python scripts/estudo_s3_s4.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import estudo_s3_s4

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_s3_s4")


def _n(v, casas=4, sinal=False):
    return (f"{v:+.{casas}f}" if sinal else f"{v:.{casas}f}").replace(".", ",")


def montar_relatorio(r: dict) -> str:
    linhas = [
        f"# S3 e S4 — variações do Elo de clubes ({dt.date.today():%d/%m/%Y})", "",
        "> Este estudo só mede. Critério do usuário: a variação só substitui o Elo em uso com perda logarítmica menor "
        f"fora da amostra e q < {_n(config.ASSOCIACAO_NIVEL_SIGNIFICANCIA, 2)}. Método em `stats/estudo_s3_s4.py`.", "",
        f"**{r['n']} jogos entre clubes** de 2020 em diante, todos previstos andando no tempo, os mesmos para todas as variações.", "",
        f"Base (Elo em uso no início do estudo, K {config.ELO_CLUBES_K:.0f}, sem margem): perda {_n(r['base']['perda_log'])}, "
        f"acerto do favorito {_n(r['base']['acerto'], 1)}%.", "",
        "| Variação | Perda log | Acerto do favorito | Ganho sobre a base | IC 95% | q | Conclusão |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    linhas += [f"| {v['variacao']} | {_n(v['perda_log'])} | {_n(v['acerto'], 1)}% | {_n(v['media'], sinal=True)} | "
               f"{_n(v['ic_inferior'], sinal=True)} a {_n(v['ic_superior'], sinal=True)} | {_n(v['q'], 3)} | {v['conclusao']} |"
               for v in r["variacoes"]]
    linhas += ["", "Escolha do K (perda nos jogos de 2015 a 2019; nada de 2020 em diante entra na escolha): "
               + "; ".join(f"K {float(k):.0f}: {_n(p)}" for k, p in r["perdas_k_2015_2019"].items()) + ".", "",
               "## Decisão"]
    aprovadas = [v["variacao"] for v in r["variacoes"] if v["conclusao"] == "melhor"]
    linhas.append("- Aprovadas pelo critério: " + (", ".join(aprovadas) if aprovadas else "nenhuma") + ".")
    linhas.append("- As demais não entram: o ganho não se distinguiu do acaso.")
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else config.BASE_DIR / "docs" / f"s3-s4-variacoes-do-elo-{dt.date.today():%d-%m-%Y}.md"
    conexao = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        resultado = estudo_s3_s4.estudar(conexao)
    finally:
        conexao.close()
    destino.write_text(montar_relatorio(resultado), encoding="utf-8")
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

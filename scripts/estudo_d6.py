#!/usr/bin/env python3
"""D6 — concursos com muitos ganhadores (pulverizados). Roda sobre o banco real, SÓ EM LEITURA, e grava o relatório.
Ver stats/estudo_d6.py.

Uso: python scripts/estudo_d6.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import estudo_d6

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_d6")


def _n(v, casas=2, sinal=False):
    return (f"{v:+.{casas}f}" if sinal else f"{v:.{casas}f}").replace(".", ",")


def _q(v):
    return "<0,001" if v < 0.001 else _n(v, 3)


def _tabela(grupo: list[dict]) -> list[str]:
    linhas = ["| Sinal | Pulverizados (média) | Outros (média) | Diferença | q | Leitura |", "|---|---:|---:|---:|---:|---|"]
    linhas += [f"| {r['descricao']} | {_n(r['pulverizados'])} | {_n(r['outros'])} | {_n(r['diferenca'], sinal=True)} | {_q(r['q'])} | "
               f"{'diferença real' if r['q'] < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA else 'dentro do acaso'} |" for r in grupo]
    return linhas + [""]


def montar_relatorio(r: dict) -> str:
    f = r["fora_da_amostra"]
    linhas = [
        f"# D6 — concursos com muitos ganhadores ({dt.date.today():%d/%m/%Y})", "",
        "> Este estudo só mede. Pedido do usuário em 07/10/2026: estudar os concursos que fogem da média em ganhadores, "
        "para ver se algo é perceptível. Método em `stats/estudo_d6.py`.", "",
        f"**{r['concursos']} concursos** com arrecadação registrada e os 14 jogos previstos sem olhar o futuro; "
        f"**{r['pulverizados']} pulverizados** (os 10% com mais ganhadores de 14 por milhão arrecadado dentro do mesmo ano).", "",
        "## Antes do prazo: o que já se sabia", *_tabela(r["antes"]),
        "## Teste fora da amostra",
        f"Logística com os sinais de antes do prazo, treinada só nos anos anteriores, em {f['concursos_testados']} concursos "
        f"({f['pulverizados_testados']} pulverizados): área sob a curva ROC **{_n(f['auc'], 3)}** (IC 95%: {_n(f['ic_inferior'], 3)} a "
        f"{_n(f['ic_superior'], 3)}). 0,5 é o acaso; 1,0 seria acertar sempre.", "",
        ("**Leitura:** há um sinal perceptível antes do prazo, mas fraco: o perfil ajuda a dizer que um concurso tende a ter "
         "mais ganhadores, sem dizer quais concursos serão pulverizados." if f["perceptivel"]
         else "**Leitura:** nada perceptível antes do prazo; o perfil só serve para a revisão pós-jogo."), "",
        "## Depois do resultado: o que aconteceu", *_tabela(r["depois"]),
        "## Os 15 concursos mais pulverizados (posição no próprio ano)",
        "| Concurso | Ano | Ganhadores de 14 | Por milhão | Favoritos confirmados | Zebras | Dificuldade prevista | Favoritos fortes |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    linhas += [f"| {t['numero']} | {t['ano']} | {t['ganhadores_14']} | {_n(t['por_milhao'], 1)} | {t['favoritos_confirmados']:.0f} | "
               f"{t['zebras']:.0f} | {_n(t['dificuldade'])} | {t['favoritos_fortes']:.0f} |" for t in r["mais_pulverizados"]]
    linhas += ["", "## Como ler",
               "- Previsões da época: Elo de clubes nos jogos entre clubes, Elo das seleções e modelo histórico no resto.",
               "- O app nunca estima prêmio em reais; o estudo fala de ganhadores por milhão arrecadado, não de valor."]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else config.BASE_DIR / "docs" / f"d6-concursos-pulverizados-{dt.date.today():%d-%m-%Y}.md"
    conexao = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        resultado = estudo_d6.estudar(conexao)
    finally:
        conexao.close()
    destino.write_text(montar_relatorio(resultado), encoding="utf-8")
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

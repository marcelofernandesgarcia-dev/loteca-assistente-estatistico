#!/usr/bin/env python3
"""Estudo B4 do plano v2: onde colocar o único duplo ou triplo da sugestão (ver stats/estudo_b4.py).
Roda sobre o banco real, SÓ EM LEITURA, e grava o relatório. Não muda a sugestão.

Uso: python scripts/estudo_b4.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import calibracao, estudo_b4

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_b4")


def _n(valor, casas=3, sinal=False):
    return (f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}").replace(".", ",")


def montar_relatorio(r: dict) -> str:
    linhas = [
        f"# B4 — onde colocar o único duplo ou triplo ({dt.date.today():%d/%m/%Y})", "",
        "> Este estudo só mede. A regra da sugestão só muda se uma regra nova ganhar com q < "
        f"{_n(config.ASSOCIACAO_NIVEL_SIGNIFICANCIA, 2)}. Método em `stats/estudo_b4.py`.", "",
        f"**{r['concursos']} concursos** de 2019 em diante (anos com temporada da CBF), com os 14 jogos previstos sem olhar o futuro.", "",
        "| Regra | Acertos por concurso (média) | Concursos em que escolheu outro jogo |", "|---|---:|---:|",
    ]
    linhas += [f"| {estudo_b4.DESCRICAO[k]} | {_n(r['media'][k])} | {r['outro_jogo'][k]} |" for k in estudo_b4.REGRAS]
    linhas += ["", "| Comparação com a regra atual | Diferença em acertos | IC 95% | q | Conclusão |", "|---|---:|---|---:|---|"]
    linhas += [f"| {estudo_b4.DESCRICAO[c['regra']]} | {_n(c['media'], sinal=True)} | {_n(c['ic_inferior'], sinal=True)} a "
               f"{_n(c['ic_superior'], sinal=True)} | {_n(c['q'])} | {c['conclusao']} |" for c in r["comparacoes"]]
    melhor = [c for c in r["comparacoes"] if c["conclusao"] == "melhor"]
    linhas += ["", "**Decisão: " + ("uma regra nova ganhou; a troca depende do usuário.**" if melhor
               else "a regra atual continua (jogo mais incerto). Dar prioridade ao jogo de pouca cobertura não ganhou.**")]
    linhas += ["", "## Como ler",
               "- Os palpites simples são iguais nas três regras; muda só o jogo que recebe o duplo ou o triplo.",
               "- Cobertura da época: completa (os dois clubes na mesma série A ou B da CBF no ano), seleções (Elo), "
               "baixa (frequência geral) e parcial (o resto). O aviso de alta incerteza na tela continua: ele informa, "
               "não escolhe o jogo."]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else config.BASE_DIR / "docs" / f"b4-onde-colocar-o-multiplo-{dt.date.today():%d-%m-%Y}.md"
    conexao = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        resultado = estudo_b4.estudar(estudo_b4.montar_concursos(conexao, calibracao.carregar_registros(conexao)))
    finally:
        conexao.close()
    if resultado is None:
        logger.error("Nenhum concurso elegível.")
        return 1
    destino.write_text(montar_relatorio(resultado), encoding="utf-8")
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

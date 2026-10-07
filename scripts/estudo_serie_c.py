#!/usr/bin/env python3
"""Estudo da Série C (itens B3 e C2 do plano v2): roda sobre o banco real, SÓ EM LEITURA, e grava o relatório.
Não muda nenhum percentual: a decisão de usar o modelo da temporada na Série C depende do resultado e do
usuário. Ver stats/estudo_serie_c.py.

Uso: python scripts/estudo_serie_c.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import backtest_competicao as b2
from stats import backtest_loteca as bl
from stats import estudo_serie_c

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_serie_c")


def _n(valor, casas=4, sinal=False):
    if valor is None:
        return "—"
    return (f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}").replace(".", ",")


def _pct(valor):
    return "—" if valor is None else f"{100 * valor:.1f}%".replace(".", ",")


def _q(valor):
    return "<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ",")


def _minuscula(texto: str) -> str:
    return texto[0].lower() + texto[1:]


def _decisao_b3(loteca: dict | None) -> str:
    if not loteca:
        return "**Decisão: sem base para decidir; a Série C segue com o modelo anterior.**"
    c = next(c for c in loteca["comparacoes"] if c["modelo"] == "retrospecto" and c["contra"] == "atual")
    if c["conclusao"] == "melhor":
        return (f"**Critério atingido (q {_q(c['q'])}): o modelo da temporada pode passar a valer na Série C, "
                "se o usuário decidir.**")
    return (f"**Critério não atingido (q {_q(c['q'])}, precisa ser menor que "
            f"{_n(config.ASSOCIACAO_NIVEL_SIGNIFICANCIA, 2)}): a Série C segue com o modelo anterior e o aviso de "
            "cobertura parcial. Refazer quando houver mais jogos da Série C na Loteca.**")


def montar_relatorio(r: dict) -> str:
    linhas = [
        f"# Série C: modelo da temporada e fase decisiva ({dt.date.today():%d/%m/%Y})",
        "",
        "> Este estudo só mede. Nenhum percentual do app foi alterado por ele.",
        "",
        "## Dados (páginas públicas da CBF, coletadas em 07/10/2026)",
        "| Ano | Jogos | Com placar | Fases | Jogos sem fase |", "|---|---:|---:|---:|---:|",
    ]
    linhas += [f"| {c['ano']} | {c['jogos']} | {c['com_placar']} | {c['fases']} | {c['sem_fase']} |" for c in r["cobertura"]]
    linhas += ["", "Jogo sem fase: a sequência de rodadas da temporada não fechou com as fases da CBF; esses jogos ficam fora do item C2.", ""]

    linhas += ["## B3 — modelo da temporada nos jogos da CBF (Série C)"]
    if r["cbf"]:
        linhas += ["| Modelo | Jogos | Perda logarítmica | Acerto do favorito |", "|---|---:|---:|---:|"]
        linhas += [f"| {b2.DESCRICAO[m]} | {r['cbf']['metricas'][m]['n']} | {_n(r['cbf']['metricas'][m]['perda_log'])} | "
                   f"{_pct(r['cbf']['metricas'][m]['acuracia'] / 100)} |" for m in b2.MODELOS]
        linhas += ["", "| Comparação | Ganho em perda log | IC 95% | q | Conclusão |", "|---|---:|---|---:|---|"]
        linhas += [f"| {b2.DESCRICAO[c['modelo']]} contra {_minuscula(b2.DESCRICAO[c['contra']])} | {_n(c['perda_log']['media'], sinal=True)} | "
                   f"{_n(c['perda_log']['ic_inferior'], sinal=True)} a {_n(c['perda_log']['ic_superior'], sinal=True)} | {_q(c['q'])} | {c['conclusao']} |"
                   for c in r["cbf"]["comparacoes"]]
    else:
        linhas.append("Sem temporadas suficientes para o teste (é preciso ao menos uma de treino antes da testada).")

    linhas += ["", "## B3 — nos jogos da Loteca entre dois clubes da Série C (o critério da decisão)",
               "| Etapa | Jogos |", "|---|---:|"]
    linhas += [f"| {rotulo} | {r['funil'][chave]} |" for chave, rotulo in bl.ETAPAS_DO_FUNIL]
    if r["loteca"]:
        linhas += ["", "| Modelo | Perda logarítmica | Acerto do favorito |", "|---|---:|---:|"]
        linhas += [f"| {bl.DESCRICAO[m]} | {_n(r['loteca']['metricas'][m]['perda_log'])} | {_pct(r['loteca']['metricas'][m]['acuracia'] / 100)} |"
                   for m in bl.MODELOS]
        linhas += ["", "| Comparação | Ganho em perda log | IC 95% | q | Conclusão |", "|---|---:|---|---:|---|"]
        linhas += [f"| {bl.DESCRICAO[c['modelo']]} contra {_minuscula(bl.DESCRICAO[c['contra']])} | {_n(c['perda_log']['media'], sinal=True)} | "
                   f"{_n(c['perda_log']['ic_inferior'], sinal=True)} a {_n(c['perda_log']['ic_superior'], sinal=True)} | {_q(c['q'])} | {c['conclusao']} |"
                   for c in r["loteca"]["comparacoes"]]
    else:
        linhas += ["", "Nenhum jogo da Loteca entre dois clubes da Série C passou pelo funil: não há base para decidir."]
    linhas += ["", _decisao_b3(r["loteca"])]

    e = r["empates"]
    linhas += ["", "## C2 — a fase decisiva empata mais?", "| Fase | Jogos | Empates | Taxa | IC 95% |", "|---|---:|---:|---:|---|"]
    for chave, rotulo in (("primeira_fase", "1ª fase"), ("decisivas", "2ª fase em diante")):
        f = e[chave]
        linhas.append(f"| {rotulo} | {f['jogos']} | {f['empates']} | {_pct(f['taxa'])} | {_pct(f['ic95'][0])} a {_pct(f['ic95'][1])} |")
    if "diferenca" in e:
        d = e["diferenca"]
        linhas.append(f"\nDiferença (decisivas menos 1ª fase): {_n(100 * d['pontos'], 1, True)} pontos percentuais "
                      f"(IC 95%: {_n(100 * d['ic95'][0], 1, True)} a {_n(100 * d['ic95'][1], 1, True)}).")
    fase = r["fase_decisiva"]
    if fase:
        linhas.append(
            f"\nCritério: acrescentar \"fase decisiva\" ao retrospecto, treinado em anos anteriores, em {fase['n']} jogos testados: "
            f"ganho médio {_n(fase['media'], sinal=True)} na perda logarítmica (IC 95%: {_n(fase['ic_inferior'], sinal=True)} a "
            f"{_n(fase['ic_superior'], sinal=True)}; q {_q(fase['q'])}). "
            + ("**Melhora a previsão.**" if fase["q"] < config.ASSOCIACAO_NIVEL_SIGNIFICANCIA else "**Não há melhora comprovada: a fase fica só como contexto na tela.**")
        )
    else:
        linhas.append("\nSem anos suficientes com fase para o teste fora da amostra.")
    linhas += ["", "## Como ler",
               "- Perda logarítmica: quanto menor, mais chance o modelo deu ao que aconteceu. É o critério de troca de modelo.",
               "- Treino só com temporadas anteriores da Série C; os jogos de uma rodada compartilham contexto, por isso o intervalo reamostra rodadas (CBF) ou concursos (Loteca).",
               "- Taxa de empate é descritiva; só o teste fora da amostra diz se a fase ajuda a prever."]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else config.BASE_DIR / "docs" / f"serie-c-modelo-e-fases-{dt.date.today():%d-%m-%Y}.md"
    conexao = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        resultado = estudo_serie_c.estudar(conexao)
    finally:
        conexao.close()
    destino.write_text(montar_relatorio(resultado), encoding="utf-8")
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

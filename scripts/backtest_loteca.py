#!/usr/bin/env python3
"""Roda o teste B2 nos jogos da PRÓPRIA Loteca sobre o banco real, SÓ EM LEITURA, e grava o relatório
em docs/. Compara a frequência simples, o modelo atual do app e dois modelos que usam a temporada da
CBF. Não altera nenhum percentual. Parâmetros em config.B2_*; resultado reprodutível.

Uso: python scripts/backtest_loteca.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import backtest
from stats import backtest_competicao as b2
from stats import backtest_loteca as bl

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backtest_loteca")


def _num(valor, casas=4, sinal=False):
    if valor is None:
        return "—"
    texto = f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}"
    return texto.replace(".", ",")


def _texto_p(valor):
    return "<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ",")


def _rotulo(c: dict) -> str:
    contra = bl.DESCRICAO[c["contra"]]
    return f"{bl.DESCRICAO[c['modelo']]} contra {contra[0].lower() + contra[1:]}"


def montar_relatorio(resumo: dict | None, funil: dict) -> str:
    linhas = [
        f"# B2 nos jogos da Loteca ({dt.date.today():%d/%m/%Y})",
        "",
        "> Este teste só mede. Nenhum percentual exibido no app foi alterado, e trocar o modelo exige decisão do usuário.",
        "",
        "## Pergunta",
        "O teste B2 anterior usou os jogos da CBF. Aqui o mesmo método é aplicado aos jogos que de fato entram nos concursos da Loteca: "
        "os modelos que usam a temporada da CBF superam o modelo atual do app e a frequência simples de 1/X/2?",
        "",
        "## Base e método",
        "- Quatro modelos sobre **exatamente os mesmos jogos**: frequência simples de 1/X/2 da Loteca (referência do B3); modelo atual do app "
        "(Poisson sobre o histórico da Loteca, versão incremental do B3); retrospecto dos dois times na temporada da CBF (logística treinada só nos "
        "jogos da CBF de anos anteriores); Poisson da temporada da CBF, refeito só com jogos disputados antes do dia.",
        f"- Só entra jogo entre dois clubes das Séries A ou B da CBF **na mesma série** no ano, com pelo menos {config.B2_JOGOS_ANTERIORES_MINIMOS} jogos de cada time já disputados "
        "antes do dia do jogo (o jogo do próprio dia não conta). Seleções, estaduais, copas e times de outras divisões ficam de fora: o modelo da temporada não tem base para eles.",
        f"- Comparação pareada jogo a jogo; intervalo de 95% e valor p unilateral por reamostragem de concursos ({config.B2_REPETICOES_BOOTSTRAP} repetições); "
        "valor q de Benjamini-Hochberg entre as seis comparações (critério: perda logarítmica, como no B3).",
        "",
        "## Cobertura (funil)",
        "",
        "| Etapa | Jogos |",
        "|---|---:|",
    ]
    for chave, descricao in bl.ETAPAS_DO_FUNIL:
        linhas.append(f"| {descricao} | {funil[chave]} |")
    if resumo is None:
        linhas += ["", "**Nenhum jogo atendeu a todos os critérios; não há comparação a mostrar.**"]
        return "\n".join(linhas) + "\n"
    linhas += [
        "",
        f"O resultado vale para esses **{resumo['n']}** jogos, não para o concurso inteiro.",
        "",
        "## Desempenho de cada modelo",
        "",
        "| Modelo | Jogos | Acerto do favorito | Brier | Perda logarítmica |",
        "|---|---:|---:|---:|---:|",
    ]
    for modelo in bl.MODELOS:
        m = resumo["metricas"][modelo]
        linhas.append(f"| {bl.DESCRICAO[modelo]} | {m['n']} | {_num(m['acuracia'], 1)}% | {_num(m['brier'])} | {_num(m['perda_log'])} |")
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
            f"| {_rotulo(c)} | {_num(pl['media'], 4, True)} | {_num(pl['ic_inferior'], 4, True)} a {_num(pl['ic_superior'], 4, True)} | "
            f"{_texto_p(pl['p'])} | {_texto_p(c['q'])} | {_num(br['media'], 4, True)} | {_num(br['ic_inferior'], 4, True)} a {_num(br['ic_superior'], 4, True)} | {c['conclusao']} |"
        )
    linhas += ["", "## Perda logarítmica por ano (só descritivo)", "", "| Ano | Jogos | " + " | ".join(bl.DESCRICAO[m] for m in bl.MODELOS) + " |", "|---|---:|" + "---:|" * len(bl.MODELOS)]
    for ano, linha in resumo["por_ano"].items():
        linhas.append(f"| {ano} | {linha['n']} | " + " | ".join(_num(linha[m]) for m in bl.MODELOS) + " |")
    linhas += [
        "",
        "## Como ler",
        "- \"Melhor\" significa mais probabilidade dada ao que de fato aconteceu, fora da amostra, com q < "
        f"{str(config.ASSOCIACAO_NIVEL_SIGNIFICANCIA).replace('.', ',')}. \"Sem diferença perceptível\" não prova igualdade: a amostra pode não detectar ganho pequeno.",
        "- O acerto do favorito não é o critério: o que importa é a qualidade das probabilidades (perda logarítmica e Brier).",
        "- Os jogos de um mesmo concurso compartilham contexto, por isso o intervalo reamostra concursos. Times se repetem entre concursos, o que o intervalo não corrige por completo.",
        "- O resultado descreve os jogos entre clubes das Séries A e B com dados suficientes da temporada. Não cobre seleções, estaduais, copas nem times de outras divisões, que são grande parte dos concursos.",
        "- Mudar o percentual exibido no app seria uma decisão separada, com aprovação do usuário.",
        "",
        "## Reprodução",
        "`.venv\\Scripts\\python scripts\\backtest_loteca.py` (só lê `loteca.db`; semente em `config.B2_SEMENTE`).",
    ]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "docs" / f"b2-jogos-da-loteca-{dt.date.today():%d-%m-%Y}.md"
    )
    conexao = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        previsoes_atual = backtest.prever_walk_forward(backtest.carregar_jogos(conexao))
        pesos = bl.pesos_por_ano(b2.carregar_amostra(conexao))
        jogos, funil = bl.montar_jogos(conexao, previsoes_atual, pesos)
    finally:
        conexao.close()
    logger.info("Funil: %s", funil)
    resumo = bl.resumir(jogos)
    destino.write_text(montar_relatorio(resumo, funil), encoding="utf-8")
    if resumo:
        for m in bl.MODELOS:
            logger.info("%s: perda log %s, Brier %s", m, _num(resumo["metricas"][m]["perda_log"]), _num(resumo["metricas"][m]["brier"]))
        for c in resumo["comparacoes"]:
            logger.info("%s: ganho %s, q %s, %s", _rotulo(c), _num(c["perda_log"]["media"], 4, True), _texto_p(c["q"]), c["conclusao"])
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

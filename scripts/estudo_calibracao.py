#!/usr/bin/env python3
"""Roda o estudo de calibração dos percentuais (E4, Fase 1) sobre o banco real, SÓ EM LEITURA, e grava o
relatório em docs/. Não altera nenhum percentual do app. Parâmetros em config.CALIBRACAO_*.

Uso: python scripts/estudo_calibracao.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import calibracao as cal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_calibracao")


def _num(valor, casas=4, sinal=False):
    if valor is None:
        return "—"
    texto = f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}"
    return texto.replace(".", ",")


def _texto_p(valor):
    return "<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ",")


def _intervalo(par, casas=1):
    return f"{_num(par[0], casas)} a {_num(par[1], casas)}"


def _bilhete(b):
    partes = []
    if b["duplos"]:
        partes.append(f"{b['duplos']} duplo{'s' if b['duplos'] > 1 else ''}")
    if b["triplos"]:
        partes.append(f"{b['triplos']} triplo{'s' if b['triplos'] > 1 else ''}")
    modo = "pela regra" if b["modo"] == "regra" else "sorteado"
    return f"{' e '.join(partes)}, {modo} ({b['apostas']} apostas)"


def montar_relatorio(estudo: dict) -> str:
    m = estudo["metricas"]
    linhas = [
        f"# Calibração dos percentuais — Fase 1 ({dt.date.today():%d/%m/%Y})",
        "",
        "> Estudo só de leitura. Nenhum percentual do app foi alterado. A integração (Fase 2) depende da validação do usuário.",
        "",
        "## Pergunta",
        "Os percentuais do app são confiantes demais (o estudo de 30/09 viu a chance de 13 ou mais cerca de 7 vezes acima do que aconteceu). "
        "Uma correção simples, ajustada só com o passado, aproxima a chance do bilhete do que de fato acontece?",
        "",
        "## Base e método",
        f"- **{estudo['jogos_avaliados']}** jogos em **{estudo['concursos_avaliados']}** concursos, com a previsão que o app daria na época "
        "(sem olhar o futuro): Elo nos jogos entre seleções depois de 2010, força histórica dos clubes nos demais, frequência simples quando faltam jogos.",
        "- Por origem: " + "; ".join(f"{cal.DESCRICAO_ORIGEM.get(o, o)} {n}" for o, n in estudo["por_origem_n"].items()) + ".",
        "- Correção: o percentual é elevado a um **expoente** (abaixo de 1 achata percentuais confiantes demais) e **misturado** com a frequência simples. "
        "Expoente 1 e mistura 1 significam sem correção.",
        f"- Os parâmetros de cada bloco de {config.CALIBRACAO_REAJUSTE_A_CADA} concursos são ajustados só com os concursos anteriores, por origem. "
        "Só entram na avaliação jogos cuja origem já tinha treino suficiente.",
        "- Método principal definido antes do resultado: expoente e mistura juntos. Os dois isolados aparecem só para comparação.",
        f"- Comparação pareada jogo a jogo com a versão sem correção; intervalo e valor p por reamostragem de concursos ({config.CALIBRACAO_REPETICOES_BOOTSTRAP} repetições); "
        "valor q de Benjamini-Hochberg entre as três correções.",
        "",
        "## Parâmetros que o app usaria hoje (ajustados com todos os concursos)",
        "",
        "| Origem | Jogos | Expoente | Mistura | Leitura |",
        "|---|---:|---:|---:|---|",
    ]
    for origem, p in estudo["parametros_finais"].items():
        leitura = []
        leitura.append("achata os percentuais" if p["expoente"] < 0.95 else ("acentua os percentuais" if p["expoente"] > 1.05 else "mantém o formato"))
        leitura.append(f"{_num(100 * (1 - p['mistura']), 0)}% de peso para a frequência simples")
        linhas.append(f"| {cal.DESCRICAO_ORIGEM.get(origem, origem)} | {p['jogos']} | {_num(p['expoente'], 2)} | {_num(p['mistura'], 2)} | {'; '.join(leitura)} |")
    linhas += [
        "",
        "## Qualidade dos percentuais (menor é melhor)",
        "",
        "| Versão | Perda logarítmica | Brier |",
        "|---|---:|---:|",
    ]
    for metodo in cal.METODOS:
        linhas.append(f"| {cal.DESCRICAO_METODO[metodo]} | {_num(m[metodo]['perda_log'])} | {_num(m[metodo]['brier'])} |")
    linhas.append(f"| Frequência simples (referência) | {_num(m['frequencia']['perda_log'])} | {_num(m['frequencia']['brier'])} |")
    linhas += ["", "| Correção contra sem correção | Ganho em perda logarítmica | IC 95% | q | Conclusão |", "|---|---:|---|---:|---|"]
    for c in estudo["comparacoes"]:
        linhas.append(f"| {cal.DESCRICAO_METODO[c['metodo']]} | {_num(c['media'], 4, True)} | {_num(c['ic_inferior'], 4, True)} a {_num(c['ic_superior'], 4, True)} | {_texto_p(c['q'])} | {c['conclusao']} |")
    linhas += ["", "### Por origem (perda logarítmica)", "", "| Origem | Jogos | Sem correção | Principal | Frequência simples |", "|---|---:|---:|---:|---:|"]
    for origem, valores in estudo["por_origem"].items():
        linhas.append(
            f"| {cal.DESCRICAO_ORIGEM.get(origem, origem)} | {valores['original']['n']} | {_num(valores['original']['perda_log'])} | "
            f"{_num(valores[cal.METODO_PRINCIPAL]['perda_log'])} | {_num(valores['frequencia']['perda_log'])} |"
        )
    linhas += ["", "## Curva de calibração (quando o app diz X%, quanto acontece)", "", "Entre parênteses, quantos percentuais caíram na faixa em cada versão.", "",
               "| Faixa prevista | Sem correção: previsto → observado | Corrigida: previsto → observado |", "|---|---|---|"]
    corrigida = {round(c["faixa"][0], 1): c for c in estudo["curva_corrigida"]}
    original = {round(c["faixa"][0], 1): c for c in estudo["curva_original"]}
    for inicio in sorted(set(original) | set(corrigida)):
        o, c = original.get(inicio), corrigida.get(inicio)
        texto_o = f"{_num(100 * o['previsto'], 1)}% → {_num(100 * o['observado'], 1)}% ({o['n']})" if o else "—"
        texto_c = f"{_num(100 * c['previsto'], 1)}% → {_num(100 * c['observado'], 1)}% ({c['n']})" if c else "—"
        linhas.append(f"| {_num(100 * inicio, 0)}% a {_num(100 * inicio + 10, 0)}% | {texto_o} | {texto_c} |")
    linhas += [
        "",
        "## O que importa: a chance do bilhete contra o que aconteceu",
        "",
        "Mesmos bilhetes nas duas contas; só a chance muda. Valores somados nos concursos avaliados. "
        "O intervalo é a faixa de 95% em que o número de concursos premiados deveria cair se a conta estivesse certa.",
        "",
        "| Bilhete | Concursos | Fez 13 ou mais | Conta sem correção | Conta corrigida | Fez 14 | Sem correção | Corrigida |",
        "|---|---:|---:|---|---|---:|---|---|",
    ]
    for b in estudo["bilhetes"]:
        linhas.append(
            f"| {_bilhete(b)} | {b['concursos']} | **{b['feito_13']}** | {_num(b['previsto_13_original'], 1)} ({_intervalo(b['intervalo_13_original'])}) | "
            f"{_num(b['previsto_13_corrigida'], 1)} ({_intervalo(b['intervalo_13_corrigida'])}) | **{b['feito_14']}** | "
            f"{_num(b['previsto_14_original'], 1)} ({_intervalo(b['intervalo_14_original'])}) | {_num(b['previsto_14_corrigida'], 1)} ({_intervalo(b['intervalo_14_corrigida'])}) |"
        )
    linhas += [
        "",
        "## Conferência da suposição de jogos independentes",
        "",
        "Com o bilhete de um duplo pela regra: número de concursos com pelo menos k acertos, esperado pela conta e observado.",
        "",
        "| k acertos ou mais | Esperado sem correção | Esperado corrigido | Observado |",
        "|---:|---:|---:|---:|",
    ]
    for k in sorted(estudo["distribuicao_corrigida"]):
        o, c = estudo["distribuicao_original"][k], estudo["distribuicao_corrigida"][k]
        linhas.append(f"| {k} | {_num(o['esperado'], 1)} | {_num(c['esperado'], 1)} | **{c['observado']}** |")
    linhas += [
        "",
        "## Como ler",
        "- A conta do bilhete está certa quando o número de concursos premiados cai dentro do intervalo. Fora dele, a chance mostrada engana.",
        "- Expoente abaixo de 1 com mistura perto de 1 significa que os percentuais daquela origem têm informação, mas exagerada: a correção achata, quase sem recorrer à frequência simples. "
        "Mistura perto de 0 significaria o contrário: percentual sem informação além da frequência.",
        "- Compare, na tabela por origem, a coluna Principal com a Frequência simples: é ali que se vê se a origem, depois de corrigida, supera a frequência.",
        "- O ajuste de notícias não entra aqui (não há histórico); ele continua aplicado por cima do percentual, limitado a "
        f"{_num(config.AJUSTE_EXTERNO_TETO_PONTOS, 0)} pontos.",
        "- Jogos entre seleções antes de 2010 e os não casados com a base aberta seguem o modelo histórico, como no teste do Elo.",
        "",
        "## Reprodução",
        "`.venv\\Scripts\\python scripts\\estudo_calibracao.py` (só lê `loteca.db` e a base aberta das seleções; parâmetros em `config.CALIBRACAO_*`).",
    ]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "docs" / f"e4-calibracao-fase1-{dt.date.today():%d-%m-%Y}.md"
    )
    conexao = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        registros = cal.carregar_registros(conexao)
    finally:
        conexao.close()
    logger.info("Registros: %s", len(registros))
    estudo = cal.estudar(registros)
    if estudo is None:
        logger.error("Sem jogos com treino suficiente para avaliar a calibração; relatório não gerado.")
        return 1
    destino.write_text(montar_relatorio(estudo), encoding="utf-8")
    for origem, p in estudo["parametros_finais"].items():
        logger.info("%s: expoente %s, mistura %s (%s jogos)", origem, p["expoente"], p["mistura"], p["jogos"])
    for c in estudo["comparacoes"]:
        logger.info("%s: ganho %s, q %s, %s", c["metodo"], _num(c["media"], 4, True), _texto_p(c["q"]), c["conclusao"])
    for b in estudo["bilhetes"]:
        logger.info("%s: fez13 %s | prev orig %.1f | prev corr %.1f || fez14 %s | prev orig %.1f | prev corr %.1f", _bilhete(b), b["feito_13"],
                    b["previsto_13_original"], b["previsto_13_corrigida"], b["feito_14"], b["previsto_14_original"], b["previsto_14_corrigida"])
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

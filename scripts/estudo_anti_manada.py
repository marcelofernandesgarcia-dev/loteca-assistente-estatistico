#!/usr/bin/env python3
"""Roda o estudo anti-manada (Q7) sobre o banco real, SÓ EM LEITURA, e grava o relatório em docs/.
Parâmetros em config.Q7_*; resultado reprodutível.

Uso: python scripts/estudo_anti_manada.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import anti_manada
from stats.premiacao import reais

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_anti_manada")

MOTIVOS = {
    "sem_14_jogos_apurados": "sem os 14 jogos apurados (formato antigo de 13 jogos ou concurso ainda aberto)",
    "jogo_decidido_por_sorteio": "com jogo decidido por sorteio (o resultado não saiu do jogo)",
    "sem_arrecadacao": "sem arrecadação informada (a CAIXA só informa de 2009 em diante)",
    "sem_ganhadores_14": "sem a faixa de 14 acertos informada",
}


def _num(valor, casas=2, sinal=False):
    texto = f"{valor:+.{casas}f}" if sinal else f"{valor:.{casas}f}"
    return texto.replace(".", ",")


def _texto_p(valor):
    return "—" if valor is None else ("<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ","))


def montar_relatorio(
    concursos: list[dict], fora: dict, resultados: list[dict], faixas: list[dict], ingenuas: dict, anterior: dict | None
) -> str:
    anos = sorted({c["ano"] for c in concursos})
    if anterior:
        linha_anterior = (
            f"- A conta anterior (**-0,13**) foi reproduzida em {anterior['n']} concursos: é a correlação de **Pearson** entre jogos fora da coluna 1 e o "
            f"número bruto de ganhadores de 14, que pesa muito os poucos concursos com centenas de ganhadores: {_num(anterior['pearson'], 2, True)}. "
            f"Com os mesmos concursos e a correlação de postos (Spearman), o valor é {_num(anterior['spearman'], 2, True)}. "
            "O -0,13 subestimava a relação por causa dos valores extremos, não porque ela fosse fraca."
        )
    else:
        linha_anterior = "- Não foi possível reproduzir a conta anterior com os dados atuais."
    linhas = [
        f"# Q7 — Estudo anti-manada ({dt.date.today():%d/%m/%Y})",
        "",
        "> Descreve o passado. Não diz o que vai acontecer em um concurso futuro e não recomenda marcar zebra. "
        "Loteria é jogo de azar regulado; nenhum padrão aqui garante prêmio.",
        "",
        "## Pergunta",
        "Quando o resultado do concurso se afasta do que a maioria marca (mais jogos fora da coluna 1), há menos ganhadores de 14 acertos, "
        "e portanto prêmio menos dividido? A conta anterior do projeto (correlação de -0,13) não descontava a arrecadação nem a época.",
        "",
        "## Base e método",
        f"- **{len(concursos)}** concursos úteis, de {anos[0]} a {anos[-1]}. Ficaram de fora: "
        + "; ".join(f"{n} {MOTIVOS[k]}" for k, n in fora.items() if n) + ".",
        "- Desfecho: ganhadores de 14 acertos por R$ 1 milhão arrecadado (desconta o tamanho do concurso).",
        "- Correlação de Spearman **estratificada por ano**: os postos são calculados dentro de cada ano, para que mudanças de época "
        f"(arrecadação, hábito dos apostadores) não fabriquem correlação. Anos com menos de {config.Q7_CONCURSOS_MINIMOS_POR_ANO} concursos úteis ficam fora.",
        f"- Valor p por permutação dentro do ano ({config.Q7_PERMUTACOES} sorteios); intervalo de 95% por reamostragem de concursos "
        f"({config.Q7_REPETICOES_BOOTSTRAP} repetições, com os postos fixos); valor q de Benjamini-Hochberg entre as 3 exposições.",
        "",
        "## Resultado",
        "",
        "| Exposição | Concursos | Correlação | IC 95% | p | q | Conclusão |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for r in resultados:
        ic = "—" if r["rho"] is None else f"{_num(r['ic_inferior'], 2, True)} a {_num(r['ic_superior'], 2, True)}"
        rho = "—" if r["rho"] is None else _num(r["rho"], 2, True)
        linhas.append(f"| {r['descricao']} | {r['n']} | {rho} | {ic} | {_texto_p(r['p'])} | {_texto_p(r['q'])} | {r['conclusao']} |")
    linhas += [
        "",
        "## Conferência com a conta anterior do projeto",
        linha_anterior,
        f"- Nos {len(concursos)} concursos úteis, sem estratificar por ano: {_num(ingenuas['bruto'], 2, True)} contra o número bruto de ganhadores e "
        f"{_num(ingenuas['taxa'], 2, True)} contra ganhadores por milhão arrecadado. A resposta estratificada da tabela acima fica próxima: "
        "a época e o tamanho do concurso explicam pouco da relação.",
        "",
        "## Descritivo por faixa de jogos fora da coluna 1",
        "",
        "| Jogos fora da coluna 1 | Concursos | Ganhadores de 14 por milhão arrecadado (média) | Sem ganhador de 14 | Prêmio mediano de 14 (onde houve) |",
        "|---|---:|---:|---:|---:|",
    ]
    for f in faixas:
        premio = "—" if f["premio_mediano"] is None else reais(f["premio_mediano"])
        linhas.append(f"| {f['faixa']} | {f['concursos']} | {_num(f['ganhadores_por_milhao'])} | {_num(f['sem_ganhador_14'], 0)}% | {premio} |")
    linhas += [
        "",
        "## Como ler",
        "- **Correlação negativa** significa: nos concursos com mais jogos fora da coluna 1, houve menos ganhadores de 14 por milhão arrecadado, comparando concursos do mesmo ano. É associação, não causa.",
        "- **Sem diferença perceptível** não prova que não existe relação: a amostra pode não detectar efeito pequeno. O intervalo mostra o que a amostra ainda admite.",
        "- Mais zebras também aumentam a chance de ninguém acertar os 14, o que acumula o prêmio e não é o mesmo que \"prêmio maior para quem acerta\". O prêmio de 14 acertos depende da arrecadação, do rateio do manual e dos acúmulos; ver `docs/valores-dos-concursos-30-09-2026.md`.",
        "- A chance de acertar 14 jogos continua muito pequena em qualquer estratégia; este estudo não a altera.",
        "",
        "## Reprodução",
        "`.venv\\Scripts\\python scripts\\estudo_anti_manada.py` (só lê `loteca.db`; semente em `config.Q7_SEMENTE`).",
    ]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "docs" / f"q7-anti-manada-{dt.date.today():%d-%m-%Y}.md"
    )
    conexao = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        concursos, fora = anti_manada.carregar_concursos(conexao)
        anterior = anti_manada.conta_anterior(conexao)
    finally:
        conexao.close()
    logger.info("Concursos úteis: %s; fora: %s", len(concursos), fora)
    resultados = anti_manada.estudar(concursos)
    ingenuas = {
        "bruto": anti_manada.correlacao_simples([c["fora_da_coluna_1"] for c in concursos], [c["ganhadores_14"] for c in concursos]),
        "taxa": anti_manada.correlacao_simples([c["fora_da_coluna_1"] for c in concursos], [c["ganhadores_por_milhao"] for c in concursos]),
    }
    destino.write_text(
        montar_relatorio(concursos, fora, resultados, anti_manada.tabela_por_faixa(concursos), ingenuas, anterior), encoding="utf-8"
    )
    for r in resultados:
        logger.info("%s: %s (rho %s, q %s)", r["exposicao"], r["conclusao"], r["rho"], _texto_p(r["q"]))
    logger.info("Ingênuas: %s", ingenuas)
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

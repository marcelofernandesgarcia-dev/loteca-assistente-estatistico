#!/usr/bin/env python3
"""Roda o estudo de associação (P3/Q4) sobre o banco real, SÓ EM LEITURA, e grava o
relatório em docs/. Os parâmetros vêm de config.ASSOCIACAO_*; o resultado é reprodutível
(semente fixa).

Uso: python scripts/estudo_associacao.py [caminho-do-relatorio.md]
"""
import datetime as dt
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from stats import associacao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("estudo_associacao")


def _sinal(valor, casas=3):
    return "—" if valor is None else f"{valor:+.{casas}f}".replace(".", ",")


def _pct(valor):
    return "—" if valor is None else f"{100 * valor:+.2f}%".replace(".", ",")


def _texto_p(valor):
    if valor is None:
        return "—"
    return "<0,001" if valor < 0.001 else f"{valor:.3f}".replace(".", ",")


def montar_relatorio(resultados: list[dict], n_jogos: int, n_temporadas: int) -> str:
    n_testes = sum(1 for r in resultados if r["avaliado"])
    linhas = [
        f"# P3 — Estudo de associação entre fatores e desempenho ({dt.date.today():%d/%m/%Y})",
        "",
        f"> {associacao.AVISO}",
        "",
        "## Pergunta",
        "Cada fator objetivo **melhora a previsão do resultado do jogo** além do que o retrospecto do time na temporada e o mando já dizem? "
        "Mostra o que costuma vir junto; não mostra o que causa.",
        "",
        "## Base e método",
        f"- **{n_jogos}** jogos de time (Séries A e B da CBF, {n_temporadas} temporadas), com pelo menos "
        f"{config.ASSOCIACAO_JOGOS_ANTERIORES_MINIMOS} jogos anteriores do time na temporada. Resultado = pontos (0, 1 ou 3).",
        "- Modelo base: pontos ~ retrospecto (pontos por jogo até o jogo anterior) + mando. Modelo com o fator: o mesmo mais o fator.",
        "- Validação fora da amostra: cada temporada (série e ano) é deixada de fora; os modelos são ajustados nas outras e comparados na que ficou. "
        "**Ganho** = erro quadrático do modelo base menos o do modelo com o fator (positivo = o fator ajudou).",
        f"- Intervalo de 95% e valor p por reamostragem de times na temporada ({config.ASSOCIACAO_REPETICOES_BOOTSTRAP} repetições; "
        f"{config.ASSOCIACAO_REPETICOES_COEFICIENTE} para o coeficiente). Valor p unilateral (só interessa se melhora). "
        f"Valor q pela correção de Benjamini-Hochberg entre os {n_testes} testes feitos; nível q < {config.ASSOCIACAO_NIVEL_SIGNIFICANCIA}.",
        f"- Limiares fixados antes do resultado: forma boa ≥ {config.ASSOCIACAO_FORMA_BOA} e ruim ≤ {config.ASSOCIACAO_FORMA_RUIM} "
        f"pontos por jogo nos últimos {config.ASSOCIACAO_FORMA_JANELA}; sequência de {config.ASSOCIACAO_SEQUENCIA_MINIMA}; "
        f"topo/fundo = {config.ASSOCIACAO_ZONA_TAMANHO} primeiros/últimos pela tabela da rodada anterior.",
        "- Cartões ficaram fora: a base guarda só o total da temporada, não o cartão por rodada (decisão do usuário, 01/10/2026).",
        "",
        "## Resultado",
        "",
        "| Fator | Jogos com | Jogos sem | Ganho de previsão (erro quadrático) | IC 95% do ganho | p | q | Coeficiente (pontos/jogo) | IC 95% | Conclusão |",
        "|---|---:|---:|---:|---|---:|---:|---:|---|---|",
    ]
    for r in resultados:
        if r["avaliado"]:
            ganho = _pct(r["ganho_relativo"])
            ic_ganho = f"{_sinal(r['ganho_ic_inferior'], 4)} a {_sinal(r['ganho_ic_superior'], 4)}"
            ic_coef = f"{_sinal(r['coef_ic_inferior'], 2)} a {_sinal(r['coef_ic_superior'], 2)}"
            coef = _sinal(r["coeficiente"], 2)
        else:
            ganho = ic_ganho = ic_coef = coef = "—"
        linhas.append(
            f"| {r['descricao']} | {r['n_exposto']} | {r['n_referencia']} | {ganho} | {ic_ganho} | "
            f"{_texto_p(r['p'])} | {_texto_p(r['q'])} | {coef} | {ic_coef} | {r['conclusao']} |"
        )
    linhas += [
        "",
        "## Como ler",
        "- **Ganho** em percentual do erro do modelo base; o IC está em unidades de erro quadrático por jogo. Ganho perto de zero significa que o fator não acrescenta nada ao que o retrospecto e o mando já informam.",
        "- **Coeficiente** é quantos pontos por jogo o fator soma ou subtrai, já descontados retrospecto e mando (ajuste com todos os dados). É descritivo: o que decide se o fator vale é o ganho fora da amostra.",
        "- **Não melhora a previsão** não prova que o fator não importa; indica que, com esta amostra, ele não acrescenta ao que já se sabe. O IC do coeficiente mostra o tamanho do efeito que a amostra ainda admite.",
        "- **Melhora a previsão fora da amostra** é associação, não causa, e **não autoriza** mudar o percentual do modelo: isso exigiria um backtest completo sobre a frequência simples.",
        "- **SAF:** poucos clubes, adoção do modelo não aleatória (clubes grandes e clubes em crise) e marca vinda do nome do clube na CBF, que não prova a ausência de SAF.",
        "- Os jogos de um time na temporada não são independentes; por isso o intervalo reamostra times, não jogos.",
        "",
        "## Primeira versão descartada (registro de rastreabilidade)",
        "A primeira versão comparava, dentro de cada time e temporada, o resultado de jogos com e sem o fator, com valor p por permutação de rótulos. "
        "Rodou sobre o banco real e apontou sete dos oito fatores como \"associação detectada\", com sinais coerentes demais "
        "(forma boa, sequência de vitórias e topo da tabela com diferença **negativa**; as versões opostas, **positiva**). "
        "Causa: o fator é calculado do histórico do próprio time e a média usada para comparar inclui esses mesmos jogos, "
        "o que cria viés negativo; a permutação pressupõe rótulos intercambiáveis, o que não vale para rótulos derivados do passado. "
        "O resultado foi descartado antes de qualquer uso. O teste `test_regressao_do_artefato_historico_puro_nao_vira_achado` impede a volta do erro.",
        "",
        "## Reprodução",
        "`.venv\\Scripts\\python scripts\\estudo_associacao.py` (só lê `loteca.db`; semente fixa em `config.ASSOCIACAO_SEMENTE`).",
    ]
    return "\n".join(linhas) + "\n"


def main() -> int:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parent.parent / "docs" / f"p3-associacao-fatores-{dt.date.today():%d-%m-%Y}.md"
    )
    conexao = sqlite3.connect(f"file:{config.DB_PATH.as_posix()}?mode=ro", uri=True)
    conexao.row_factory = sqlite3.Row
    try:
        observacoes = associacao.carregar_observacoes(conexao)
    finally:
        conexao.close()
    n_temporadas = len({o["temporada"] for o in observacoes})
    logger.info("Observações: %s jogos, %s temporadas", len(observacoes), n_temporadas)
    resultados = associacao.estudar(observacoes)
    destino.write_text(montar_relatorio(resultados, len(observacoes), n_temporadas), encoding="utf-8")
    for r in resultados:
        logger.info(
            "%s: %s (ganho %s, coeficiente %s, q %s)", r["fator"], r["conclusao"],
            _pct(r.get("ganho_relativo")), _sinal(r.get("coeficiente"), 2), _texto_p(r["q"]),
        )
    logger.info("Relatório gravado em %s", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

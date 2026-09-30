"""Sugestões de alteração e complexidade dos jogos de um bilhete já marcado
(recomendações 1, 2 e 4 do estudo E1-E4, aprovadas pelo usuário em 30/09/2026).

Regras de segurança, do usuário:
- a sugestão NUNCA aumenta o custo nem o número de duplos e triplos que ele escolheu;
- a sugestão do próprio app continua em no máximo um duplo ou um triplo (stats.bilhete);
- toda alteração vem com o efeito medido em concursos passados (stats.calibracao_bilhete),
  que é pequeno: ajuda pouco e sozinha não leva a 13 ou 14.

Só montagem de dados: as contas estão em stats.otimizacao_bilhete.
"""
import config
from stats.analise_palpite import formatar_uma_em
from stats.otimizacao_bilhete import complexidade_do_jogo, economias, trocas_de_um_passo

NOME_NIVEL = {"baixa": "baixa", "media": "média", "alta": "alta"}


def _custo(marcacoes: list[list[str]]) -> int:
    apostas = 1
    for colunas in marcacoes:
        apostas *= len(colunas)
    return apostas


def melhor_no_ano(diferenca: dict | None) -> str | None:
    """'casa' ou 'fora' quando o ano em curso aponta um lado com confiança suficiente: as duas
    partes com dado da mesma fonte e sem amostra pequena. Senão None (não usar como motivo)."""
    if not diferenca or diferenca.get("fontes_diferentes") or diferenca.get("amostra_pequena"):
        return None
    return diferenca.get("melhor")


def complexidade_dos_jogos(jogos: list[dict], diferencas_no_ano: dict[int, dict | None] | None = None) -> dict[int, dict]:
    """{num_jogo: complexidade_do_jogo(...)}. `jogos`: cada um com num_jogo, pct e, opcional,
    sem_base_propria. `diferencas_no_ano`: {num_jogo: stats.ano_em_curso.diferenca_no_ano(...)}."""
    diferencas_no_ano = diferencas_no_ano or {}
    return {
        j["num_jogo"]: complexidade_do_jogo(
            j["pct"], bool(j.get("sem_base_propria")), melhor_no_ano(diferencas_no_ano.get(j["num_jogo"]))
        )
        for j in jogos
    }


def montar_sugestoes(jogos: list[dict]) -> dict:
    """`jogos`: os jogos de stats.analise_palpite.analisar_palpite (num_jogo, pct, marcacoes).
    Devolve {'trocas': [...], 'economias': [...]}. Cada troca mantém o custo e o número de duplos
    e triplos (conferido aqui: uma sugestão que mude o custo é descartada, não mostrada)."""
    pcts = [j["pct"] for j in jogos]
    marcacoes = [list(j["marcacoes"]) for j in jogos]
    numeros = [j["num_jogo"] for j in jogos]
    custo = _custo(marcacoes)
    forma = sorted(len(m) for m in marcacoes)

    trocas = [
        t for t in trocas_de_um_passo(pcts, marcacoes, numeros)
        if _custo(t["marcacoes"]) == custo and sorted(len(m) for m in t["marcacoes"]) == forma
    ][: config.SUGESTOES_MAX_TROCAS]
    return {
        "trocas": trocas,
        "economias": economias(pcts, marcacoes, numeros)[: config.SUGESTOES_MAX_ECONOMIAS],
        "custo": custo,
    }


def frase_da_troca(troca: dict) -> str:
    descricao = troca["descricao"]
    return (
        f"{descricao[0].upper()}{descricao[1:]}. Pelos percentuais do app, a chance de acertar todos vai de "
        f"{formatar_uma_em(troca['chance_antes'])} para {formatar_uma_em(troca['chance_depois'])}, pelo mesmo custo."
    )


def frase_da_economia(economia: dict) -> str:
    de, para = "".join(economia["de"]), "".join(economia["para"])
    perda = economia["perda_relativa"] * 100
    return (
        f"Jogo {economia['jogo']}: tirar a coluna {economia['tirar']} ({de} vira {para}) economiza "
        f"R$ {economia['economia_reais']:.2f}".replace(".", ",")
        + f" e reduz em {perda:.0f}% a chance de acertar todos, pelos percentuais do app."
    )


def marcacao_contra_o_favorito(analise_jogos: list[dict]) -> list[int]:
    """Números dos jogos marcados contra o favorito dos dados (sem ser triplo nem zebra declarada):
    é onde a troca por coluna costuma render mais no teste."""
    return [j["num_jogo"] for j in analise_jogos if j["categoria"] == "contra_o_favorito"]

"""O que aconteceu de fato com bilhetes do mesmo custo nos concursos passados, para
ficar ao lado da "chance de acertar" calculada pelos percentuais (recomendação 3 do
estudo E1-E4, aprovada pelo usuário em 30/09/2026).

Motivo: no teste de 1.127 concursos, bilhetes de 8 custos diferentes fizeram 13 ou mais
em 29 concursos onde os percentuais previam 217 (cerca de 7 vezes menos), e 14 em nenhum
onde previam 29. A conta "1 em X" supõe os percentuais corretos; eles são mais confiantes
que a realidade. Ver docs/estudo-sugestoes-jogos-complexos-30-09-2026.md.

Sem olhar o futuro: os percentuais de cada concurso usam só os concursos anteriores
(stats.backtest.prever_walk_forward). Limitação: modelo histórico dos clubes, sem o Elo
das seleções e sem o ajuste de notícias.
"""
import config
from stats.analise_palpite import chance_do_bilhete
from stats.backtest import carregar_jogos, prever_walk_forward
from stats.bilhete import PRECO_APOSTA
from stats.estudo_sugestoes import acertos, avaliar_trocas, concursos_completos
from stats.otimizacao_bilhete import distribuicao_por_regra


def concursos_para_calibracao(conexao) -> list[list[tuple[dict, str]]]:
    """Concursos passados completos, cada um [(percentuais, resultado)] dos 14 jogos."""
    jogos = carregar_jogos(conexao)
    return concursos_completos(jogos, prever_walk_forward(jogos))


def versao_dos_dados(conexao) -> tuple:
    """Muda quando entra concurso apurado novo: chave de cache da calibração."""
    linha = conexao.execute(
        "SELECT COUNT(*), COALESCE(MAX(concurso_numero), 0) FROM jogos WHERE resultado IS NOT NULL"
    ).fetchone()
    return (linha[0], linha[1])


def frequencia_por_custo(concursos: list[list[tuple[dict, str]]], duplos: int, triplos: int) -> dict | None:
    """Com bilhetes de `duplos` duplos e `triplos` triplos montados pela regra do app em cada
    concurso passado: quantas vezes fez 12+, 13+ e 14, e quantas vezes os percentuais previam.
    None se a combinação não cabe nos 14 jogos ou não há concursos."""
    if not concursos or duplos < 0 or triplos < 0 or duplos + triplos > 14:
        return None
    feitos = {12: 0, 13: 0, 14: 0}
    previsto_14 = previsto_13 = 0.0
    for concurso in concursos:
        pcts, reais = [p for p, _ in concurso], [r for _, r in concurso]
        bilhete = distribuicao_por_regra(pcts, duplos, triplos)
        chance = chance_do_bilhete([sum(p[c] for c in m) for p, m in zip(pcts, bilhete)])
        previsto_14 += chance["chance_todos"]
        previsto_13 += chance["chance_todos_menos_um_ou_mais"]
        n_acertos = acertos(bilhete, reais)
        for limite in feitos:
            feitos[limite] += n_acertos >= limite
    return {
        "concursos": len(concursos), "duplos": duplos, "triplos": triplos,
        "apostas": 2**duplos * 3**triplos, "custo": 2**duplos * 3**triplos * PRECO_APOSTA,
        "fez_12_ou_mais": feitos[12], "fez_13_ou_mais": feitos[13], "fez_14": feitos[14],
        "previsto_13_ou_mais": previsto_13, "previsto_14": previsto_14,
    }


def _numero(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",") if valor < 10 else f"{valor:.0f}"


def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def reais(valor: float) -> str:
    """R$ 6,00 (vírgula decimal, como o resto do texto novo)."""
    return f"R$ {valor:.2f}".replace(".", ",")


def frase_da_calibracao(freq: dict | None) -> str:
    """O texto que fica ao lado da chance mostrada. Sem base suficiente, diz isso."""
    if not freq or freq["concursos"] < config.CALIBRACAO_MIN_CONCURSOS:
        return (
            "Ainda não há concursos passados suficientes no banco para comparar esta chance com o que aconteceu "
            f"(mínimo {config.CALIBRACAO_MIN_CONCURSOS}). Trate o número acima como limite superior."
        )
    return (
        f"O que aconteceu de fato: em {_milhar(freq['concursos'])} concursos passados, bilhetes com os mesmos "
        f"{freq['duplos']} duplo(s) e {freq['triplos']} triplo(s) ({reais(freq['custo'])}), montados pela regra "
        f"do app, fizeram 13 ou mais em {freq['fez_13_ou_mais']} e 14 em {freq['fez_14']}. Pelos percentuais, "
        f"o app previa {_numero(freq['previsto_13_ou_mais'])} e {_numero(freq['previsto_14'])}. "
        "Os percentuais são mais confiantes do que a realidade: leia o número acima como limite superior, não como expectativa."
    )


def efeito_medido_das_trocas(concursos: list[list[tuple[dict, str]]], duplos: int, triplos: int) -> dict | None:
    """Acertos a mais, em média, ao aplicar a melhor troca de um passo num bilhete montado sem
    critério (stats.estudo_sugestoes.avaliar_trocas). None sem base ou combinação inválida."""
    if len(concursos) < config.CALIBRACAO_MIN_CONCURSOS or duplos + triplos < 1 or duplos + triplos > 14:
        return None
    resultado = avaliar_trocas(concursos, duplos, triplos)
    return resultado if resultado.get("com_sugestao") else None


def frase_do_efeito(efeito: dict | None) -> str:
    if not efeito:
        return ""
    media = f"{efeito['diferenca_media']:+.2f}".replace(".", ",")
    return (
        f"Nos {_milhar(efeito['concursos'])} concursos testados, aplicar uma alteração assim num bilhete montado sem critério "
        f"rendeu {media} acerto por concurso em média (ganhou em {efeito['ganhou']}, perdeu em {efeito['perdeu']}). "
        "Ajuda pouco e sozinha não leva a 13 ou 14."
    )

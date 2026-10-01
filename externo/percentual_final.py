"""Percentual final de um jogo = percentual histórico + ajuste externo da
última varredura do concurso (ver externo/ajuste.py: aplicar_ajuste).

Calculado na hora com o histórico atual, aplicando os ajustes GUARDADOS em
`fatores_externos`; `percentuais` fica como registro do que a varredura gravou.
"""
import json

from externo.ajuste import aplicar_ajuste
from stats.calibracao import calibrar_jogo
from stats.percentual import percentual_historico


def ajustes_do_concurso(conexao, numero_concurso: int) -> dict[int, dict]:
    """Última varredura de cada participante no concurso:
    {participante_id: {ajuste, resumo, evidencias, coletado_em}}."""
    linhas = conexao.execute(
        "SELECT participante_id, ajuste_aplicado, resumo, evidencias, coletado_em FROM fatores_externos "
        "WHERE concurso_numero = ? ORDER BY coletado_em, id",
        (numero_concurso,),
    ).fetchall()
    ajustes = {}
    for linha in linhas:
        try:
            evidencias = json.loads(linha["evidencias"]) if linha["evidencias"] else []
        except ValueError:
            evidencias = []
        ajustes[linha["participante_id"]] = {
            "ajuste": linha["ajuste_aplicado"] or 0.0,
            "resumo": linha["resumo"],
            "evidencias": evidencias,
            "coletado_em": linha["coletado_em"],
        }
    return ajustes


def percentuais_do_jogo(conexao, casa_id: int, fora_id: int, ajustes: dict[int, dict]) -> dict:
    """Percentual do jogo em três camadas: `original` (modelo, sem correção), `historico` (a base do app: o original
    já com a calibração quando ela se aplica) e `final` (a base mais o ajuste das notícias). O deslocamento das
    notícias é sempre medido contra `historico`. `calibracao` explica a correção (origem, parâmetros, motivo)."""
    original = percentual_historico(conexao, casa_id, fora_id)
    calibracao = calibrar_jogo(conexao, casa_id, fora_id, original)
    historico = calibracao["calibrado"]
    da_casa, do_fora = ajustes.get(casa_id), ajustes.get(fora_id)
    resultado = aplicar_ajuste(historico, da_casa["ajuste"] if da_casa else 0.0, do_fora["ajuste"] if do_fora else 0.0)
    return {
        "original": original,
        "calibracao": calibracao,
        "historico": historico,
        "final": resultado["final"],
        "deslocamento": resultado["deslocamento"],
        "ajustado": abs(resultado["deslocamento"]) > 1e-9,
        "ajustes": {
            "casa": da_casa if da_casa and da_casa["ajuste"] else None,
            "fora": do_fora if do_fora and do_fora["ajuste"] else None,
        },
    }

"""Percentual final de um jogo = percentual histórico + ajuste externo da
última varredura do concurso (ver externo/ajuste.py: aplicar_ajuste).

Calculado na hora com o histórico atual, aplicando os ajustes GUARDADOS em
`fatores_externos`; `percentuais` fica como registro do que a varredura gravou.
"""
import json

from externo.ajuste import aplicar_ajuste
from stats.calibracao import calibrar_jogo
from stats.modelo_cbf import ORIGEM as ORIGEM_CBF
from stats.modelo_cbf import prever as prever_cbf
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


def percentuais_do_jogo(conexao, casa_id: int, fora_id: int, ajustes: dict[int, dict], data_jogo: str | None = None) -> dict:
    """Percentual do jogo em três camadas: `original` (modelo, sem correção), `historico` (a base do app: o original
    já com a calibração quando ela se aplica) e `final` (a base mais o ajuste das notícias). O deslocamento das
    notícias é sempre medido contra `historico`. `calibracao` explica a correção (origem, parâmetros, motivo).

    Com `data_jogo`, jogo entre clubes da mesma série A ou B usa o modelo da temporada da CBF (item B2 do plano
    v2), sem calibração; `anterior` traz o que o modelo anterior daria (base corrigida), para a tela mostrar os
    dois lado a lado. Nos demais jogos, `anterior` é None."""
    anterior_calibrado = calibrar_jogo(conexao, casa_id, fora_id, percentual_historico(conexao, casa_id, fora_id))
    cbf = prever_cbf(conexao, casa_id, fora_id, data_jogo)
    if cbf is not None:
        original, anterior = cbf, anterior_calibrado["calibrado"]
        calibracao = {"original": cbf, "calibrado": cbf, "origem": ORIGEM_CBF, "aplicada": False, "expoente": None,
                      "mistura": None, "motivo": "origem não corrigida"}
    else:
        original, anterior, calibracao = anterior_calibrado["original"], None, anterior_calibrado
    historico = calibracao["calibrado"]
    da_casa, do_fora = ajustes.get(casa_id), ajustes.get(fora_id)
    resultado = aplicar_ajuste(historico, da_casa["ajuste"] if da_casa else 0.0, do_fora["ajuste"] if do_fora else 0.0)
    return {
        "original": original,
        "origem": calibracao["origem"],
        "anterior": anterior,
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

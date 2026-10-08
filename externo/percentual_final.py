"""Percentual final de um jogo = percentual histórico + ajuste externo da
última varredura do concurso (ver externo/ajuste.py: aplicar_ajuste).

Calculado na hora com o histórico atual, aplicando os ajustes GUARDADOS em
`fatores_externos`; `percentuais` fica como registro do que a varredura gravou.
"""
import json

from externo.ajuste import aplicar_ajuste
from stats.calibracao import calibrar_jogo
from stats.elo_clubes import ORIGEM as ORIGEM_ELO
from stats.elo_clubes import prever as prever_elo
from stats.modelo_cbf import ORIGEM as ORIGEM_CBF
from stats.modelo_cbf import prever as prever_cbf

ORIGEM_CBF_E_ELO = "temporada_cbf_e_elo"
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

    Com `data_jogo`, e sem calibração (os estudos mostraram que ela não ajuda nestes modelos):
    - clubes da mesma série A ou B: média entre o modelo da temporada da CBF e o Elo de clubes (estudo S2,
      docs/s2-elo-de-clubes-08-10-2026.md); só a temporada se o Elo estiver desligado;
    - demais jogos entre dois clubes: Elo de clubes (mesmo estudo);
    - seleções e o resto: como antes (Elo das seleções ou Poisson histórico calibrado).
    `anterior` traz o que o modelo anterior (Poisson histórico calibrado) daria, para a tela mostrar os dois lado a
    lado; None quando o modelo anterior é o que está em uso."""
    anterior_calibrado = calibrar_jogo(conexao, casa_id, fora_id, percentual_historico(conexao, casa_id, fora_id))
    cbf = prever_cbf(conexao, casa_id, fora_id, data_jogo)
    elo = prever_elo(conexao, casa_id, fora_id, data_jogo)
    if cbf is not None and elo is not None:
        novo, origem = {c: (cbf[c] + elo[c]) / 2 for c in ("1", "X", "2")}, ORIGEM_CBF_E_ELO
    elif cbf is not None:
        novo, origem = cbf, ORIGEM_CBF
    elif elo is not None and anterior_calibrado["origem"] != "elo_selecoes":
        novo, origem = elo, ORIGEM_ELO
    else:
        novo, origem = None, None
    if novo is not None:
        original, anterior = novo, anterior_calibrado["calibrado"]
        calibracao = {"original": novo, "calibrado": novo, "origem": origem, "aplicada": False, "expoente": None,
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

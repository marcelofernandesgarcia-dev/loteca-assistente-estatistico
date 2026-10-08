"""Apresentação da calibração dos percentuais (E4, Fase 2): explica ao usuário que o percentual de cada jogo
foi corrigido, de que origem ele vem e quanto mudou. As contas estão em stats/calibracao.py; as funções de texto
são puras para poderem ser testadas sem o Streamlit."""
import html

import streamlit as st
from estilo_caixa import renderizar_tabela

import config
from stats.calibracao import ORIGEM_TEXTO


def _tres(pct: dict) -> str:
    return " / ".join(f"{pct[c]:.0f}" for c in ("1", "X", "2"))


def _virgula(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def frase_da_correcao(calibracao: dict) -> str:
    """Uma frase curta sobre o que foi feito com o percentual deste jogo."""
    if calibracao["aplicada"]:
        return f"corrigido (expoente {_virgula(calibracao['expoente'])}, mistura {_virgula(calibracao['mistura'])})"
    motivo = calibracao["motivo"]
    if motivo == "origem não corrigida" and calibracao.get("origem") in ("retrospecto_cbf", "temporada_cbf_e_elo", "elo_clubes"):
        return "sem correção (no teste, a correção não melhorou este modelo)"
    if motivo == "origem não corrigida":
        return "sem correção (o Elo das seleções já está calibrado)"
    if motivo == "interruptor desligado":
        return "sem correção (desligada por LOTECA_CALIBRACAO=0)"
    if motivo == "sem parâmetros gravados":
        return "sem correção (parâmetros ainda não calculados)"
    return "sem correção"


def linhas_calibracao(jogos: list[dict], calculos: dict[int, dict]) -> list[list[str]]:
    """Uma linha por jogo: origem, percentual do modelo, base corrigida, final com notícias e a correção feita."""
    linhas = []
    for j in jogos:
        c = calculos[j["id"]]
        cal = c["calibracao"]
        linhas.append([
            f"{j['num_jogo']}. {html.escape(j['casa'])} x {html.escape(j['fora'])}",
            html.escape(ORIGEM_TEXTO.get(cal["origem"], cal["origem"])),
            _tres(c["original"]),
            _tres(c["historico"]),
            _tres(c["final"]),
            html.escape(frase_da_correcao(cal)),
            _tres(c["anterior"]) if c.get("anterior") else "-",
        ])
    return linhas


CABECALHOS = ["Jogo", "Origem do percentual", "Do modelo (1 / X / 2)", "Base do app (corrigida)", "Final (com notícias)",
              "Correção", "Modelo anterior, para comparar"]


def resumo_do_concurso(calculos: dict[int, dict]) -> str:
    """Quantos jogos foram corrigidos e quantos não, em uma frase."""
    total = len(calculos)
    corrigidos = sum(1 for c in calculos.values() if c["calibracao"]["aplicada"])
    if not config.CALIBRACAO_ATIVA:
        return "A calibração está desligada: os percentuais são os do modelo, sem correção."
    if corrigidos == 0:
        return "Nenhum jogo deste concurso foi corrigido (origem sem correção ou parâmetros ainda não calculados)."
    return (
        f"{corrigidos} de {total} jogos tiveram o percentual corrigido pela calibração; os demais usam o percentual do modelo sem correção."
    )


def mostrar_calibracao(jogos: list[dict], calculos: dict[int, dict]) -> None:
    """Legenda e quadro 'como o percentual foi corrigido' logo abaixo do card de percentuais."""
    st.caption(
        resumo_do_concurso(calculos)
        + " A calibração existe porque, nos concursos passados, os percentuais do modelo eram confiantes demais: "
        "quando diziam 60% a 70%, o resultado acontecia em cerca de 52% das vezes. Corrigidos, ficam próximos do que de fato acontece."
    )
    with st.expander("Ver como cada percentual foi corrigido"):
        st.markdown(
            renderizar_tabela("Percentual do modelo, base corrigida e final, por jogo", CABECALHOS, linhas_calibracao(jogos, calculos)),
            unsafe_allow_html=True,
        )
        st.caption(
            "A correção achata os percentuais exagerados e mistura uma parte da frequência histórica geral de 1/X/2. Os parâmetros "
            "são refeitos a cada concurso apurado, só com o passado. O ajuste de notícias entra depois, sobre a base corrigida."
        )
        st.caption(
            "Clubes da mesma série A ou B: média entre o modelo da temporada da CBF (pontos por jogo até o dia) e o Elo "
            "de clubes. Demais jogos entre clubes: Elo de clubes, calculado com todos os jogos da Loteca. Os dois foram "
            "adotados depois de testados sem olhar o futuro (docs/b2-jogos-da-loteca-07-10-2026.md e "
            "docs/s2-elo-de-clubes-08-10-2026.md). A última coluna mostra o que o modelo anterior daria, para comparar. "
            "Para voltar ao anterior: LOTECA_ELO_CLUBES=0 e LOTECA_MODELO_CLUBES=historico."
        )

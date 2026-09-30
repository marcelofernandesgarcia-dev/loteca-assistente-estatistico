"""Blocos de tela das recomendações do estudo E1-E4 (aprovadas em 30/09/2026): complexidade
de cada jogo, sugestões de alteração pelo mesmo custo, economia e o que aconteceu de fato
com bilhetes do mesmo custo. Só apresentação: as contas estão em stats/sugestoes_bilhete.py
e stats/calibracao_bilhete.py."""
import html
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import db
from stats.calibracao_bilhete import (
    concursos_para_calibracao,
    efeito_medido_das_trocas,
    frase_da_calibracao,
    frase_do_efeito,
    frequencia_por_custo,
    versao_dos_dados,
)
from stats.sugestoes_bilhete import (
    complexidade_dos_jogos,
    frase_da_economia,
    frase_da_troca,
    marcacao_contra_o_favorito,
    montar_sugestoes,
)

log = logging.getLogger("loteca.sugestoes")
NOME_NIVEL = {"baixa": "baixa", "media": "média", "alta": "alta"}


@st.cache_resource(show_spinner=False)
def _concursos_passados(versao: tuple):
    """Os concursos passados com o percentual de cada época; refeito só quando entra concurso novo."""
    conexao = db.conectar()
    try:
        return concursos_para_calibracao(conexao)
    finally:
        conexao.close()


@st.cache_data(show_spinner=False)
def _frequencia(versao: tuple, duplos: int, triplos: int):
    return frequencia_por_custo(_concursos_passados(versao), duplos, triplos)


@st.cache_data(show_spinner=False)
def _efeito(versao: tuple, duplos: int, triplos: int):
    return efeito_medido_das_trocas(_concursos_passados(versao), duplos, triplos)


def texto_da_calibracao(conexao, duplos: int, triplos: int) -> str:
    """A frase do que aconteceu de fato; se a base de teste falhar, a tela segue com o aviso genérico."""
    try:
        return frase_da_calibracao(_frequencia(versao_dos_dados(conexao), duplos, triplos))
    except Exception as erro:  # a análise do palpite não pode cair por causa do teste de apoio
        log.error("calibração indisponível: %s", type(erro).__name__)
        return frase_da_calibracao(None)


def texto_do_efeito(conexao, duplos: int, triplos: int) -> str:
    try:
        return frase_do_efeito(_efeito(versao_dos_dados(conexao), duplos, triplos))
    except Exception as erro:
        log.error("efeito medido indisponível: %s", type(erro).__name__)
        return ""


def complexidade_da_tela(jogos: list[dict], resumo_ano: list[dict]) -> dict[int, dict]:
    """{num_jogo: complexidade}. `jogos`: num_jogo, pct, sem_base_propria. `resumo_ano`: de
    stats.ano_em_curso.resumo_do_concurso_no_ano (traz a diferença do ano em curso por jogo)."""
    return complexidade_dos_jogos(jogos, {r["num_jogo"]: r["diferenca"] for r in resumo_ano})


def texto_da_complexidade(comp: dict) -> str:
    """HTML seguro para a célula da tabela: nível e, se houver, os motivos."""
    motivos = "; ".join(html.escape(m) for m in comp["motivos"])
    nivel = NOME_NIVEL[comp["nivel"]]
    return f"<strong>{nivel}</strong>" + (f"<br><small>{motivos}</small>" if motivos else "")


def mostrar_sugestoes(conexao, analise: dict, duplos: int, triplos: int) -> None:
    """Sugestões de alteração pelo mesmo custo e leitura de economia, com o efeito medido.
    Nunca aumentam o custo nem o número de duplos e triplos já escolhidos."""
    sugestoes = montar_sugestoes(analise["jogos"])
    contra = marcacao_contra_o_favorito(analise["jogos"])
    st.markdown("**Sugestões de alteração, pelo mesmo custo**")
    if not sugestoes["trocas"] and not contra:
        st.markdown(
            "- Pelos percentuais do app, nenhuma troca simples aumenta a chance de acertar todos em 10% ou mais "
            "mantendo o custo. Isso não quer dizer que a marcação esteja certa."
        )
    for troca in sugestoes["trocas"]:
        st.markdown(f"- {frase_da_troca(troca)}")
    if contra:
        lista = ", ".join(map(str, contra))
        st.markdown(
            f"- Você marcou contra o favorito dos dados no(s) jogo(s) {lista}. Nos concursos testados, trocar esse tipo "
            "de marcação pela coluna favorita foi onde as alterações mais renderam. A decisão é sua: pode haver "
            "informação que o app não tem."
        )
    # O efeito medido é de "uma alteração assim": só faz sentido quando há alteração sugerida.
    efeito = texto_do_efeito(conexao, duplos, triplos) if (sugestoes["trocas"] or contra) else ""
    if efeito:
        st.caption(efeito)
    if sugestoes["economias"]:
        st.markdown("**Se quiser gastar menos** (pela menor perda de chance por real economizado)")
        for economia in sugestoes["economias"]:
            st.markdown(f"- {frase_da_economia(economia)}")
    st.caption(
        "As sugestões usam os percentuais do app e seguem a sua escolha de quantos duplos e triplos jogar: "
        "não aumentam o custo. A sugestão do próprio app continua em no máximo um duplo ou um triplo."
    )

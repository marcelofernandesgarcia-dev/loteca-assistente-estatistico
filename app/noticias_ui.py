"""Manchetes lidas pela varredura, com a decisão do filtro (item A3 do plano v2, 07/10/2026).
Só leitura do banco; quem decide é externo/analise.py (classificar_noticias)."""
import html

import streamlit as st
from estilo_caixa import renderizar_tabela

from externo.analise import MOTIVOS_DE_DESCARTE
from externo.varredura import noticias_lidas_do_concurso

NOME_SITUACAO = {
    "aplicada": "Mexe no percentual",
    "informativa": "Só informativa",
    "descartada": "Descartada",
    "sem_sinal": "Sem sinal",
}


def _nome_sinal(tipo: str) -> str:
    return tipo.replace("_", " ")


def _motivos(descartes: list[dict]) -> str:
    vistos = []
    for descarte in descartes:
        texto = MOTIVOS_DE_DESCARTE.get(descarte["motivo"], descarte["motivo"])
        if texto not in vistos:
            vistos.append(texto)
    return "; ".join(vistos)


def _link(url: str | None, titulo: str) -> str:
    seguro = html.escape(titulo)
    if url and url.startswith(("https://", "http://")):
        return f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">{seguro}</a>'
    return seguro


def mostrar_manchetes_lidas(conexao, numero_concurso: int, participantes: list[dict]) -> None:
    """`participantes`: [{'id', 'nome'}] do concurso, para dizer quem ficou sem leitura (diferente de
    "lido, sem sinal")."""
    lidas = noticias_lidas_do_concurso(conexao, numero_concurso)
    com_leitura = {n["participante_id"] for n in lidas}
    sem_leitura = [p["nome"] for p in participantes if p["id"] not in com_leitura]
    relevantes = [n for n in lidas if n["situacao"] != "sem_sinal"]
    contagem = {s: sum(1 for n in lidas if n["situacao"] == s) for s in NOME_SITUACAO}
    with st.expander(f"Manchetes lidas e decisão do filtro ({len(lidas)} manchetes)"):
        if not lidas:
            st.caption(
                "Nenhuma manchete registrada para este concurso. O registro de cada manchete começou em 07/10/2026; "
                "leituras anteriores guardaram só os sinais aceitos."
            )
            return
        st.caption(
            f"{contagem['aplicada']} mexem no percentual, {contagem['informativa']} são só informativas, "
            f"{contagem['descartada']} foram descartadas pelo filtro e {contagem['sem_sinal']} não tinham palavra de "
            "sinal. Vale a leitura mais recente de cada time."
        )
        if sem_leitura:
            st.warning("Sem leitura de notícias neste concurso: " + ", ".join(sem_leitura) + ".")
        if relevantes:
            linhas = [
                [
                    html.escape(n["participante"]), _link(n["url"], n["titulo"]), html.escape(n["fonte"] or "-"),
                    NOME_SITUACAO[n["situacao"]],
                    html.escape(", ".join(_nome_sinal(s) for s in n["aceitos"]) or "-"),
                    html.escape(_motivos(n["descartes"]) or "-"),
                ]
                for n in relevantes
            ]
            st.markdown(
                renderizar_tabela(
                    "Manchetes com palavra de sinal",
                    ["Time", "Manchete", "Veículo", "Decisão", "Sinal aceito", "Motivo do descarte"],
                    linhas,
                ),
                unsafe_allow_html=True,
            )

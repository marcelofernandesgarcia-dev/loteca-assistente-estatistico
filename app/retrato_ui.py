"""Exibe o retrato guardado ao salvar o bilhete (item A1 do plano v2, 07/10/2026). Só leitura."""
import datetime as dt
import html

import streamlit as st
from estilo_caixa import renderizar_tabela

NOME_ORIGEM = {
    "poisson": "histórico da Loteca (Poisson)",
    "elo_selecoes": "Elo das seleções",
    "frequencia_global": "frequência geral (sem base própria)",
}


def _pct(p: dict) -> str:
    return " / ".join(f"{p[c]:.0f}%" for c in ("1", "X", "2"))


def _noticias(noticias: dict) -> str:
    deslocamento = noticias.get("deslocamento") or 0.0
    lidas = [lado for lado in ("casa", "fora") if noticias.get(lado)]
    if not lidas:
        return "sem leitura"
    if abs(deslocamento) < 1e-9:
        return "lidas, sem efeito"
    a_favor = "mandante" if deslocamento > 0 else "visitante"
    return f"{abs(deslocamento):.1f} ponto(s) a favor do {a_favor}".replace(".", ",")


def mostrar_retrato(retrato: dict | None, chave: str) -> None:
    if retrato is None:
        st.caption("Bilhete salvo antes de 07/10/2026: o retrato completo do que o app mostrava não foi guardado.")
        return
    if not st.toggle("Ver o que o app mostrava ao salvar", key=chave):
        return
    geral = retrato["geral"] or {}
    linhas = [
        [
            f"{j['num_jogo']}. {html.escape(j['casa'])} x {html.escape(j['fora'])}",
            html.escape(NOME_ORIGEM.get(j["origem"], j["origem"])),
            _pct(j["percentual"]["final"]),
            html.escape(_noticias(j["noticias"])),
            ("⚠ " if j["cobertura"]["alta_incerteza"] else "") + html.escape(j["cobertura"]["nome_nivel"]),
            ", ".join(j["sugestao_do_app"]),
            ", ".join(j["marcacao"]),
        ]
        for j in retrato["jogos"]
    ]
    st.markdown(
        renderizar_tabela(
            "O que o app mostrava ao salvar",
            ["Jogo", "Origem do percentual", "Percentual 1 / X / 2", "Notícias", "Cobertura", "Sugestão do app",
             "Você marcou"],
            linhas,
        ),
        unsafe_allow_html=True,
    )
    salvo = dt.datetime.fromisoformat(geral["salvo_em"]).strftime("%d/%m/%Y %H:%M") if geral.get("salvo_em") else "-"
    st.caption(
        f"Guardado em {salvo}, versão do app {geral.get('versao_app', '-')}, calibração "
        f"{'ligada' if geral.get('calibracao_ativa') else 'desligada'}, regras de notícias de "
        f"{geral.get('versao_regras_noticias', '-')}. O retrato não muda depois de salvo."
    )

"""Blocos de tela do ANO EM CURSO, usados na página inicial e no Concurso atual
(pedido do usuário, 30/09/2026: sempre visível, como prioridade). Só
apresentação: as contas estão em stats/ano_em_curso.py."""
import html
import logging
import os
import sys
from pathlib import Path

# Como em util.py: a raiz do projeto precisa estar no caminho antes de importar
# config e stats (este módulo pode ser importado antes de util).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st
from estilo_caixa import renderizar_tabela
from paleta import AZUL, CINZA_CLARO

import config
from stats.ano_em_curso import cobertura, frase_do_lado, resumo_do_concurso_no_ano
from stats.selecoes import carregar_nomes, carregar_resultados

log = logging.getLogger("loteca.ano_em_curso")


@st.cache_data(show_spinner=False)
def _base_selecoes(_marca: tuple):
    return carregar_resultados(), carregar_nomes()


def base_selecoes():
    """(jogos, nomes) da base aberta de seleções, ou (None, None) se ela não estiver
    disponível: a tela continua funcionando e as seleções caem nos jogos da Loteca."""
    try:
        marca = (os.path.getmtime(config.SELECOES_BASE_CSV), os.path.getmtime(config.SELECOES_NOMES_CSV))
        return _base_selecoes(marca)
    except (OSError, KeyError, ValueError) as erro:
        log.warning("base de seleções indisponível para o ano em curso: %s", type(erro).__name__)
        return None, None


def resumo_do_ano(conexao, jogos: list[dict], ano: int) -> list[dict]:
    jogos_base, nomes = base_selecoes()
    return resumo_do_concurso_no_ano(conexao, jogos, ano, jogos_base, nomes)


def _nome(texto: str) -> str:
    return html.escape(texto.title())


def _celula_lado(lado: dict) -> str:
    return f"<strong>{_nome(lado['nome'])}</strong><br><small>{html.escape(frase_do_lado(lado))}</small>"


def _celula_diferenca(jogo: dict) -> str:
    d = jogo["diferenca"]
    if d is None:
        return "sem comparação (falta dado do ano de um lado)"
    if d["melhor"] is None:
        texto = "mesmo aproveitamento"
    else:
        lado = jogo[d["melhor"]]
        texto = f"{_nome(lado['nome'])} +{abs(d['pontos_percentuais']):.0f} p.p."
    avisos = []
    if d["fontes_diferentes"]:
        avisos.append("fontes diferentes")
    if d["amostra_pequena"]:
        avisos.append("amostra pequena")
    return texto + (f"<br><small>{', '.join(avisos)}: comparação frágil</small>" if avisos else "")


def tabela_jogo_a_jogo(resumo: list[dict], ano: int, complexidade: dict[int, str] | None = None) -> str:
    """`complexidade`: {num_jogo: HTML seguro da célula} (app/sugestoes_ui.texto_da_complexidade);
    sem ele a coluna não aparece."""
    cabecalhos = ["Jogo", "Mandante no ano", "Visitante no ano", "Quem vai melhor no ano"]
    linhas = [
        [str(j["num_jogo"]), _celula_lado(j["casa"]), _celula_lado(j["fora"]), _celula_diferenca(j)]
        for j in resumo
    ]
    if complexidade:
        cabecalhos.append("Complexidade do jogo")
        for linha, j in zip(linhas, resumo):
            linha.append(complexidade.get(j["num_jogo"], "-"))
    return renderizar_tabela(f"Jogo a jogo em {ano}", cabecalhos, linhas)


def grafico_aproveitamento(resumo: list[dict], ano: int) -> go.Figure | None:
    """Barras horizontais do aproveitamento no ano de todos os participantes. A amostra
    pequena é dita no rótulo (não só pela cor mais clara)."""
    lados = [l for j in resumo for l in (j["casa"], j["fora"]) if l["aproveitamento"] is not None]
    if not lados:
        return None
    lados.sort(key=lambda l: l["aproveitamento"])
    rotulos = [f"{l['nome'].title()}{' (amostra pequena)' if l['amostra_pequena'] else ''}" for l in lados]
    figura = go.Figure(
        go.Bar(
            x=[l["aproveitamento"] for l in lados], y=rotulos, orientation="h",
            marker=dict(color=[CINZA_CLARO if l["amostra_pequena"] else AZUL for l in lados],
                        line=dict(color=AZUL, width=1)),
            text=[f"{l['aproveitamento']:.0f}% · {l['jogos']} jogos" for l in lados], textposition="outside",
            hovertemplate="%{y}: %{x:.0f}%<extra></extra>",
        )
    )
    figura.update_layout(
        title=f"Aproveitamento em {ano} (pontos: vitória 3, empate 1)", height=max(320, 24 * len(lados) + 80),
        margin=dict(l=10, r=10, t=50, b=30), xaxis=dict(range=[0, 115], title="%"), yaxis=dict(title=None),
        showlegend=False,
    )
    return figura


def mostrar_ano_em_curso(conexao, jogos: list[dict], ano: int, chave: str, com_grafico: bool = True,
                         resumo: list[dict] | None = None, complexidade: dict[int, str] | None = None) -> list[dict]:
    """Bloco completo: números de cobertura, gráfico e jogo a jogo. Devolve o resumo
    (passe `resumo` se ele já foi calculado, para não repetir a conta)."""
    resumo = resumo if resumo is not None else resumo_do_ano(conexao, jogos, ano)
    c = cobertura(resumo)
    st.caption(
        f"Fonte de cada participante, da mais completa para a mais pobre: classificação da CBF ({c['cbf']}), "
        f"jogos de seleções do ano na base aberta ({c['selecoes']}), jogos do ano na grade da Loteca ({c['loteca']}). "
        f"Sem jogos de {ano}: {c['sem_dado']}. É o que aconteceu no ano, não previsão do jogo."
    )
    if com_grafico:
        figura = grafico_aproveitamento(resumo, ano)
        if figura:
            st.plotly_chart(figura, width="stretch", key=f"grafico_ano_{chave}")
    st.markdown(tabela_jogo_a_jogo(resumo, ano, complexidade), unsafe_allow_html=True)
    return resumo

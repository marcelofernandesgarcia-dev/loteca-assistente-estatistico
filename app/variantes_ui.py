"""Tela dos bilhetes alternativos a partir do volante (pedido do usuário, 08/10/2026). Só apresentação: as contas
estão em stats/variantes_bilhete.py. As funções de texto são puras para poderem ser testadas sem o Streamlit."""
import html
from typing import Callable

import streamlit as st
from chances_ui import reais
from estilo_caixa import renderizar_tabela
from sugestoes_ui import texto_da_calibracao, texto_do_efeito

from stats.analise_palpite import ZEBRA, classificar_jogo, formatar_uma_em
from stats.variantes_bilhete import NOMES, gerar_variantes
from stats.versoes_palpite import frase_da_mudanca

CABECALHOS = ["Bilhete", "Apostas (custo)", "Chance de 14 (pelos percentuais)", "Chance de 13 ou mais (pelos percentuais)",
              "Acertos esperados", "Duplos / triplos", "Zebras", "Jogos mudados", "Virou bilhete"]


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def zebras(pcts: list[dict], marcacoes: list[list[str]]) -> int:
    """Jogos marcados só em resultado de pouca chance, pela mesma regra da análise do palpite."""
    return sum(1 for p, m in zip(pcts, marcacoes) if classificar_jogo(p, m)["categoria"] == ZEBRA)


def _linha(nome: str, medidas: dict, n_zebras: int, mudados: str, salvo: int | None) -> list[str]:
    return [
        nome, f"{medidas['apostas']} ({reais(medidas['custo'])})", formatar_uma_em(medidas["chance_14"]),
        formatar_uma_em(medidas["chance_13_ou_mais"]), _decimal(medidas["acertos_esperados"]),
        f"{medidas['duplos']} / {medidas['triplos']}", str(n_zebras), mudados,
        f"sim (nº {salvo})" if salvo else "não",
    ]


def linhas_da_comparacao(resultado: dict, extras: list[tuple[int, int | None]]) -> list[list[str]]:
    """O seu bilhete e cada variante, lado a lado, nas colunas da tabela de versões. `extras`: (zebras, nº do bilhete
    salvo com a mesma marcação ou None), primeiro o do seu bilhete e depois o de cada variante, na mesma ordem."""
    zebras_base, salvo_base = extras[0]
    linhas = [_linha("Seu bilhete (volante)", resultado["base"], zebras_base, "-", salvo_base)]
    for i, (v, (n_zebras, salvo)) in enumerate(zip(resultado["variantes"], extras[1:]), start=1):
        mudados = ", ".join(str(m["num_jogo"]) for m in v["mudancas"])
        linhas.append(_linha(f"{i}. {v['nome']}", v["medidas"], n_zebras, mudados, salvo))
    return linhas


def frase_do_premio_dividido(variante: dict, base: dict) -> str | None:
    """Aviso aprovado pelo usuário (08/10/2026, item 5): só texto, sem valor em reais."""
    if not variante["mais_favoritos_que_a_base"]:
        return None
    return (
        f"Esta alternativa marca só o favorito em {variante['favoritos_secos']} jogo(s); o seu bilhete, em "
        f"{base['favoritos_secos']}. Bilhete com mais favoritos se parece mais com o da maioria: se acertar, o prêmio "
        "tende a ser dividido com mais gente (estudos anti-manada e D6: nos concursos com muitos ganhadores, os "
        "favoritos se confirmaram mais)."
    )


def frase_do_custo(variante: dict) -> str:
    if variante["economia"] > 0:
        return f"Custa {reais(variante['medidas']['custo'])}: {reais(variante['economia'])} a menos que o seu."
    return f"Mesmo custo do seu: {reais(variante['medidas']['custo'])}."


def mostrar_variantes(
    conexao,
    numero_concurso: int,
    pcts: list[dict],
    marcacoes: list[list[str]],
    numeros: list[int],
    ao_levar: Callable[[list[list[str]]], None],
    ao_salvar: Callable[[dict], None],
    ao_confirmar: Callable[[dict], None],
    bilhete_salvo: Callable[[list[list[str]]], int | None],
) -> None:
    """Monta e mostra até três alternativas. `ao_levar` roda como callback do botão (antes de o volante ser
    redesenhado); `ao_salvar` grava ou pede confirmação; `ao_confirmar` mostra o aviso de bilhete igual ou de bilhete
    salvo, se houver; `bilhete_salvo` devolve o nº do bilhete já salvo com aquela marcação, ou None."""
    try:
        resultado = gerar_variantes(pcts, marcacoes, numeros)
    except ValueError as erro:
        st.info(str(erro))
        return
    extras = [(zebras(pcts, m), bilhete_salvo(m)) for m in [marcacoes] + [v["marcacoes"] for v in resultado["variantes"]]]
    st.markdown(renderizar_tabela("Seu bilhete e as alternativas", CABECALHOS, linhas_da_comparacao(resultado, extras)),
                unsafe_allow_html=True)
    st.caption(
        "As chances são calculadas pelos percentuais do app e servem para comparar os bilhetes entre si. No teste com "
        "1.127 concursos passados, alterações assim renderam pouco (cerca de um acerto a mais a cada três concursos, quase "
        "tudo vindo de desfazer marcação contra o favorito) e nenhuma estratégia fez 14."
    )
    for sem in resultado["sem_variante"]:
        st.caption(f"Sem bilhete “{html.escape(NOMES[sem['tipo']])}”: {sem['motivo']}.")
    if not resultado["variantes"]:
        return
    for i, v in enumerate(resultado["variantes"], start=1):
        with st.container(border=True):
            st.markdown(f"**{i}. {v['nome']}** — {v['descricao']}")
            st.markdown("\n".join(f"- {frase_da_mudanca(m)}" for m in v["mudancas"]))
            # "\$": com dois cifrões no mesmo texto, o Streamlit lê o trecho entre eles como fórmula e some com o "$".
            st.caption((frase_do_custo(v) + " Como foi montado: " + "; ".join(v["passos"]) + ".").replace("$", "\\$"))
            aviso = frase_do_premio_dividido(v, resultado["base"])
            if aviso:
                st.caption(aviso)
            medidas = v["medidas"]
            st.caption(texto_da_calibracao(conexao, medidas["duplos"], medidas["triplos"]))
            if v["tipo"] == "ajuste_leve":
                efeito = texto_do_efeito(conexao, medidas["duplos"], medidas["triplos"])
                if efeito:
                    st.caption(efeito)
            with st.container(horizontal=True):
                st.button("Levar ao volante", key=f"variante_levar_{numero_concurso}_{v['tipo']}", on_click=ao_levar,
                          args=(v["marcacoes"],),
                          help="Põe estas marcações no volante, acima, para você mexer antes de salvar.")
                salvar = st.button("Salvar como meu bilhete", key=f"variante_salvar_{numero_concurso}_{v['tipo']}",
                                   help="Grava como bilhete seu, com a origem anotada para comparar depois do resultado.")
            if salvar:
                ao_salvar(v)
            ao_confirmar(v)
    st.caption(
        "Se você salvar e apostar mais de um bilhete, o gasto se soma. Em 'Meus bilhetes' dá para ver a chance do "
        "conjunto e, depois do resultado, se a alternativa acertou mais ou menos que o seu volante."
    )

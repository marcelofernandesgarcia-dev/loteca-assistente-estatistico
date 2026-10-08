"""Tela do termômetro do perfil do concurso (S6, aprovado em 08/10/2026). Só apresentação: as contas estão em
stats/perfil_concurso.py. As funções de texto são puras para poderem ser testadas sem o Streamlit."""
import logging

import streamlit as st
from estilo_caixa import renderizar_tabela

import db
from stats.calibracao_bilhete import versao_dos_dados
from stats.perfil_concurso import avaliar, preparar

log = logging.getLogger("loteca.perfil")


def _decimal(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _taxa(registro: dict) -> str:
    if not registro["concursos"]:
        return "sem concursos nesta faixa"
    return f"{registro['pulverizados']} de {registro['concursos']} ({_decimal(100 * registro['taxa'], 0)}%)"


def frase_principal(resultado: dict, preparo: dict) -> str:
    acima = round(100 * resultado["posicao"])
    return (
        f"**Perfil do concurso (informativo): {resultado['nome_faixa']}.** Pelos sinais de antes do prazo, este concurso "
        f"tende a ter mais ganhadores que {acima}% dos {preparo['concursos']} concursos passados."
    )


def frase_da_medida(resultado: dict, preparo: dict) -> str:
    teste, faixas = preparo["teste"], preparo["faixas"]
    return (
        f"Nos concursos passados da mesma faixa, {_taxa(faixas[resultado['faixa']])} tiveram muitos ganhadores (os 10% "
        f"com mais ganhadores no ano); no geral, {_taxa(faixas['geral'])}. Medida fora da amostra: cada ano previsto só "
        f"com os anos anteriores. Acerto do termômetro: área sob a curva ROC de {_decimal(teste['auc'], 3)} (IC 95%: "
        f"{_decimal(teste['ic_inferior'], 3)} a {_decimal(teste['ic_superior'], 3)}); 0,5 é o acaso. É um sinal fraco: "
        "não muda a sugestão, não diz quais jogos vão sair e não estima prêmio."
    )


def frase_da_manada(resultado: dict) -> str | None:
    if resultado["faixa"] != "favoritos":
        return None
    return ("Num concurso de perfil de favoritos, quem marca os favoritos tende a dividir o prêmio com mais gente, "
            "se acertar (estudos anti-manada e D6).")


def linhas_dos_sinais(resultado: dict) -> list[list[str]]:
    linhas = []
    for s in resultado["sinais"]:
        if s["chave"] in ("anterior_acumulou", "final_0_ou_5"):
            valor = "sim" if s["valor"] >= 0.5 else "não"
            if s["chave"] == "anterior_acumulou" and resultado["anterior_desconhecido"]:
                valor = "ainda sem resultado (fica neutro)"
            media = f"{_decimal(100 * s['media'], 0)}% dos concursos"
        else:
            valor, media = _decimal(s["valor"]), _decimal(s["media"])
        linhas.append([s["descricao"], valor, media])
    return linhas


@st.cache_resource(show_spinner=False)
def _preparo(versao: tuple):
    """Refeito só quando entra concurso apurado novo (cerca de 2 segundos no banco real)."""
    conexao = db.conectar()
    try:
        return preparar(conexao)
    finally:
        conexao.close()


def mostrar_perfil_do_concurso(conexao, numero_concurso: int, jogos: list[dict]) -> None:
    """`jogos`: como em stats.estudo_d6.sinais_dos_jogos ('p', 'casa', 'fora'), na ordem do concurso."""
    try:
        preparo = _preparo(versao_dos_dados(conexao))
    except Exception as erro:  # o termômetro é informativo: a página segue sem ele
        log.error("termômetro do perfil indisponível: %s", type(erro).__name__)
        st.caption("Perfil do concurso: não foi possível calcular agora. O resto da página não depende dele.")
        return
    if preparo is None:
        st.caption("Perfil do concurso: ainda não há concursos passados suficientes no banco para o termômetro.")
        return
    linha = conexao.execute("SELECT acumulado FROM concursos WHERE numero = ?", (numero_concurso - 1,)).fetchone()
    anterior = None if linha is None or linha["acumulado"] is None else bool(linha["acumulado"])
    resultado = avaliar(preparo, jogos, numero_concurso, anterior)
    if not resultado["disponivel"]:
        st.caption(f"Perfil do concurso: {resultado['motivo']}.")
        return
    with st.container(border=True):
        st.markdown(frase_principal(resultado, preparo))
        st.caption(frase_da_medida(resultado, preparo))
        manada = frase_da_manada(resultado)
        if manada:
            st.caption(manada)
        with st.expander("Sinais do concurso e a média dos concursos passados"):
            st.markdown(renderizar_tabela("Sinais de antes do prazo", ["Sinal", "Este concurso", "Média dos passados"],
                                          linhas_dos_sinais(resultado)), unsafe_allow_html=True)

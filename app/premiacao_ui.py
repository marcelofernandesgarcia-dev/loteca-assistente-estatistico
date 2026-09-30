"""Blocos de tela dos valores de cada concurso (pedido do usuário, 30/09/2026). Só
apresentação: as contas estão em stats/premiacao.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from estilo_caixa import renderizar_tabela

from stats.premiacao import reais, resumo_por_numero


def _inteiro(valor: int | None) -> str:
    return "sem dado" if valor is None else f"{valor:,}".replace(",", ".")


def _linhas_das_faixas(resumo: dict) -> list[list[str]]:
    linhas = []
    for f in resumo["faixas"]:
        ganhadores = f["ganhadores"]
        valor = "ninguém acertou" if ganhadores == 0 else reais(f["valor_por_ganhador"])
        linhas.append([
            f["nome"], _inteiro(ganhadores), valor,
            reais(f["total"]) if ganhadores != 0 else reais(0.0),
        ])
    return linhas


def mostrar_premiacao(conexao, numero: int, rotulo: str | None = None, com_titulo: bool = True) -> dict | None:
    """Premiação de um concurso apurado: arrecadação, ganhadores e prêmio por faixa, total pago e
    acumulados. Devolve o resumo (ou None se o concurso não existe). `com_titulo=False` quando a
    página já pôs o próprio título de seção."""
    resumo = resumo_por_numero(conexao, numero)
    if resumo is None:
        st.info(f"Concurso {numero} não encontrado.")
        return None
    if com_titulo:
        st.markdown(f"#### {rotulo or f'Valores do concurso {numero}'}")
    if not resumo["faixas"]:
        st.info(
            "Este concurso ainda não tem premiação registrada (não foi apurado). A estimativa do prêmio do próximo "
            f"concurso publicada pela CAIXA é {reais(resumo['estimativa_proximo'])}."
        )
        return resumo

    with st.container(horizontal=True, wrap=True):
        st.metric("Arrecadação total", reais(resumo["arrecadado"]), border=True,
                  help="Valor publicado pela CAIXA para o concurso.")
        st.metric("Total pago nas faixas", reais(resumo["total_pago"]), border=True,
                  help="Soma de ganhadores x valor por ganhador nas faixas de 14 e de 13 acertos. Já desconta o "
                       "Imposto de Renda e inclui valor acumulado de concursos anteriores: não é retorno sobre a arrecadação.")
        st.metric("Apostas premiadas", _inteiro(resumo["ganhadores_total"]), border=True)
    if resumo["sem_ganhador_14"]:
        st.info("Ninguém acertou os 14 jogos neste concurso: o prêmio da 1ª faixa acumulou para o seguinte.")

    st.markdown(
        renderizar_tabela(
            f"Premiação do concurso {numero}",
            ["Faixa", "Ganhadores", "Prêmio por ganhador", "Total pago na faixa"],
            _linhas_das_faixas(resumo),
        ),
        unsafe_allow_html=True,
    )

    acumulados = [
        ("Acumulado para o próximo concurso de final zero ou cinco", resumo["acumulado_final_0_5"]),
        ("Acumulado para a Loteca Especial", resumo["acumulado_especial"]),
        ("Acumulado na 1ª faixa do próximo concurso", resumo["acumulado_proximo"]),
        ("Estimativa de prêmio do próximo concurso", resumo["estimativa_proximo"]),
    ]
    st.markdown(
        renderizar_tabela(
            "O que segue para os próximos concursos", ["Item", "Valor"], [[nome, reais(valor)] for nome, valor in acumulados]
        ),
        unsafe_allow_html=True,
    )

    with st.expander("Regra oficial de distribuição e o que os números mostram"):
        st.caption(
            "Regra do Manual de Produtos das Loterias CAIXA v21 (item 6.3.4): 55% da arrecadação vão para prêmios, com "
            "desconto do Imposto de Renda. Desse valor, 70% ficam na 1ª faixa (14 acertos), 10% na 2ª (13 acertos), 10% "
            "acumulam para a 1ª faixa dos concursos de final zero ou cinco e 10% para a Loteca Especial. Sem ganhador "
            "em uma faixa, o prêmio acumula para a 1ª faixa do concurso seguinte."
        )
        st.caption(
            "O app mostra o que a CAIXA publicou e não calcula valores por essa regra: medida nos dados, a relação entre o "
            "que foi pago e o que a regra prevê não é a mesma em todos os concursos. Nos concursos recentes, o acumulado "
            "para final zero ou cinco cresce de um concurso para o outro e volta a começar nos concursos de final 5 e 0, "
            "como a regra descreve."
        )
    return resumo

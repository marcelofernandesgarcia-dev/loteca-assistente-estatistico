import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from util import mostrar_aviso_responsabilidade

from stats.fechamento import calcular, consultar

st.title("Fechamento de bolão")
mostrar_aviso_responsabilidade()
st.write("Calculadora baseada na tabela oficial (Anexo I do Manual de Produtos das Loterias CAIXA v21).")

col1, col2 = st.columns(2)
triplos = col1.number_input("Triplos", min_value=0, max_value=6, value=0, step=1)
duplos = col2.number_input("Duplos", min_value=0, max_value=9, value=1, step=1)

oficial = consultar(triplos, duplos)
calculado = calcular(triplos, duplos)

st.metric("Apostas (combinações)", calculado["apostas"])
st.metric("Valor total", f"R$ {calculado['valor_reais']:.2f}")

if calculado["apostas"] > 864:
    st.warning("Essa combinação passa do máximo oficial de 864 apostas (5 duplos + 3 triplos).")

if oficial and oficial["cotas_min"]:
    st.subheader("Se organizar como Bolão CAIXA")
    st.write(
        f"Cotas: de {oficial['cotas_min']} a {oficial['cotas_max']} · "
        f"Valor mínimo da cota: R$ {oficial['valor_min_cota_reais']:.2f}"
    )
elif oficial:
    st.caption("Essa combinação não admite Bolão (menos de 3 duplos/1 triplo) -- só aposta direta.")

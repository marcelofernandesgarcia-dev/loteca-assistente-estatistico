import streamlit as st
from util import mostrar_aviso_responsabilidade, obter_conexao

st.set_page_config(page_title="Loteca -- Assistente Estatístico", page_icon="⚽", layout="wide")

st.title("Loteca -- Assistente Estatístico")
st.write(
    "Ferramenta pessoal de análise estatística da Loteca, para fortalecer a "
    "análise e reduzir risco e erro na escolha -- não prevê nem garante "
    "resultado, é jogo de azar. Use as páginas na barra lateral: **Concurso "
    "atual**, **Por concurso**, **Por time** e **Fechamento de bolão**."
)
mostrar_aviso_responsabilidade()

conexao = obter_conexao()
total_concursos = conexao.execute("SELECT COUNT(*) AS n FROM concursos").fetchone()["n"]
total_jogos = conexao.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
total_valorfinal = conexao.execute("SELECT COUNT(*) AS n FROM historico_valorfinal").fetchone()["n"]

col1, col2, col3 = st.columns(3)
col1.metric("Concursos importados (CAIXA)", total_concursos)
col2.metric("Jogos com time/placar", total_jogos)
col3.metric("Jogos no bootstrap (ValorFinal)", total_valorfinal)

if total_concursos == 0:
    st.info(
        "Ainda não foi importado nenhum concurso da CAIXA -- as páginas "
        "'Por time' e 'Concurso atual' vão ficar vazias até rodar a "
        "importação. Veja `README.md` para o comando."
    )
conexao.close()

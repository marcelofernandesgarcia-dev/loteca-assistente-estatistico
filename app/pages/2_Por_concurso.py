import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

st.title("Por concurso")
mostrar_aviso_responsabilidade()

conexao = obter_conexao()
numeros = [linha["numero"] for linha in conexao.execute("SELECT numero FROM concursos ORDER BY numero DESC")]

if not numeros:
    st.info("Nenhum concurso importado ainda -- veja a página 'Concurso atual'.")
else:
    numero = st.selectbox("Concurso", numeros)

    concurso = conexao.execute("SELECT * FROM concursos WHERE numero = ?", (numero,)).fetchone()
    st.caption(
        f"Apuração: {formatar_data_br(concurso['data_apuracao'])} · "
        f"Prazo de aposta (aproximado): {formatar_data_br(concurso['data_limite_aposta'])} · "
        f"Acumulou: {'sim' if concurso['acumulado'] else 'não'}"
    )

    jogos = conexao.execute(
        """
        SELECT j.num_jogo, j.gols_casa, j.gols_fora, j.resultado, j.campeonato, j.situacao, j.data_jogo,
               pc.nome AS casa, pf.nome AS fora
        FROM jogos j
        JOIN participantes pc ON pc.id = j.casa_id
        JOIN participantes pf ON pf.id = j.fora_id
        WHERE j.concurso_numero = ?
        ORDER BY j.num_jogo
        """,
        (numero,),
    ).fetchall()
    linhas = [
        {
            "Jogo": j["num_jogo"],
            "Mandante": j["casa"],
            "Placar": f"{j['gols_casa']} x {j['gols_fora']}" if j["gols_casa"] is not None else "-",
            "Visitante": j["fora"],
            "Coluna": j["resultado"] or "-",
            "Data": formatar_data_br(j["data_jogo"]),
            "Campeonato": j["campeonato"] or "-",
            "Situação": j["situacao"],
        }
        for j in jogos
    ]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    premiacoes = conexao.execute(
        "SELECT faixa, pontos, ganhadores, valor_premio FROM premiacoes WHERE concurso_numero = ? ORDER BY faixa",
        (numero,),
    ).fetchall()
    if premiacoes:
        st.subheader("Premiação")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Faixa": p["faixa"], "Pontos": p["pontos"], "Ganhadores": p["ganhadores"], "Prêmio (R$)": p["valor_premio"]}
                    for p in premiacoes
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

conexao.close()

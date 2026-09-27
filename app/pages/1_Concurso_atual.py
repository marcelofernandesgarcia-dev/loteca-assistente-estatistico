import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from util import mostrar_aviso_responsabilidade, obter_conexao

from importer.caixa_client import ErroImportacaoLoteca, importar_concurso
from stats.percentual import percentual_historico

st.title("Concurso atual")
mostrar_aviso_responsabilidade()

conexao = obter_conexao()

if st.button("Buscar/atualizar concurso vigente na CAIXA"):
    try:
        numero = importar_concurso(None, conexao)
        conexao.commit()
        st.success(f"Concurso {numero} atualizado.")
    except ErroImportacaoLoteca as erro:
        st.error(f"Não foi possível atualizar: {erro}")

concurso_atual = conexao.execute(
    "SELECT numero FROM concursos ORDER BY numero DESC LIMIT 1"
).fetchone()

if not concurso_atual:
    st.info("Nenhum concurso importado ainda -- clique no botão acima.")
else:
    numero = concurso_atual["numero"]
    st.subheader(f"Concurso {numero}")
    jogos = conexao.execute(
        """
        SELECT j.id, j.num_jogo, j.gols_casa, j.gols_fora, j.resultado, j.campeonato,
               pc.nome AS casa, pc.id AS casa_id, pf.nome AS fora, pf.id AS fora_id
        FROM jogos j
        JOIN participantes pc ON pc.id = j.casa_id
        JOIN participantes pf ON pf.id = j.fora_id
        WHERE j.concurso_numero = ?
        ORDER BY j.num_jogo
        """,
        (numero,),
    ).fetchall()

    linhas = []
    for jogo in jogos:
        pct = percentual_historico(conexao, jogo["casa_id"], jogo["fora_id"])
        placar = f"{jogo['gols_casa']} x {jogo['gols_fora']}" if jogo["gols_casa"] is not None else "-"
        linhas.append(
            {
                "Jogo": jogo["num_jogo"],
                "Mandante": jogo["casa"],
                "Placar": placar,
                "Visitante": jogo["fora"],
                "% Mandante (1)": round(pct["1"], 1),
                "% Empate (X)": round(pct["X"], 1),
                "% Visitante (2)": round(pct["2"], 1),
                "Resultado": jogo["resultado"] or "-",
            }
        )
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
    st.caption(
        "Percentual histórico (Poisson sobre o próprio banco importado) -- "
        "ver 'Fora do escopo da v1' no plano do app sobre por que não usa "
        "odds de mercado. Sem ajuste de notícias ainda para jogos futuros "
        "até a varredura semanal rodar."
    )

conexao.close()

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

from stats.forma import forma_recente
from stats.frequencia import frequencia_participante
from stats.temporada import desempenho_no_ano

st.title("Por time")
mostrar_aviso_responsabilidade()

conexao = obter_conexao()
participantes = conexao.execute(
    "SELECT id, nome, tipo FROM participantes ORDER BY nome"
).fetchall()

if not participantes:
    st.info("Nenhum participante importado ainda -- veja a página 'Concurso atual'.")
else:
    opcoes = {f"{p['nome']} ({p['tipo']})": p["id"] for p in participantes}
    escolha = st.selectbox("Participante (clube ou seleção)", list(opcoes.keys()))
    participante_id = opcoes[escolha]

    freq = frequencia_participante(conexao, participante_id)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Como mandante")
        t = freq["mandante"]["total"] or 1
        st.write(f"{freq['mandante']['total']} jogos")
        st.write(f"Vitória: {100*freq['mandante']['1']/t:.1f}% · Empate: {100*freq['mandante']['X']/t:.1f}% · Derrota: {100*freq['mandante']['2']/t:.1f}%")
    with col2:
        st.subheader("Como visitante")
        t = freq["visitante"]["total"] or 1
        st.write(f"{freq['visitante']['total']} jogos")
        st.write(f"Vitória: {100*freq['visitante']['2']/t:.1f}% · Empate: {100*freq['visitante']['X']/t:.1f}% · Derrota: {100*freq['visitante']['1']/t:.1f}%")

    st.subheader("Forma recente (últimos jogos, qualquer ano)")
    forma = forma_recente(conexao, participante_id)
    st.write(
        f"Últimos {forma['jogos_considerados']} jogos: {forma['vitorias']}V {forma['empates']}E {forma['derrotas']}D · "
        f"{forma['gols_marcados']} gols marcados, {forma['gols_sofridos']} sofridos, {forma['clean_sheets']} clean sheets."
    )

    st.subheader("Desempenho no ano em curso")
    st.caption("Só os jogos deste ano civil -- é a base usada no card 'Seu bilhete' da página Concurso atual para confrontar com sua marcação.")
    desempenho = desempenho_no_ano(conexao, participante_id)
    if desempenho["jogos"] == 0:
        st.write(f"Nenhum jogo importado em {desempenho['ano']} para este participante ainda.")
    else:
        st.write(
            f"{desempenho['ano']}: {desempenho['jogos']} jogos · {desempenho['vitorias']}V {desempenho['empates']}E {desempenho['derrotas']}D · "
            f"{desempenho['gols_marcados']} gols marcados, {desempenho['gols_sofridos']} sofridos."
        )

    st.subheader("Histórico de aparições na Loteca")
    jogos = conexao.execute(
        """
        SELECT j.concurso_numero, j.data_jogo, j.gols_casa, j.gols_fora, j.resultado,
               pc.nome AS casa, pf.nome AS fora
        FROM jogos j
        JOIN participantes pc ON pc.id = j.casa_id
        JOIN participantes pf ON pf.id = j.fora_id
        WHERE j.casa_id = ? OR j.fora_id = ?
        ORDER BY j.data_jogo DESC
        """,
        (participante_id, participante_id),
    ).fetchall()
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Concurso": j["concurso_numero"],
                    "Data": formatar_data_br(j["data_jogo"]),
                    "Mandante": j["casa"],
                    "Placar": f"{j['gols_casa']} x {j['gols_fora']}" if j["gols_casa"] is not None else "-",
                    "Visitante": j["fora"],
                    "Coluna": j["resultado"] or "-",
                }
                for j in jogos
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Fatores externos já coletados (varredura semanal)")
    fatores = conexao.execute(
        "SELECT concurso_numero, coletado_em, resumo, ajuste_aplicado FROM fatores_externos "
        "WHERE participante_id = ? ORDER BY coletado_em DESC",
        (participante_id,),
    ).fetchall()
    if fatores:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Concurso": f["concurso_numero"], "Coletado em": f["coletado_em"], "Resumo": f["resumo"], "Ajuste (p.p.)": f["ajuste_aplicado"]}
                    for f in fatores
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("Nenhuma varredura rodada para este participante ainda.")

conexao.close()

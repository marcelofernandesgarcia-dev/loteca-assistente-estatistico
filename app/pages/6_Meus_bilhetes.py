"""Bilhetes salvos, conferência e controle de gasto x prêmio (etapa A3).
Dado fica só neste computador; nenhum dado pessoal é gravado, só a marcação
e o valor que você mesmo informar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

from stats.bilhetes_salvos import (
    conferir_bilhete,
    listar_bilhetes,
    pode_conferir,
    registrar_premio,
    resumo_financeiro,
)

NOME_RESULTADO = {"V": "Vitória", "E": "Empate", "D": "Derrota"}

st.title("Meus bilhetes")
mostrar_aviso_responsabilidade()
st.caption(
    "Bilhetes que você salvou na página 'Concurso atual', com o percentual de cada jogo no momento em que "
    "salvou. Fica só neste computador (`loteca.db`) -- não é enviado a lugar nenhum, e não guarda seu nome "
    "nem qualquer outro dado pessoal, só a marcação e o gasto."
)

conexao = obter_conexao()
bilhetes = listar_bilhetes(conexao)

if not bilhetes:
    st.info("Nenhum bilhete salvo ainda -- vá em 'Concurso atual', marque o bilhete e clique em 'Salvar bilhete'.")
    conexao.close()
    st.stop()

resumo = resumo_financeiro(conexao)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Bilhetes salvos", resumo["bilhetes"])
c2.metric("Total gasto", f"R$ {resumo['gasto_total']:.2f}")
c3.metric("Total em prêmios (informado por você)", f"R$ {resumo['premio_total']:.2f}")
c4.metric("Saldo", f"R$ {resumo['saldo']:.2f}", delta=None)
st.caption(
    "O prêmio só entra aqui se você informar (abaixo, em cada bilhete apurado) -- o app não consulta a CAIXA "
    "para saber se você ganhou."
)

for bilhete in bilhetes:
    linhas_bilhete = conexao.execute(
        "SELECT j.resultado FROM bilhete_jogos bj JOIN jogos j ON j.id = bj.jogo_id WHERE bj.bilhete_id = ?",
        (bilhete["id"],),
    ).fetchall()
    total_jogos_bilhete = len(linhas_bilhete)
    jogos_apurados_antes = pode_conferir(linhas_bilhete)
    titulo = f"Concurso {bilhete['concurso_numero']} · salvo em {formatar_data_br(bilhete['criado_em'][:10])} · {bilhete['apostas']} apostas · R$ {bilhete['custo']:.2f}"
    if bilhete["conferido_em"] is not None:
        titulo += f" · {bilhete['acertos']}/{total_jogos_bilhete} acertos"
    with st.expander(titulo):
        if bilhete["conferido_em"] is None:
            if jogos_apurados_antes:
                if st.button("Conferir", key=f"conferir_{bilhete['id']}"):
                    conferir_bilhete(conexao, bilhete["id"])
                    conexao.commit()
                    st.rerun()
            else:
                st.caption("Ainda não dá para conferir -- nem todos os jogos deste concurso foram apurados.")
        else:
            resultado = conferir_bilhete(conexao, bilhete["id"])  # idempotente; recalcula para exibir o detalhe
            st.write(
                f"**{resultado['acertos']} de {resultado['total_jogos']} acertos.**"
                + (" 13 pontos ou mais!" if resultado["acertos"] >= 13 else "")
            )
            if resultado["acertos_sugestao_do_modelo"] is not None:
                st.caption(
                    f"A sugestão do modelo (sobre o mesmo percentual salvo neste bilhete) teria acertado "
                    f"{resultado['acertos_sugestao_do_modelo']} de {resultado['total_jogos']} -- não é o que você "
                    "marcou, é só uma referência de comparação."
                )
            linhas = [
                {
                    "Jogo": j["num_jogo"], "Confronto": f"{j['casa']} x {j['fora']}",
                    "Você marcou": ", ".join(j["marcacoes"]), "Resultado": j["resultado"],
                    "Acertou": "Sim" if j["acertou"] else "Não",
                }
                for j in resultado["jogos"]
            ]
            st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)

            premio = st.number_input(
                "Prêmio recebido (R$, 0 se não ganhou)", min_value=0.0, step=0.01,
                value=float(bilhete["premio_informado"] or 0.0), key=f"premio_{bilhete['id']}",
            )
            if st.button("Salvar prêmio", key=f"salvar_premio_{bilhete['id']}"):
                registrar_premio(conexao, bilhete["id"], premio)
                conexao.commit()
                st.rerun()

conexao.close()

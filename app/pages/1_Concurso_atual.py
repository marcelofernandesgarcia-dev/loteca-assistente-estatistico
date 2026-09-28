import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from estilo_caixa import renderizar_cartao
from util import mostrar_aviso_responsabilidade, obter_conexao

import config
from importer.caixa_client import ErroImportacaoLoteca, importar_concurso
from stats.percentual import percentual_historico
from stats.sugestao import sugerir_marcacao

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


def _jogos_do_concurso(numero: int):
    return conexao.execute(
        """
        SELECT j.id, j.num_jogo, j.gols_casa, j.gols_fora, j.resultado, j.data_jogo,
               pc.nome AS casa, pc.id AS casa_id, pf.nome AS fora, pf.id AS fora_id
        FROM jogos j
        JOIN participantes pc ON pc.id = j.casa_id
        JOIN participantes pf ON pf.id = j.fora_id
        WHERE j.concurso_numero = ?
        ORDER BY j.num_jogo
        """,
        (numero,),
    ).fetchall()


ultimo_encerrado = conexao.execute(
    "SELECT DISTINCT concurso_numero FROM jogos WHERE resultado IS NOT NULL ORDER BY concurso_numero DESC LIMIT 1"
).fetchone()
concurso_vigente = conexao.execute("SELECT numero FROM concursos ORDER BY numero DESC LIMIT 1").fetchone()

if not concurso_vigente:
    st.info("Nenhum concurso importado ainda -- clique no botão acima.")
else:
    # Card 1 -- resultado real do último concurso encerrado (estilo do portal da CAIXA)
    if ultimo_encerrado:
        jogos = _jogos_do_concurso(ultimo_encerrado["concurso_numero"])
        linhas = []
        for j in jogos:
            venceu_casa = j["resultado"] == "1"
            venceu_x = j["resultado"] == "X"
            venceu_fora = j["resultado"] == "2"
            linhas.append(
                {
                    "num_jogo": j["num_jogo"],
                    "casa": j["casa"],
                    "fora": j["fora"],
                    "data": j["data_jogo"] or "-",
                    "valor_casa": str(j["gols_casa"]) if j["gols_casa"] is not None else "-",
                    "valor_x": "" if not venceu_x else "X",
                    "valor_fora": str(j["gols_fora"]) if j["gols_fora"] is not None else "-",
                    "destaque_casa": venceu_casa,
                    "destaque_x": venceu_x,
                    "destaque_fora": venceu_fora,
                }
            )
        st.markdown(
            renderizar_cartao(f"Resultado do concurso {ultimo_encerrado['concurso_numero']} (encerrado)", linhas),
            unsafe_allow_html=True,
        )

    # Cards 2 e 3 -- percentual histórico e marcação sugerida do concurso vigente
    numero_vigente = concurso_vigente["numero"]
    jogos_vigente = _jogos_do_concurso(numero_vigente)

    linhas_pct, linhas_sugestao = [], []
    for j in jogos_vigente:
        pct = percentual_historico(conexao, j["casa_id"], j["fora_id"])
        maior = max(pct, key=pct.get)
        sugestao = sugerir_marcacao(pct)

        linhas_pct.append(
            {
                "num_jogo": j["num_jogo"],
                "casa": j["casa"],
                "fora": j["fora"],
                "data": j["data_jogo"] or "-",
                "valor_casa": f"{pct['1']:.0f}%",
                "valor_x": f"{pct['X']:.0f}%",
                "valor_fora": f"{pct['2']:.0f}%",
                "destaque_casa": maior == "1",
                "destaque_x": maior == "X",
                "destaque_fora": maior == "2",
            }
        )
        linhas_sugestao.append(
            {
                "num_jogo": j["num_jogo"],
                "casa": j["casa"],
                "fora": j["fora"],
                "data": j["data_jogo"] or "-",
                "valor_casa": f"{pct['1']:.0f}%",
                "valor_x": f"{pct['X']:.0f}%",
                "valor_fora": f"{pct['2']:.0f}%",
                "destaque_casa": "1" in sugestao["colunas"],
                "destaque_x": "X" in sugestao["colunas"],
                "destaque_fora": "2" in sugestao["colunas"],
            }
        )

    st.markdown(
        renderizar_cartao(f"Percentual histórico -- concurso {numero_vigente}", linhas_pct),
        unsafe_allow_html=True,
    )
    st.markdown(
        renderizar_cartao(f"Marcação sugerida -- concurso {numero_vigente}", linhas_sugestao),
        unsafe_allow_html=True,
    )
    st.caption(
        "Marcação sugerida: seco quando o favorito passa de "
        f"{config.SUGESTAO_LIMIAR_SECO:.0f}%, duplo entre "
        f"{config.SUGESTAO_LIMIAR_DUPLO:.0f}% e {config.SUGESTAO_LIMIAR_SECO:.0f}%, "
        "triplo abaixo disso -- limiares ajustáveis em config.py. Ainda sem ajuste de "
        "notícias para concursos futuros até a varredura semanal rodar."
    )

conexao.close()

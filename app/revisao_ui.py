"""Revisão pós-jogo de um bilhete conferido e diagnóstico do concurso (itens D2 e D4 do plano v2, 07/10/2026).
As contas estão em stats/revisao.py; aqui só a apresentação e a anotação do usuário."""
import datetime as dt
import html

import streamlit as st
from estilo_caixa import renderizar_tabela
from retrato_ui import NOME_ORIGEM

from stats.bilhete import montar_bilhete
from stats.revisao import diagnostico_do_concurso, frase_do_diagnostico, revisao_do_bilhete


def _pct(p: dict) -> str:
    return " / ".join(f"{p[c]:.0f}%" for c in ("1", "X", "2"))


def _virgula(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def gravar_nota(conexao, bilhete_id: int, texto: str) -> bool:
    texto = texto.strip()
    if not texto:
        return False
    conexao.execute("INSERT INTO notas_bilhete (bilhete_id, criado_em, texto) VALUES (?, ?, ?)",
                    (bilhete_id, dt.datetime.now().isoformat(timespec="seconds"), texto))
    return True


def notas_do_bilhete(conexao, bilhete_id: int) -> list[dict]:
    return [dict(l) for l in conexao.execute(
        "SELECT criado_em, texto FROM notas_bilhete WHERE bilhete_id = ? ORDER BY id", (bilhete_id,))]


def mostrar_revisao(conexao, bilhete: dict, jogos: list[dict], retrato: dict | None, concursos: list[dict],
                    referencia: dict | None) -> None:
    """`jogos`: de conferir_bilhete (num_jogo, casa, fora, marcacoes, resultado, percentual_*). `concursos`: de
    stats.anti_manada.carregar_concursos. `referencia`: frequência simples em %."""
    st.markdown("**Revisão pós-jogo**")
    diagnostico = diagnostico_do_concurso(concursos, bilhete["concurso_numero"])
    if diagnostico:
        st.caption(frase_do_diagnostico(diagnostico))
    if not all(j["percentual_1"] is not None for j in jogos):
        st.caption("Sem os percentuais do momento guardados: não dá para medir a surpresa de cada jogo.")
        return
    por_jogo = {j["num_jogo"]: j for j in (retrato or {}).get("jogos", [])}
    pcts = [{"1": j["percentual_1"], "X": j["percentual_x"], "2": j["percentual_2"]} for j in jogos]
    # Sem retrato, a sugestão é refeita sobre os MESMOS percentuais guardados (mesma conta da conferência).
    sugestao_refeita = montar_bilhete(pcts)["marcacoes"]
    entrada = [
        {"num_jogo": j["num_jogo"], "marcacoes": j["marcacoes"], "resultado": j["resultado"], "pct": pct,
         "sugestao": por_jogo.get(j["num_jogo"], {}).get("sugestao_do_app") or sugestao_refeita[i]}
        for i, (j, pct) in enumerate(zip(jogos, pcts))
    ]
    revisao = revisao_do_bilhete(entrada, referencia)
    linhas = []
    for j, e, r in zip(jogos, entrada, revisao["jogos"]):
        foto = por_jogo.get(j["num_jogo"], {})
        linhas.append([
            f"{j['num_jogo']}. {html.escape(j['casa'])} x {html.escape(j['fora'])}",
            ", ".join(j["marcacoes"]), ", ".join(e["sugestao"]) if e["sugestao"] else "-",
            _pct(e["pct"]), html.escape(NOME_ORIGEM.get(foto.get("origem"), "-")), j["resultado"],
            _virgula(r["surpresa"]), html.escape(r["texto"]),
        ])
    st.markdown(
        renderizar_tabela(
            "Jogo a jogo, com o que o app mostrava ao salvar",
            ["Jogo", "Você marcou", "Sugestão do app", "Percentual 1 / X / 2", "Origem", "Resultado",
             "Surpresa", "Leitura"],
            linhas,
        ),
        unsafe_allow_html=True,
    )
    texto = (f"Surpresa = −ln(chance que o app deu ao resultado): perto de 0, resultado esperado; acima de 1,4, "
             f"o app dava menos de 25%. Média do app neste concurso: {_virgula(revisao['perda_log_app'], 3)}")
    if revisao["perda_log_referencia"] is not None:
        melhor = "menor" if revisao["perda_log_app"] < revisao["perda_log_referencia"] else "maior"
        texto += (f"; da frequência simples de 1/X/2: {_virgula(revisao['perda_log_referencia'], 3)} (o app teve surpresa "
                  f"{melhor} que a referência neste concurso). Um concurso só não mede o modelo: a medida está em "
                  "'Confiabilidade do modelo'.")
    st.caption(texto)
    if not retrato:
        st.caption("Bilhete salvo antes de 07/10/2026: a sugestão foi refeita sobre os percentuais guardados; a origem "
                   "do momento não foi guardada (coluna com \"-\").")

    for nota in notas_do_bilhete(conexao, bilhete["id"]):
        st.markdown(f"- *{nota['criado_em'][:16].replace('T', ' ')}*: {html.escape(nota['texto'])}")
    chave = f"nota_{bilhete['id']}"
    st.text_area("Sua anotação sobre este concurso (o que mudou na semana, o que você aprendeu)", key=chave,
                 help="Fica só neste computador. Não escreva dados pessoais. A anotação não muda o retrato.")
    if st.button("Guardar anotação", key=f"guardar_{chave}"):
        if gravar_nota(conexao, bilhete["id"], st.session_state.get(chave, "")):
            conexao.commit()
            st.success("Anotação guardada.")
            st.rerun()
        else:
            st.warning("Escreva algo antes de guardar.")

"""Quadro de bilhetes do concurso (pedido do usuário, 08/10/2026): todos os bilhetes salvos lado a lado, com a
análise guardada no momento de salvar, nas mesmas colunas da tabela de versões. Só apresentação: as contas estão em
stats/bilhetes_salvos.quadro_do_concurso. As funções de texto são puras para poderem ser testadas sem o Streamlit."""
import streamlit as st
from estilo_caixa import renderizar_tabela

from stats.analise_palpite import formatar_uma_em
from stats.bilhetes_salvos import APOSTADO, NOME_SITUACAO, RASCUNHO, SIMULADO, confirmar_situacao
from stats.premiacao import reais
from stats.variantes_bilhete import nome_da_origem

CABECALHOS = ["Bilhete", "Origem", "Salvo em", "Apostas (custo)", "Chance de {n} (pelos percentuais)",
              "Chance de {m} ou mais (pelos percentuais)", "Acertos esperados", "Duplos / triplos", "Zebras", "Situação"]


def _salvo_em(criado_em: str) -> str:
    """'2026-10-08T14:34:34' -> '08/10 14:34'."""
    return f"{criado_em[8:10]}/{criado_em[5:7]} {criado_em[11:16]}"


def cabecalhos(linhas: list[dict]) -> list[str]:
    n = max((l["total_jogos"] for l in linhas), default=14)
    nomes = [c.format(n=n, m=n - 1) for c in CABECALHOS]
    return nomes + (["Acertos"] if any(l["acertos"] is not None for l in linhas) else [])


def linhas_do_quadro(linhas: list[dict]) -> list[list[str]]:
    com_acertos = any(l["acertos"] is not None for l in linhas)
    saida = []
    for l in linhas:
        linha = [
            f"nº {l['id']}", nome_da_origem(l["origem"]), _salvo_em(l["criado_em"]),
            f"{l['apostas']} ({reais(l['custo'])})",
            formatar_uma_em(l["chance_todos"]) if l["chance_todos"] is not None else "-",
            formatar_uma_em(l["chance_todos_menos_um"]) if l["chance_todos_menos_um"] is not None else "-",
            f"{l['acertos_esperados']:.1f}".replace(".", ",") if l["acertos_esperados"] is not None else "-",
            f"{l['duplos']} / {l['triplos']}",
            "-" if l["zebras"] is None else str(l["zebras"]),
            NOME_SITUACAO[l["situacao"]],
        ]
        if com_acertos:
            linha.append("-" if l["acertos"] is None else f"{l['acertos']} de {l['total_jogos']}")
        saida.append(linha)
    return saida


def _data_hora(texto: str | None) -> str:
    """'2026-10-10T09:15:02' -> '10/10/2026 09:15'."""
    return f"{texto[8:10]}/{texto[5:7]}/{texto[:4]} {texto[11:16]}" if texto else ""


def mostrar_pergunta_aposta(conexao, bilhete: dict, chave: str, prazo_passou: bool = False) -> None:
    """Botão "Foi apostado?" com confirmação (pedido do usuário, 10/10/2026). Só bilhete apostado entra nas contas;
    a resposta pode ser desfeita. A gravação roda no fluxo da página (não em callback): o callback rodaria com a
    conexão da execução anterior, já fechada."""
    aberta = f"pergunta_aposta_{chave}"
    if bilhete["situacao"] != RASCUNHO:
        quando = _data_hora(bilhete["jogado_em"] if bilhete["situacao"] == APOSTADO else bilhete["simulado_em"])
        st.caption(f"Situação: **{NOME_SITUACAO[bilhete['situacao']]}**, respondido em {quando}. "
                   + ("Entra no gasto e no aprendizado." if bilhete["situacao"] == APOSTADO
                      else "Não entra no gasto nem no aprendizado; pode ser limpo em 'Meus bilhetes'."))
        if st.button("Voltar para rascunho", key=f"{aberta}_desfazer", help="Desfaz a resposta."):
            confirmar_situacao(conexao, bilhete["id"], RASCUNHO)
            conexao.commit()
            st.rerun()
        return
    if prazo_passou:
        st.warning("O prazo deste concurso já passou: responda se este bilhete foi apostado. Enquanto não responder, "
                   "ele não entra no gasto nem no aprendizado.")
    if not st.session_state.get(aberta):
        st.button("Foi apostado?", key=f"{aberta}_abrir", on_click=lambda: st.session_state.update({aberta: True}),
                  help="Confirme se este bilhete foi jogado na lotérica ou se foi só simulação.")
        return
    st.info(f"Bilhete nº {bilhete['id']}: {bilhete['apostas']} apostas, {reais(bilhete['custo'])}. "
            "Você apostou este bilhete na lotérica?")
    with st.container(horizontal=True):
        sim = st.button("Sim, apostei", key=f"{aberta}_sim", type="primary")
        nao = st.button("Não, foi simulação", key=f"{aberta}_nao")
        st.button("Cancelar", key=f"{aberta}_cancelar", on_click=lambda: st.session_state.pop(aberta, None))
    if sim or nao:
        confirmar_situacao(conexao, bilhete["id"], APOSTADO if sim else SIMULADO)
        conexao.commit()
        st.session_state.pop(aberta, None)
        st.rerun()


def mostrar_quadro(linhas: list[dict], titulo: str) -> None:
    if not linhas:
        return
    st.markdown(renderizar_tabela(titulo, cabecalhos(linhas), linhas_do_quadro(linhas)), unsafe_allow_html=True)
    st.caption(
        f"Se apostar todos, o gasto soma {reais(sum(l['custo'] for l in linhas))}. As chances e os acertos esperados são "
        "os do momento em que cada bilhete foi salvo, pelos percentuais do app, e costumam ser otimistas: use o quadro "
        "para comparar os bilhetes entre si, não como expectativa. A chance do conjunto, com os percentuais de hoje, "
        "está em 'Meus bilhetes'."
    )

"""Estudos estatísticos (pedido do usuário, 01/10/2026): o que os dados dizem sobre os fatores do
desempenho, sobre os modelos de 1/X/2 e sobre a estratégia anti-manada. Só apresentação: as contas
estão em stats/associacao.py, stats/backtest_competicao.py e stats/anti_manada.py, e os relatórios
completos, em docs/. Nada aqui altera os percentuais do app."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import estudos_ui as ui
import streamlit as st
from estilo_caixa import renderizar_tabela
from util import mostrar_aviso_responsabilidade, obter_conexao

from stats import anti_manada, associacao
from stats import backtest_competicao as b2
from stats.premiacao import reais

logger = logging.getLogger("estudos_estatisticos")


def _versao(consulta: str) -> tuple:
    """Impressão digital dos dados de que o estudo depende: muda quando entram dados novos e renova o cache."""
    conexao = obter_conexao()
    try:
        return tuple(conexao.execute(consulta).fetchone())
    finally:
        conexao.close()


@st.cache_data(show_spinner=False)
def _calcular_fatores(versao: tuple):
    conexao = obter_conexao()
    try:
        observacoes = associacao.carregar_observacoes(conexao)
    finally:
        conexao.close()
    return associacao.estudar(observacoes), len(observacoes)


@st.cache_data(show_spinner=False)
def _calcular_modelos(versao: tuple):
    conexao = obter_conexao()
    try:
        amostra = b2.carregar_amostra(conexao)
    finally:
        conexao.close()
    previstos = b2.prever(amostra)
    if not previstos:
        return None
    return b2.resumir(previstos), sorted({o["ano"] for o in previstos})


@st.cache_data(show_spinner=False)
def _calcular_anti_manada(versao: tuple):
    conexao = obter_conexao()
    try:
        concursos, fora = anti_manada.carregar_concursos(conexao)
    finally:
        conexao.close()
    if not concursos:
        return None
    anos = sorted({c["ano"] for c in concursos})
    return anti_manada.estudar(concursos), anti_manada.tabela_por_faixa(concursos), len(concursos), (anos[0], anos[-1])


def _calcular(rotulo: str, funcao, versao: tuple):
    """Roda o cálculo com aviso de espera; em caso de falha, registra o erro e mostra mensagem útil com nova tentativa."""
    try:
        with st.spinner(f"Calculando {rotulo}..."):
            return funcao(versao), True
    except Exception:
        logger.exception("Falha ao calcular %s", rotulo)
        st.error(
            f"Não foi possível calcular {rotulo} agora. Nenhum dado do app foi alterado. "
            "Tente de novo; se o problema continuar, o registro técnico ficou no log do servidor."
        )
        if st.button("Tentar de novo", key=f"retentar_{rotulo}"):
            st.cache_data.clear()
            st.rerun()
        return None, False


def _tabela(titulo: str, cabecalhos: list[str], linhas: list[list[str]]) -> None:
    st.markdown(renderizar_tabela(titulo, cabecalhos, linhas), unsafe_allow_html=True)


st.title("Estudos estatísticos")
mostrar_aviso_responsabilidade()
st.caption(
    "O que os dados dizem, medido sem olhar o futuro e com o tamanho da incerteza. Nenhum estudo desta página altera os "
    "percentuais do aplicativo nem prevê resultado. Os relatórios completos estão na pasta docs/ do projeto."
)

aba_fatores, aba_modelos, aba_manada = st.tabs(["Fatores do desempenho", "Modelos de 1/X/2", "Anti-manada"])

with aba_fatores:
    st.header("O que vem junto de um bom resultado?")
    st.caption(
        "Para cada fator, mede-se se ele melhora a previsão do resultado do jogo (Séries A e B da CBF, 2019 em diante), além do "
        "que o retrospecto do time, o do adversário e o mando já informam. A previsão é testada em temporadas deixadas de fora."
    )
    versao = _versao("SELECT COUNT(*), MAX(coletado_em) FROM cbf_partidas")
    if not versao[0]:
        st.info("Nenhuma partida da CBF foi coletada ainda. Veja a coleta no README (scripts/coleta_cbf.py).")
    else:
        saida, ok = _calcular("os fatores do desempenho", _calcular_fatores, versao)
        if ok and saida:
            resultados, n_jogos = saida
            st.markdown(f"**Conclusão.** {ui.frase_fatores(resultados)}")
            figura = ui.figura_coeficientes(resultados)
            if figura is not None:
                st.markdown(f"**{ui.TITULO_FIGURA_FATORES}**")
                st.plotly_chart(figura, width="stretch", key="grafico_fatores")
                st.caption(
                    "Descrição do gráfico: cada losango é o efeito estimado do fator em pontos por jogo; a barra é o intervalo de 95%. "
                    "Barra que cruza a linha tracejada em zero indica efeito que a amostra não distingue de nenhum. Os mesmos números estão na tabela abaixo."
                )
            _tabela(f"Fatores testados ({ui.inteiro(n_jogos)} jogos de time)", ui.CABECALHOS_FATORES, ui.linhas_fatores(resultados))
            with st.expander("Como foi feito e o que não dá para concluir"):
                st.markdown(
                    "- **Ganho de previsão:** quanto o erro do modelo diminui ao incluir o fator. Valor negativo ou perto de zero significa que ele não ajuda.\n"
                    "- **q:** valor que já corrige o fato de oito a dez fatores serem testados ao mesmo tempo; só abaixo de 0,05 o fator é dado como útil.\n"
                    "- **Associação não é causa.** \"Melhora a previsão\" não autoriza mudar o percentual do modelo.\n"
                    "- **SAF:** poucos clubes, adoção não aleatória e marca vinda do nome do clube na CBF, que não prova a ausência de SAF.\n"
                    "- **Cartões** ficaram fora: o banco guarda só o total da temporada, não o cartão de cada rodada.\n"
                    "- Uma primeira versão do método apontava quase todos os fatores como relevantes e foi descartada: era efeito do próprio cálculo. "
                    "Detalhes em docs/p3-associacao-fatores-01-10-2026.md."
                )

with aba_modelos:
    st.header("Os jogos da temporada ajudam a prever 1, X ou 2?")
    st.caption(
        "Compara três modelos nos jogos da CBF, sempre treinando em anos anteriores ao testado: a frequência simples de 1/X/2, "
        "o retrospecto dos dois times e o Poisson da temporada. Só mede; o percentual exibido no app não muda."
    )
    versao = _versao("SELECT COUNT(*), MAX(coletado_em) FROM cbf_partidas")
    if not versao[0]:
        st.info("Nenhuma partida da CBF foi coletada ainda. Veja a coleta no README (scripts/coleta_cbf.py).")
    else:
        if not st.session_state.get("pedido_teste_modelos"):
            st.info("Este teste refaz os modelos a cada rodada e leva cerca de 10 segundos.")
            if st.button("Rodar o teste dos modelos", key="rodar_teste_modelos"):
                st.session_state["pedido_teste_modelos"] = True
                st.rerun()
        else:
            saida, ok = _calcular("o teste dos modelos", _calcular_modelos, versao)
            if ok and saida is None:
                st.info("Ainda não há jogos suficientes para o teste (cada time precisa de 5 jogos já conhecidos e de pelo menos um ano anterior para treino).")
            elif ok:
                resumo, anos = saida
                st.markdown(f"**Conclusão.** {ui.frase_b2(resumo)}")
                st.markdown(f"**{ui.TITULO_FIGURA_B2}**")
                st.plotly_chart(ui.figura_comparacoes_b2(resumo), width="stretch", key="grafico_modelos")
                st.caption(
                    "Descrição do gráfico: cada losango é o ganho médio em perda logarítmica de um modelo sobre outro; a barra é o intervalo de 95%. "
                    "À direita da linha em zero, o primeiro modelo é melhor. Os mesmos números estão nas tabelas abaixo."
                )
                _tabela(f"Desempenho de cada modelo ({ui.inteiro(resumo['n'])} jogos, de {anos[0]} a {anos[-1]})", ui.CABECALHOS_B2, ui.linhas_b2(resumo))
                _tabela("Comparações pareadas", ui.CABECALHOS_B2_COMPARACAO, ui.linhas_b2_comparacoes(resumo))
                with st.expander("Como foi feito e o que não dá para concluir"):
                    st.markdown(
                        "- **Perda logarítmica e Brier:** medem a qualidade das probabilidades; menor é melhor. O acerto do favorito não é o critério.\n"
                        "- **Sem olhar o futuro:** só entram jogos já disputados antes da rodada; jogo adiado só conta depois de acontecer.\n"
                        "- **Vale para as Séries A e B.** O percentual da Loteca também envolve seleções e times de outras divisões, que este teste não cobre.\n"
                        "- Trocar o modelo do app seria uma decisão separada. Detalhes em docs/b2-modelo-por-competicao-01-10-2026.md."
                    )

with aba_manada:
    st.header("Resultados fora do esperado dividem menos o prêmio?")
    st.caption(
        "Compara, concurso a concurso, quantos jogos terminaram fora da coluna 1 (empate ou vitória do visitante) com quantos apostadores "
        "fizeram os 14 pontos, por milhão arrecadado e dentro do mesmo ano."
    )
    versao = _versao("SELECT COUNT(*), MAX(concurso_numero) FROM premiacoes")
    if not versao[0]:
        st.info("Nenhuma premiação importada ainda. Veja a página \"Concurso atual\" e o README (scripts/importar_valores.py).")
    else:
        saida, ok = _calcular("o estudo anti-manada", _calcular_anti_manada, versao)
        if ok and saida is None:
            st.info("Ainda não há concursos com arrecadação e ganhadores de 14 informados para a análise.")
        elif ok:
            resultados, faixas, n_concursos, anos = saida
            st.markdown(f"**Conclusão.** {ui.frase_q7(resultados, n_concursos, anos)}")
            if faixas:
                st.markdown(f"**{ui.TITULO_FIGURA_Q7}**")
                st.plotly_chart(ui.figura_faixas_q7(faixas), width="stretch", key="grafico_faixas_manada")
                st.caption(
                    "Descrição do gráfico: para cada faixa de jogos fora da coluna 1, a barra mostra a porcentagem de concursos em que ninguém acertou os 14 jogos. "
                    "Os mesmos números estão na tabela abaixo."
                )
            _tabela("Correlação entre jogos fora da coluna 1 e ganhadores de 14", ui.CABECALHOS_Q7, ui.linhas_q7(resultados))
            _tabela("Por faixa de jogos fora da coluna 1", ui.CABECALHOS_Q7_FAIXAS, ui.linhas_q7_faixas(faixas, reais))
            with st.expander("Como foi feito e o que não dá para concluir"):
                st.markdown(
                    "- **Correlação de postos estratificada por ano:** compara concursos do mesmo ano, para que mudanças de época não pareçam efeito.\n"
                    "- **Por milhão arrecadado:** desconta o tamanho do concurso, já que mais apostas geram mais ganhadores.\n"
                    "- Ficam de fora concursos sem arrecadação informada (antes de 2009), com jogo decidido por sorteio ou no formato antigo de 13 jogos.\n"
                    "- Mais jogos fora da coluna 1 também aumentam a chance de ninguém acertar os 14, o que acumula o prêmio. Isso não é o mesmo que prêmio maior para quem acerta.\n"
                    "- É um retrato do passado. **Não recomenda marcar resultados improváveis**: a chance de acertar 14 jogos continua muito pequena em qualquer estratégia.\n"
                    "- A conta anterior do projeto (-0,13) usava a correlação de Pearson sobre contagens brutas, que subestimava a relação. "
                    "Detalhes em docs/q7-anti-manada-01-10-2026.md."
                )

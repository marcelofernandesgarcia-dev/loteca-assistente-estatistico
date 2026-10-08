"""Tabelas da Loteca (pedido do usuário, 08/10/2026): valores e combinações de apostas, chances de cada combinação de
duplos e triplos em três leituras e a análise de uma combinação escolhida. Só apresentação: as contas estão em
stats/tabela_loteca.py."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from chances_ui import mostrar_chances_do_bilhete, percentuais_atuais_do_concurso
from estilo_caixa import renderizar_tabela
from util import mostrar_aviso_responsabilidade, obter_conexao

import config
import db
from stats.analise_palpite import formatar_uma_em
from stats.calibracao_bilhete import concursos_para_calibracao, frase_da_calibracao, frequencia_por_custo, versao_dos_dados
from stats.concursos import concurso_a_jogar
from stats.premiacao import reais
from stats.tabela_loteca import (
    chances_metodo_caixa,
    chances_pelos_percentuais,
    combinacoes_validas,
    motivo_invalida,
    tabela_de_chances,
    tabela_de_valores,
    uma_em,
)

log = logging.getLogger("loteca.tabelas")


@st.cache_data(show_spinner="Contando o que aconteceu nos concursos passados...")
def _historico(versao: tuple) -> dict:
    """{(duplos, triplos): frequencia_por_custo} de cada combinação válida; refeito só com concurso apurado novo."""
    conexao = db.conectar()
    try:
        concursos = concursos_para_calibracao(conexao)
    finally:
        conexao.close()
    return {(d, t): frequencia_por_custo(concursos, d, t) for d, t in combinacoes_validas()}


def _de_fato(freq: dict | None, chave: str) -> str:
    if not freq or freq["concursos"] < config.CALIBRACAO_MIN_CONCURSOS:
        return "-"
    return f"{freq[chave]} em {freq['concursos']:,}".replace(",", ".")


st.title("Tabelas da Loteca")
mostrar_aviso_responsabilidade()
st.caption(
    f"Preço vigente: {reais(config.PRECO_APOSTA_LOTECA)} por aposta ({config.PRECO_APOSTA_FONTE}, conferido no "
    "comprovante do concurso 1273). O formato das tabelas segue o CAIXA Informa de 2019, cujos preços não valem mais."
)

conexao = obter_conexao()
a_jogar = concurso_a_jogar(conexao)
jogos_atuais, pcts_atuais = percentuais_atuais_do_concurso(conexao, a_jogar["numero"]) if a_jogar else ([], [])
if len(pcts_atuais) != config.JOGOS_POR_CONCURSO:
    jogos_atuais, pcts_atuais = [], []
try:
    historico = _historico(versao_dos_dados(conexao))
except Exception as erro:  # a página segue com as outras leituras
    log.error("histórico das combinações indisponível: %s", type(erro).__name__)
    historico = None

# 1. Valores e combinações (formato do CAIXA Informa)
st.subheader("Valores e combinações de apostas")
st.caption("Cada duplo dobra e cada triplo triplica o número de apostas. Mínimo: 1 duplo (2 apostas). Máximo oficial: "
           f"{config.BILHETE_MAX_APOSTAS} apostas (5 duplos e 3 triplos).")
valores = tabela_de_valores()
for grupo, titulo in (("ate_1_triplo", "Sem triplo ou com 1 triplo"), ("2_ou_mais_triplos", "Com 2 triplos ou mais")):
    st.markdown(renderizar_tabela(titulo, ["Duplos", "Triplos", "Apostas", "Valor da aposta"], [
        [str(l["duplos"]), str(l["triplos"]), f"{l['apostas']:,}".replace(",", "."), reais(l["valor"])]
        for l in valores if l["grupo"] == grupo
    ]), unsafe_allow_html=True)

# 2. Chances por combinação, nas três leituras
st.subheader("Chances por combinação")
st.caption(
    "**Método da CAIXA:** cada resultado com 1 em 3, como nas tabelas oficiais (reproduz as chances da aposta mínima do "
    "Manual v21: 14 pontos, 1 em 2.391.485; 13 pontos, 1 em 85.410). A coluna \"13 (tabela da CAIXA)\" soma a chance de "
    "cada aposta do bilhete; \"bilhete premiar\" conta cada resultado uma vez. "
    + (f"**Pelos percentuais:** os duplos e triplos nos jogos mais incertos do concurso {a_jogar['numero']}, pelos "
       "percentuais do app (otimistas). " if pcts_atuais else "")
    + "**De fato:** a mesma regra nos concursos passados."
)
linhas_chances = tabela_de_chances(pcts_atuais or None, historico)
cabecalhos = ["Duplos / triplos", "Apostas (valor)", "14 (CAIXA)", "13 (tabela da CAIXA)", "Bilhete premiar (CAIXA)"]
if pcts_atuais:
    cabecalhos += [f"14 (percentuais do {a_jogar['numero']})", f"13 ou mais (percentuais do {a_jogar['numero']})"]
cabecalhos += ["13 ou mais de fato", "14 de fato"]
corpo = []
for l in linhas_chances:
    c = l["caixa"]
    apostas_texto = f"{l['apostas']:,}".replace(",", ".")
    linha = [f"{l['duplos']} / {l['triplos']}", f"{apostas_texto} ({reais(l['valor'])})",
             uma_em(c["total_resultados"], c["casos_14"]), uma_em(c["total_resultados"], c["casos_13_caixa"]),
             uma_em(c["total_resultados"], c["casos_premiar"])]
    if pcts_atuais:
        linha += [formatar_uma_em(l["percentuais"]["chance_14"]), formatar_uma_em(l["percentuais"]["chance_13_ou_mais"])]
    linha += [_de_fato(l["historico"], "fez_13_ou_mais"), _de_fato(l["historico"], "fez_14")]
    corpo.append(linha)
st.markdown(renderizar_tabela("Chance de acerto por combinação de duplos e triplos", cabecalhos, corpo),
            unsafe_allow_html=True)
if historico is None:
    st.caption("O que aconteceu de fato não pôde ser calculado agora; as outras colunas não dependem dele.")
st.caption("Nenhuma combinação garante acerto. Jogar mais duplos e triplos aumenta a chance e o custo na mesma proporção "
           "no método da CAIXA; o app não estima prêmio em reais.")

# 3. Analisar uma combinação
st.subheader("Analisar uma combinação")
col_d, col_t = st.columns(2)
duplos = int(col_d.number_input("Duplos", min_value=0, max_value=config.JOGOS_POR_CONCURSO, value=1, step=1, key="tabela_duplos"))
triplos = int(col_t.number_input("Triplos", min_value=0, max_value=config.JOGOS_POR_CONCURSO, value=0, step=1, key="tabela_triplos"))
motivo = motivo_invalida(duplos, triplos)
if motivo:
    st.warning(f"Essa combinação não pode ser jogada: {motivo}.")
else:
    c = chances_metodo_caixa(duplos, triplos)
    apostas_texto = f"{c['apostas']:,}".replace(",", ".")
    st.markdown(f"**{duplos} duplo(s) e {triplos} triplo(s): {apostas_texto} apostas, "
                f"{reais(c['apostas'] * config.PRECO_APOSTA_LOTECA)}.**")
    with st.container(horizontal=True, wrap=True):
        st.metric("14 pontos (método da CAIXA)", uma_em(c["total_resultados"], c["casos_14"]), border=True)
        st.metric("13 pontos (tabela da CAIXA)", uma_em(c["total_resultados"], c["casos_13_caixa"]), border=True)
        st.metric("Bilhete premiar (CAIXA)", uma_em(c["total_resultados"], c["casos_premiar"]), border=True)
    freq = historico.get((duplos, triplos)) if historico else None
    st.caption(frase_da_calibracao(freq))
    if pcts_atuais:
        st.markdown(f"**Pelos percentuais do concurso {a_jogar['numero']}**, com os duplos e triplos nos jogos mais incertos:")
        marcacoes = chances_pelos_percentuais(pcts_atuais, duplos, triplos)["marcacoes"]
        onde = [f"jogo {j['num_jogo']} ({''.join(m)})" for j, m in zip(jogos_atuais, marcacoes) if len(m) > 1]
        st.caption("Onde a regra do app poria os múltiplos: " + "; ".join(onde) + ".")
        mostrar_chances_do_bilhete(jogos_atuais, pcts_atuais, marcacoes)
    else:
        st.caption("Sem concurso aberto com os 14 jogos: a leitura pelos percentuais aparece quando houver um.")

conexao.close()

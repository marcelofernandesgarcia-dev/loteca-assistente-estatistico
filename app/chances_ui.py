"""Tela das chances de um bilhete e de um conjunto de bilhetes (pedido do usuário, 01/10/2026). Só apresentação:
as contas estão em stats/chances_bilhete.py. As funções de texto são puras para poderem ser testadas sem o Streamlit."""
import html

import streamlit as st
from estilo_caixa import renderizar_tabela

import config
from externo.percentual_final import ajustes_do_concurso, percentuais_do_jogo
from stats import chances_bilhete as cb
from stats.analise_palpite import formatar_uma_em


def pct(probabilidade: float) -> str:
    """Probabilidade em fração -> porcentagem com casas conforme o tamanho (chances pequenas precisam de mais casas)."""
    if probabilidade <= 0:
        return "0%"
    if probabilidade < 1e-4:
        return "menos de 0,01%"
    casas = 2 if probabilidade < 0.01 else 1
    return f"{100 * probabilidade:.{casas}f}%".replace(".", ",")


def reais(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def nota_da_calibracao() -> str:
    if config.CALIBRACAO_ATIVA:
        return (
            "Calculado com os percentuais já corrigidos pela calibração. Nos concursos passados, com a correção, o número de bilhetes "
            "premiados ficou próximo do previsto; sem ela, a conta era cerca de 7 vezes otimista. Mesmo assim, é uma estimativa: "
            "a chance de acertar 14 jogos continua muito pequena."
        )
    return (
        "A calibração está desligada: estes números usam os percentuais do modelo sem correção e tendem a ser otimistas "
        "(nos concursos passados, bilhetes de mesmo custo fizeram 13 ou mais bem menos vezes do que a conta previa)."
    )


def linhas_distribuicao(medidas: dict) -> list[list[str]]:
    n = medidas["jogos"]
    dist = medidas["distribuicao"]
    linhas = []
    for k in range(n, max(n - 4, -1), -1):  # os quatro números de acertos mais altos
        linhas.append([f"{k} acertos", pct(dist[k]), formatar_uma_em(dist[k])])
    if n >= 4:  # com poucos jogos não sobra faixa abaixo
        resto = sum(dist[k] for k in range(0, n - 3))
        linhas.append([f"{n - 4} acertos ou menos", pct(resto), formatar_uma_em(resto)])
    return linhas


CABECALHOS_DISTRIBUICAO = ["Número de acertos", "Chance", "Em outras palavras"]


def frase_das_apostas_premiadas(medidas: dict) -> str:
    n = medidas["jogos"]
    ap = medidas["apostas_premiadas"]
    se_todos, se_um = ap["se_acertar_todos"], ap["se_errar_exatamente_um"]
    if medidas["apostas"] == 1:
        return f"Com marcação simples em todos os jogos, o bilhete é uma única aposta: só premia se acertar {n - 1} ou {n}."
    texto = f"Se o resultado cair dentro das suas marcações nos {n} jogos, uma aposta do bilhete faz {n}"
    if se_todos["com_13"]:
        texto += f" e {inteiro(se_todos['com_13'])} aposta(s) fazem {n - 1}"
    texto += "."
    if se_um["minimo"] == se_um["maximo"]:
        texto += f" Se errar exatamente um jogo, {inteiro(se_um['minimo'])} aposta(s) fazem {n - 1}."
    else:
        texto += (
            f" Se errar exatamente um jogo, entre {inteiro(se_um['minimo'])} e {inteiro(se_um['maximo'])} apostas fazem {n - 1}, "
            "conforme o jogo errado (quanto mais colunas marcadas nele, mais apostas premiam)."
        )
    return texto


def linhas_ganho_dos_multiplos(ganhos: list[dict], jogos: list[dict]) -> list[list[str]]:
    linhas = []
    for g in ganhos:
        j = jogos[g["indice"]]
        tipo = "triplo" if g["de"] == 3 else "duplo"
        por_dez = g["ganho_13_por_real"] * 10 if g["ganho_13_por_real"] is not None else None
        linhas.append([
            f"{j['num_jogo']}. {html.escape(j['casa'])} x {html.escape(j['fora'])}",
            f"{tipo}; compara sem a coluna {g['coluna_acrescentada']}",
            f"{pct(g['chance_13_sem'])} → {pct(g['chance_13_com'])}",
            reais(g["custo_extra"]),
            "—" if por_dez is None else f"{100 * por_dez:.2f}".replace(".", ",") + " ponto percentual",
        ])
    return linhas


CABECALHOS_GANHO = ["Jogo", "Marcação", "Chance de 13 ou mais (sem → com a coluna)", "Custo da coluna", "Acréscimo a cada R$ 10,00"]


def mostrar_chances_do_bilhete(jogos: list[dict], pcts: list[dict], marcacoes: list[list[str]]) -> dict | None:
    """Chances do bilhete com as marcações atuais. `jogos`: dicts com num_jogo, casa e fora, na ordem de `pcts`.
    Devolve as medidas (ou None se a marcação for inválida)."""
    try:
        medidas = cb.medidas_do_bilhete(pcts, marcacoes)
    except ValueError as erro:
        st.info(f"Não foi possível calcular as chances deste bilhete: {erro}")
        return None
    n = medidas["jogos"]
    st.markdown("#### Chances deste bilhete")
    with st.container(horizontal=True, wrap=True):
        st.metric(f"{n} acertos", formatar_uma_em(medidas["chance_14"]), help=f"Chance de {n} acertos: {pct(medidas['chance_14'])}.", border=True)
        st.metric(f"{n - 1} acertos ou mais", formatar_uma_em(medidas["chance_13_ou_mais"]),
                  help=f"Chance de {n - 1} ou mais: {pct(medidas['chance_13_ou_mais'])}. Só premiam {n - 1} e {n}.", border=True)
        if n >= 4:
            st.metric(f"{n - 2} acertos ou mais", formatar_uma_em(medidas["chance_12_ou_mais"]),
                      help=f"Chance de {n - 2} ou mais: {pct(medidas['chance_12_ou_mais'])}. Não premia, mostra o quase.", border=True)
        st.metric("Acertos esperados", f"{medidas['acertos_esperados']:.1f}".replace(".", ","), border=True)
    st.caption(
        f"{inteiro(medidas['apostas'])} aposta(s), {reais(medidas['custo'])}. " + nota_da_calibracao()
    )
    with st.expander("Distribuição de acertos, apostas que premiam e o que cada duplo e triplo acrescenta"):
        st.markdown(renderizar_tabela("Chance de cada número de acertos", CABECALHOS_DISTRIBUICAO, linhas_distribuicao(medidas)), unsafe_allow_html=True)
        st.markdown(frase_das_apostas_premiadas(medidas))
        ganhos = cb.ganho_de_cada_multiplo(pcts, marcacoes)
        if ganhos:
            st.markdown(
                renderizar_tabela("O que cada duplo e triplo acrescenta", CABECALHOS_GANHO, linhas_ganho_dos_multiplos(ganhos, jogos)),
                unsafe_allow_html=True,
            )
            st.caption(
                "Cada linha compara o bilhete com ele mesmo sem a coluna de menor percentual daquele jogo. Mostra quanto a coluna "
                "acrescenta na chance de 13 ou mais e quanto custa. É uma comparação: não diz o que marcar."
            )
        else:
            st.caption("O bilhete só tem marcação simples; não há duplo ou triplo para comparar.")
    return medidas


# ---------------------------------------------------------------- conjunto de bilhetes

def rotulo_do_bilhete(bilhete: dict) -> str:
    return f"Bilhete {bilhete['id']} ({inteiro(bilhete['apostas'])} apostas, {reais(bilhete['custo'])})"


def linhas_por_bilhete(medidas: dict, rotulos: dict) -> list[list[str]]:
    return [
        [
            html.escape(rotulos[b["id"]]), formatar_uma_em(b["chance_14"]), formatar_uma_em(b["chance_13_ou_mais"]),
            f"{pct(b['acrescenta_13'])} ({formatar_uma_em(b['acrescenta_13'])})" if b["acrescenta_13"] > 0 else "nada",
        ]
        for b in medidas["por_bilhete"]
    ]


CABECALHOS_POR_BILHETE = ["Bilhete", "Chance de 14", "Chance de 13 ou mais", "O que acrescenta à chance de 13 ou mais do conjunto"]


def linhas_dos_pares(medidas: dict, rotulos: dict) -> list[list[str]]:
    return [
        [
            html.escape(f"{rotulos[a]} e {rotulos[b]}"), inteiro(p["apostas_em_comum"]),
            pct(p["sobreposicao_13"]),
        ]
        for p in medidas["pares"] for a, b in [p["ids"]]
    ]


CABECALHOS_PARES = ["Par de bilhetes", "Apostas idênticas nos dois", "Quanto os acertos coincidem (13 ou mais)"]


def frase_da_repeticao(medidas: dict) -> str:
    if medidas["apostas_repetidas"] == 0:
        return "Nenhuma aposta se repete entre os bilhetes: todo o dinheiro compra apostas diferentes."
    return (
        f"{inteiro(medidas['apostas_repetidas'])} aposta(s) aparecem em mais de um bilhete, o que corresponde a "
        f"{reais(medidas['custo_repetido'])} gastos em apostas repetidas (de {reais(medidas['custo'])} no total)."
    )


def frase_do_bilhete_unico(medidas: dict) -> str | None:
    u = medidas["bilhete_unico"]
    if u is None:
        return None
    sobra = f" (sobram {reais(u['sobra'])})" if u["sobra"] > 0.005 else ""
    mesmo = medidas["chance_13_ou_mais"]
    diferenca = u["chance_13_ou_mais"] - mesmo
    if abs(diferenca) < 1e-9:
        comparacao = "a mesma chance de 13 ou mais"
    elif diferenca > 0:
        comparacao = f"uma chance de 13 ou mais maior: {pct(u['chance_13_ou_mais'])} contra {pct(mesmo)}"
    else:
        comparacao = f"uma chance de 13 ou mais menor: {pct(u['chance_13_ou_mais'])} contra {pct(mesmo)}"
    return (
        f"Com o mesmo dinheiro, um único bilhete montado pela regra do app teria {inteiro(u['apostas'])} apostas "
        f"({u['duplos']} duplo(s) e {u['triplos']} triplo(s), {reais(u['custo'])}){sobra} e {comparacao}. "
        "É só uma comparação: o app não escolhe por você quantos bilhetes jogar."
    )


def mostrar_conjunto(jogos: list[dict], pcts: list[dict], bilhetes: list[dict]) -> dict | None:
    """Chances dos bilhetes escolhidos jogados juntos. `bilhetes`: [{'id', 'apostas', 'custo', 'marcacoes'}]."""
    try:
        medidas = cb.medidas_do_conjunto(pcts, bilhetes)
    except ValueError as erro:
        st.info(f"Não foi possível calcular o conjunto: {erro}")
        return None
    n = medidas["jogos"]
    rotulos = {b["id"]: rotulo_do_bilhete(b) for b in bilhetes}
    st.markdown("#### Chances do conjunto de bilhetes")
    with st.container(horizontal=True, wrap=True):
        st.metric("Custo total", reais(medidas["custo"]), help=f"{inteiro(medidas['apostas'])} aposta(s) em {medidas['bilhetes']} bilhete(s).", border=True)
        st.metric(f"Algum bilhete com {n} acertos", formatar_uma_em(medidas["chance_14"]), help=pct(medidas["chance_14"]), border=True)
        st.metric(f"Algum bilhete com {n - 1} ou mais", formatar_uma_em(medidas["chance_13_ou_mais"]), help=pct(medidas["chance_13_ou_mais"]), border=True)
        if medidas["bilhetes"] > 1:
            st.metric(f"Dois ou mais bilhetes com {n - 1}+", formatar_uma_em(medidas["chance_dois_ou_mais_bilhetes_13"]),
                      help="Quando os bilhetes se parecem, acertam juntos.", border=True)
    st.caption(
        "Os bilhetes disputam os mesmos jogos, então as chances não se somam: o cálculo percorre todos os resultados possíveis. "
        + nota_da_calibracao()
    )
    st.markdown(renderizar_tabela("Cada bilhete dentro do conjunto", CABECALHOS_POR_BILHETE, linhas_por_bilhete(medidas, rotulos)), unsafe_allow_html=True)
    st.markdown(frase_da_repeticao(medidas))
    if medidas["pares"]:
        st.markdown(renderizar_tabela("Sobreposição entre os bilhetes", CABECALHOS_PARES, linhas_dos_pares(medidas, rotulos)), unsafe_allow_html=True)
    comparacao = frase_do_bilhete_unico(medidas)
    if comparacao:
        st.markdown(comparacao)
    return medidas


def percentuais_atuais_do_concurso(conexao, numero_concurso: int) -> tuple[list[dict], list[dict]]:
    """(jogos do concurso na ordem, percentual final de cada um) com os números de hoje: calibrados e com o ajuste das notícias."""
    jogos = [
        dict(linha) for linha in conexao.execute(
            "SELECT j.id, j.num_jogo, j.casa_id, j.fora_id, j.data_jogo, pc.nome AS casa, pf.nome AS fora "
            "FROM jogos j JOIN participantes pc ON pc.id = j.casa_id JOIN participantes pf ON pf.id = j.fora_id "
            "WHERE j.concurso_numero = ? ORDER BY j.num_jogo", (numero_concurso,),
        )
    ]
    ajustes = ajustes_do_concurso(conexao, numero_concurso)
    return jogos, [percentuais_do_jogo(conexao, j["casa_id"], j["fora_id"], ajustes, j["data_jogo"])["final"] for j in jogos]

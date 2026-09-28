import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from estilo_caixa import renderizar_cartao, renderizar_titulo_cartao
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

import config
from importer.caixa_client import ErroImportacaoLoteca, importar_concurso, importar_programacao
from stats.cbf import classificacao_do_participante, resumo_curto_cbf
from stats.concursos import concurso_a_jogar, ultimo_encerrado as buscar_ultimo_encerrado
from stats.bilhete import montar_bilhete
from stats.fechamento import calcular
from stats.percentual import percentual_historico
from stats.prazo import formatar_restante, situacao_do_prazo
from stats.sugestao import sugerir_marcacao
from stats.temporada import desempenho_no_ano, resumo_curto

st.title("Concurso atual")
mostrar_aviso_responsabilidade()

conexao = obter_conexao()

if st.button("Atualizar dados da CAIXA (concurso a jogar e último apurado)"):
    try:
        programados = importar_programacao(conexao)
        apurado = importar_concurso(None, conexao)
        conexao.commit()
        st.success(f"Atualizado: concurso a jogar {', '.join(map(str, programados))}; último apurado {apurado}.")
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


numero_encerrado = buscar_ultimo_encerrado(conexao)
ultimo_encerrado = {"concurso_numero": numero_encerrado} if numero_encerrado else None
a_jogar = concurso_a_jogar(conexao)
concurso_vigente = a_jogar or conexao.execute("SELECT numero FROM concursos ORDER BY numero DESC LIMIT 1").fetchone()

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
                    "data": formatar_data_br(j["data_jogo"]),
                    "valor_casa": str(j["gols_casa"]) if j["gols_casa"] is not None else "-",
                    "valor_x": "" if not venceu_x else "X",
                    "valor_fora": str(j["gols_fora"]) if j["gols_fora"] is not None else "-",
                    "destaque_casa": venceu_casa,
                    "destaque_x": venceu_x,
                    "destaque_fora": venceu_fora,
                }
            )
        st.markdown(
            renderizar_cartao(f"1. Resultado do concurso {ultimo_encerrado['concurso_numero']} (encerrado)", linhas),
            unsafe_allow_html=True,
        )
        st.caption("O que já aconteceu de fato -- o placar real, tal como saiu. Serve de referência para conferir contra os dois cards abaixo.")

    # Card 2 -- percentual histórico do concurso vigente
    numero_vigente = concurso_vigente["numero"]
    jogos_vigente = _jogos_do_concurso(numero_vigente)
    if a_jogar:
        prazo = situacao_do_prazo(a_jogar["data_limite_aposta"], a_jogar["horario_fim_apostas"])
        if prazo["limite"]:
            hora = f" às {prazo['limite'].hour}h" if prazo["exato"] else " (dia do primeiro jogo, horário não informado)"
            estado = formatar_restante(prazo["restante"])
            texto = f"**Concurso {numero_vigente} (a jogar)** -- apostas até {formatar_data_br(a_jogar['data_limite_aposta'])}{hora} · {estado}"
            (st.success if prazo["aberto"] else st.warning)(texto)
    else:
        st.info(
            f"Nenhum concurso aberto encontrado; os cards 2 e 3 usam o concurso {numero_vigente} (já apurado). "
            "Use o botão acima para buscar a programação."
        )
    ano_atual = dt.date.today().year

    st.info(
        "**2. Percentual histórico** -- para cada jogo do concurso a jogar, a chance de vitória do "
        "mandante, empate ou vitória do visitante, calculada a partir de todo o histórico de gols "
        "desse mandante e desse visitante já importado (método Poisson, sem depender de odds de "
        "mercado -- ver `stats/percentual.py`). É o dado puro, sem nenhum ajuste ou opinião ainda."
    )

    linhas_pct = []
    dados_por_jogo = {}
    for j in jogos_vigente:
        pct = percentual_historico(conexao, j["casa_id"], j["fora_id"])
        maior = max(pct, key=pct.get)
        sugestao = sugerir_marcacao(pct)
        dados_por_jogo[j["id"]] = {"jogo": j, "pct": pct, "sugestao": sugestao}

        linhas_pct.append(
            {
                "num_jogo": j["num_jogo"],
                "casa": j["casa"],
                "fora": j["fora"],
                "data": formatar_data_br(j["data_jogo"]),
                "valor_casa": f"{pct['1']:.0f}%",
                "valor_x": f"{pct['X']:.0f}%",
                "valor_fora": f"{pct['2']:.0f}%",
                "destaque_casa": maior == "1",
                "destaque_x": maior == "X",
                "destaque_fora": maior == "2",
            }
        )

    st.markdown(
        renderizar_cartao(f"2. Percentual histórico -- concurso {numero_vigente}", linhas_pct),
        unsafe_allow_html=True,
    )

    # Card 3 -- bilhete interativo: o usuário marca, comparando com o
    # percentual histórico e com o desempenho de cada time no ano em curso.
    st.info(
        "**3. Seu bilhete** -- marque abaixo como se fosse o volante de aposta de verdade (pode marcar "
        "mais de uma coluna por jogo, igual a duplo/triplo). Ao lado de cada jogo está o percentual "
        f"histórico (card 2) e o desempenho de cada time só em {ano_atual} (o ano em curso), para você "
        "confrontar sua marcação com o dado antes de decidir -- a marcação já vem preenchida com uma "
        "sugestão que cabe no seu orçamento e no máximo oficial do volante, mas você pode mudar "
        "qualquer jogo."
    )
    st.markdown(renderizar_titulo_cartao(f"3. Seu bilhete -- concurso {numero_vigente}"), unsafe_allow_html=True)

    orcamento = st.number_input(
        "Quanto quer gastar neste bilhete (R$)? A marcação inicial se ajusta a esse valor.",
        min_value=4.0,
        max_value=float(config.BILHETE_MAX_APOSTAS * 2),
        value=config.BILHETE_ORCAMENTO_PADRAO,
        step=2.0,
        help="Mínimo oficial: R$ 4,00 (1 duplo). Máximo: R$ 1.728,00 (864 apostas). Cada aposta custa R$ 2,00.",
    )
    proposta = montar_bilhete([dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente], orcamento=orcamento)
    marcacao_inicial = {j["id"]: proposta["marcacoes"][i] for i, j in enumerate(jogos_vigente)}
    st.caption(
        f"Sugestão para R$ {orcamento:.2f}: {proposta['duplos']} duplo(s) e {proposta['triplos']} triplo(s), "
        f"R$ {proposta['custo']:.2f}. Os duplos e triplos vão para os jogos em que cobrir mais uma coluna "
        "rende mais chance por real gasto. É uma estimativa: não garante acerto."
    )

    total_triplos = total_duplos = 0
    marcacoes = {}
    for j in jogos_vigente:
        dado = dados_por_jogo[j["id"]]
        pct, sugestao = dado["pct"], dado["sugestao"]
        forma_casa = resumo_curto(desempenho_no_ano(conexao, j["casa_id"], ano_atual))
        forma_fora = resumo_curto(desempenho_no_ano(conexao, j["fora_id"], ano_atual))

        cbf_casa = classificacao_do_participante(conexao, j["casa_id"])
        cbf_fora = classificacao_do_participante(conexao, j["fora_id"])
        extra_casa = f" · {resumo_curto_cbf(cbf_casa)}" if cbf_casa else ""
        extra_fora = f" · {resumo_curto_cbf(cbf_fora)}" if cbf_fora else ""

        col_info, col_marca = st.columns([3, 2])
        with col_info:
            st.markdown(
                f"**{j['num_jogo']}. {j['casa']}** ({pct['1']:.0f}% · {forma_casa}{extra_casa}) "
                f"x **{j['fora']}** ({pct['2']:.0f}% · {forma_fora}{extra_fora}) — empate {pct['X']:.0f}%"
            )
        with col_marca:
            escolha = st.multiselect(
                "Marcação",
                options=["1", "X", "2"],
                default=marcacao_inicial[j["id"]],
                key=f"bilhete_{j['id']}_{orcamento}",
                label_visibility="collapsed",
            )
        marcacoes[j["id"]] = escolha or ["1"]
        if len(escolha) == 2:
            total_duplos += 1
        elif len(escolha) == 3:
            total_triplos += 1

    custo = calcular(total_triplos, total_duplos)
    st.success(
        f"Seu bilhete: {total_duplos} duplo(s) e {total_triplos} triplo(s) -- "
        f"{custo['apostas']} combinações, R$ {custo['valor_reais']:.2f} "
        "(ver página 'Fechamento de bolão' para organizar como Bolão CAIXA)."
    )
    if custo["apostas"] > config.BILHETE_MAX_APOSTAS:
        st.warning(
            "Esse bilhete passa do máximo oficial da Loteca (864 apostas) -- não seria aceito num "
            "volante de verdade. Remova algum duplo/triplo para caber no limite."
        )
    if total_duplos + total_triplos == 0:
        st.warning("O volante da Loteca exige ao menos 1 duplo (mínimo de R$ 4,00). Marque duas colunas em algum jogo.")
    st.caption(
        "Mudar o valor do orçamento refaz a sugestão inicial (e descarta as alterações manuais). "
        "Ainda sem ajuste de notícias para concursos futuros até a varredura semanal rodar."
    )

conexao.close()

import datetime as dt
import email.utils
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from estilo_caixa import renderizar_cartao, renderizar_titulo_cartao
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

import config
from externo.percentual_final import ajustes_do_concurso, percentuais_do_jogo
from importer.caixa_client import ErroImportacaoLoteca, importar_concurso, importar_programacao
from stats.cbf import classificacao_do_participante, resumo_curto_cbf
from stats.contexto import selo_da_posicao
from stats.concursos import concurso_a_jogar, ultimo_encerrado as buscar_ultimo_encerrado
from stats.bilhete import montar_bilhete
from stats.fechamento import calcular
from stats.prazo import formatar_restante, situacao_do_prazo
from stats.temporada import desempenho_no_ano, resumo_curto

st.title("Concurso atual")
mostrar_aviso_responsabilidade()


def _texto_percentual(final: float, historico: float) -> str:
    """Ex.: '58% (+2)' quando o ajuste de notícias mexeu no número; senão, só '56%'."""
    diferenca = final - historico
    return f"{final:.0f}%" + (f" ({diferenca:+.0f})" if abs(diferenca) >= 0.5 else "")


def _texto_seguro(texto: str) -> str:
    """Manchetes vêm de fora: tira caracteres que o Markdown interpretaria."""
    limpo = "".join(c for c in (texto or "") if c not in "[]()*`<>\\")
    return limpo.replace("_", " ")[:200]


def _data_publicacao_br(texto_rfc822: str) -> str | None:
    """RSS traz a data em RFC 822 ('Mon, 29 Sep 2026 10:00:00 GMT'); mostra
    dd/mm/aaaa. None se vazio ou não reconhecido -- não inventa data."""
    if not texto_rfc822:
        return None
    try:
        return email.utils.parsedate_to_datetime(texto_rfc822).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return None


def _link_seguro(url: str) -> str | None:
    if url and url.startswith(("http://", "https://")) and not any(c in url for c in " ()<>\""):
        return url
    return None


def mostrar_motivos_do_ajuste(jogos, calculos):
    com_ajuste = [j for j in jogos if calculos[j["id"]]["ajustes"]["casa"] or calculos[j["id"]]["ajustes"]["fora"]]
    if not com_ajuste:
        return
    with st.expander("Por que os percentuais foram ajustados (notícias da varredura)"):
        st.caption(
            "O efeito no jogo é o ajuste do mandante menos o do visitante, limitado a "
            f"{config.AJUSTE_EXTERNO_TETO_PONTOS:.0f} pontos. Os pontos que o lado favorecido ganha saem dos outros dois "
            "resultados, na proporção deles, e a soma continua 100%. Só a manchete, o veículo e o link são guardados."
        )
        for j in com_ajuste:
            calculo = calculos[j["id"]]
            if calculo["ajustado"]:
                lado = "do mandante" if calculo["deslocamento"] > 0 else "do visitante"
                efeito = f"efeito líquido de {abs(calculo['deslocamento']):.1f} pontos a favor {lado}"
            else:
                efeito = "os ajustes se compensam (efeito líquido zero)"
            st.markdown(f"**{j['num_jogo']}. {j['casa']} x {j['fora']}** — {efeito}")
            for lado, nome in (("casa", j["casa"]), ("fora", j["fora"])):
                ajuste = calculo["ajustes"][lado]
                if not ajuste:
                    continue
                st.markdown(f"- {nome}: {ajuste['ajuste']:+.1f} pontos ({_texto_seguro(ajuste['resumo'])})")
                for evidencia in ajuste["evidencias"]:
                    link = _link_seguro(evidencia.get("url", ""))
                    veiculo = _texto_seguro(evidencia.get("fonte", "")) or "veículo não informado"
                    manchete = _texto_seguro(evidencia.get("manchete", ""))
                    quando = _data_publicacao_br(evidencia.get("publicado_em", ""))
                    linha = f"    - «{manchete}» — {veiculo}"
                    linha += f" — publicada em {quando}" if quando else ""
                    linha += f" — [abrir]({link})" if link else ""
                    st.markdown(linha)

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
        "**2. Percentual** -- para cada jogo do concurso a jogar, a chance de vitória do mandante, empate ou "
        "vitória do visitante, calculada a partir do histórico de gols dos dois times já importado (método "
        "Poisson, sem odds de mercado -- ver `stats/percentual.py`). Quando a varredura semanal de notícias já "
        "rodou para este concurso, o ajuste (limitado a "
        f"{config.AJUSTE_EXTERNO_TETO_PONTOS:.0f} pontos) já está aplicado: o número é o percentual final e o valor entre "
        "parênteses mostra quantos pontos vieram das notícias. Sem varredura, é só o histórico."
    )

    linhas_pct = []
    dados_por_jogo = {}
    ajustes = ajustes_do_concurso(conexao, numero_vigente)
    calculos = {}
    for j in jogos_vigente:
        calculo = percentuais_do_jogo(conexao, j["casa_id"], j["fora_id"], ajustes)
        calculos[j["id"]] = calculo
        pct, historico = calculo["final"], calculo["historico"]
        maior = max(pct, key=pct.get)
        dados_por_jogo[j["id"]] = {"jogo": j, "pct": pct, "historico": historico}

        linhas_pct.append(
            {
                "num_jogo": j["num_jogo"],
                "casa": j["casa"],
                "fora": j["fora"],
                "data": formatar_data_br(j["data_jogo"]),
                "valor_casa": _texto_percentual(pct["1"], historico["1"]),
                "valor_x": _texto_percentual(pct["X"], historico["X"]),
                "valor_fora": _texto_percentual(pct["2"], historico["2"]),
                "destaque_casa": maior == "1",
                "destaque_x": maior == "X",
                "destaque_fora": maior == "2",
            }
        )

    st.markdown(
        renderizar_cartao(f"2. Percentual -- concurso {numero_vigente}", linhas_pct),
        unsafe_allow_html=True,
    )
    if ajustes:
        ultima = max(a["coletado_em"] for a in ajustes.values())
        quando = dt.datetime.fromisoformat(ultima).strftime("%d/%m/%Y %H:%M")
        n_ajustados = sum(1 for a in ajustes.values() if a["ajuste"])
        st.caption(f"Última varredura de notícias: {quando} · {n_ajustados} de {len(ajustes)} participantes com ajuste.")
    else:
        st.caption("Sem varredura de notícias para este concurso: os percentuais são só o histórico.")
    mostrar_motivos_do_ajuste(jogos_vigente, calculos)

    # Card 3 -- bilhete interativo: o usuário marca, comparando com o
    # percentual histórico e com o desempenho de cada time no ano em curso.
    st.info(
        "**3. Seu bilhete** -- marque abaixo como se fosse o volante de aposta de verdade (pode marcar "
        "mais de uma coluna por jogo, igual a duplo/triplo). Ao lado de cada jogo está o percentual "
        f"do card 2 e o desempenho de cada time só em {ano_atual} (o ano em curso), para você "
        "confrontar sua marcação com o dado antes de decidir -- a marcação já vem preenchida com uma "
        "sugestão de aposta simples (no máximo um duplo ou um triplo), mas você pode mudar "
        "qualquer jogo."
    )
    st.markdown(renderizar_titulo_cartao(f"3. Seu bilhete -- concurso {numero_vigente}"), unsafe_allow_html=True)

    proposta = montar_bilhete([dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente])
    marcacao_inicial = {j["id"]: proposta["marcacoes"][i] for i, j in enumerate(jogos_vigente)}
    jogo_multiplo = jogos_vigente[proposta["jogo_multiplo"]]
    tipo_multiplo = "triplo" if proposta["triplos"] else "duplo"
    st.caption(
        f"Sugestão de partida: aposta simples em todos os jogos, com um único {tipo_multiplo} no jogo "
        f"{jogo_multiplo['num_jogo']} ({jogo_multiplo['casa']} x {jogo_multiplo['fora']}), o mais incerto pelo "
        f"histórico -- {proposta['apostas']} apostas, R$ {proposta['custo']:.2f}. É uma estimativa: não garante acerto."
    )

    total_triplos = total_duplos = 0
    marcacoes = {}
    for j in jogos_vigente:
        dado = dados_por_jogo[j["id"]]
        pct, historico = dado["pct"], dado["historico"]
        forma_casa = resumo_curto(desempenho_no_ano(conexao, j["casa_id"], ano_atual))
        forma_fora = resumo_curto(desempenho_no_ano(conexao, j["fora_id"], ano_atual))

        cbf_casa = classificacao_do_participante(conexao, j["casa_id"])
        cbf_fora = classificacao_do_participante(conexao, j["fora_id"])
        selo_casa = selo_da_posicao(cbf_casa["serie"], cbf_casa["ano"], cbf_casa["posicao"]) if cbf_casa else None
        selo_fora = selo_da_posicao(cbf_fora["serie"], cbf_fora["ano"], cbf_fora["posicao"]) if cbf_fora else None
        extra_casa = f" · {resumo_curto_cbf(cbf_casa)}" if cbf_casa else ""
        extra_fora = f" · {resumo_curto_cbf(cbf_fora)}" if cbf_fora else ""
        extra_casa += f" · zona: {selo_casa}" if selo_casa else ""
        extra_fora += f" · zona: {selo_fora}" if selo_fora else ""

        col_info, col_marca = st.columns([3, 2])
        with col_info:
            st.markdown(
                f"**{j['num_jogo']}. {j['casa']}** ({_texto_percentual(pct['1'], historico['1'])} · {forma_casa}{extra_casa}) "
                f"x **{j['fora']}** ({_texto_percentual(pct['2'], historico['2'])} · {forma_fora}{extra_fora}) — "
                f"empate {_texto_percentual(pct['X'], historico['X'])}"
            )
        with col_marca:
            escolha = st.multiselect(
                "Marcação",
                options=["1", "X", "2"],
                default=marcacao_inicial[j["id"]],
                key=f"bilhete_{j['id']}",
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
        "Percentuais com o ajuste da última varredura de notícias (o valor entre parênteses mostra o efeito em pontos)."
        if ajustes
        else "Sem varredura de notícias para este concurso: os percentuais são só o histórico."
    )

conexao.close()

import datetime as dt
import email.utils
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from ano_em_curso_ui import mostrar_ano_em_curso, resumo_do_ano
from calibracao_ui import mostrar_calibracao
from chances_ui import mostrar_chances_do_bilhete
from estilo_caixa import renderizar_cartao, renderizar_tabela, renderizar_titulo_cartao
from noticias_ui import mostrar_manchetes_lidas
from perfil_ui import mostrar_perfil_do_concurso
from premiacao_ui import mostrar_premiacao
from sugestoes_ui import (
    complexidade_da_tela,
    mostrar_sugestoes,
    texto_da_calibracao,
    texto_da_complexidade,
)
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao
from variantes_ui import mostrar_variantes
from volante_ui import jogos_para_o_volante, renderizar_volante

import config
from externo.ajuste import evidencias_informativas
from externo.percentual_final import ajustes_do_concurso, percentuais_do_jogo
from importer.caixa_client import ErroImportacaoLoteca, importar_concurso, importar_programacao
from stats.cbf import classificacao_do_participante, resumo_curto_cbf
from stats.contexto import selo_da_posicao
from stats.concursos import concurso_a_jogar, ultimo_encerrado as buscar_ultimo_encerrado
from stats.analise_palpite import NOME_CATEGORIA, ZEBRA, analisar_palpite, formatar_uma_em
from stats.bilhete import PRECO_APOSTA, justificativa_da_sugestao, montar_bilhete, validar_volante
from stats.bilhetes_salvos import bilhete_igual, jogos_do_bilhete, listar_bilhetes, salvar_bilhete
from stats.variantes_bilhete import ORIGEM_VOLANTE, nome_da_origem
from stats.ano_em_curso import frase_do_lado
from stats.cobertura import cobertura_do_concurso
from stats.retrato import gravar_retrato, retrato_do_jogo, retrato_geral
from stats.painel import participantes_do_concurso
from stats.prazo import formatar_restante, situacao_do_prazo
from stats.premiacao import reais
from stats.temporada import desempenho_no_ano, resumo_curto
from stats.versoes_palpite import (
    LimiteDeVersoes,
    diferencas,
    frase_da_mudanca,
    guardar_versao,
    ligar_ao_bilhete,
    listar_versoes,
)

COLUNAS_VOLANTE = ("1", "X", "2")
LARGURA_BLOCO_JOGO = 320  # px: cabe em celular de 375 px e forma 2-3 blocos por linha no computador
LARGURA_QUADRADO = 80  # px: quadrado + percentual com "(maior)" sem cortar

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

def mostrar_noticias_de_contexto(jogos, ajustes):
    """Contratação, saída, troca de técnico e atraso de salário: aparecem como
    contexto, com manchete e link, mas não mexem no percentual (Fase Q1)."""
    linhas = []
    for j in jogos:
        for participante_id, nome in ((j["casa_id"], j["casa"]), (j["fora_id"], j["fora"])):
            registro = ajustes.get(participante_id)
            for evidencia in evidencias_informativas(registro["evidencias"] if registro else []):
                link = _link_seguro(evidencia.get("url", ""))
                veiculo = _texto_seguro(evidencia.get("fonte", "")) or "veículo não informado"
                quando = _data_publicacao_br(evidencia.get("publicado_em", ""))
                linha = f"- **{nome}** · {evidencia['nome_sinal']}: «{_texto_seguro(evidencia.get('manchete', ''))}» — {veiculo}"
                linha += f" — publicada em {quando}" if quando else ""
                linha += f" — [abrir]({link})" if link else ""
                linhas.append(linha)
    if not linhas:
        return
    with st.expander(f"Notícias de contexto: contratações, saídas, técnico e salários ({len(linhas)})"):
        st.caption(
            "Estas notícias NÃO mexem no percentual: ainda não foi medido se esses fatos costumam melhorar ou piorar "
            "o desempenho (isso é a Fase Q4). Servem para você considerar na sua marcação."
        )
        for linha in linhas:
            st.markdown(linha)


def _celula(texto: str) -> str:
    """Texto de fora (nome de time) seguro dentro da tabela HTML."""
    return html.escape(str(texto))


def mostrar_analise(analise: dict, conexao=None, duplos: int = 0, triplos: int = 0,
                    complexidade: dict[int, dict] | None = None) -> None:
    """Só apresentação: as regras estão em stats/analise_palpite.py, stats/sugestoes_bilhete.py
    e stats/calibracao_bilhete.py. `complexidade`: {num_jogo: complexidade do jogo}."""
    with st.container(border=True):
        st.markdown("#### Análise do seu palpite")
        st.caption(
            "Leitura por regra sobre os percentuais do app. Não diz se a marcação está certa: loteria é jogo de "
            "azar e, pelo teste da página 'Confiabilidade do modelo', esses percentuais são uma estimativa fraca."
        )
        chance, n = analise["chance"], analise["chance"]["jogos"]
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Chance de {n} acertos (pelos percentuais)", formatar_uma_em(chance["chance_todos"]))
        c2.metric(f"Chance de {n - 1} ou mais (pelos percentuais)", formatar_uma_em(chance["chance_todos_menos_um_ou_mais"]))
        c3.metric("Acertos esperados", f"{chance['acertos_esperados']:.1f}".replace(".", ","))
        # Estudo E1-E4 (aprovado em 30/09/2026): a chance acima é otimista; ao lado dela, o que aconteceu de fato.
        if conexao is not None:
            st.info(texto_da_calibracao(conexao, duplos, triplos))
        for frase in analise["frases"]:
            st.markdown(f"- {frase}")

        # Tabela em HTML dentro de um contêiner com rolagem própria: no celular
        # ela rola para o lado em vez de ser cortada.
        linhas = []
        for j in analise["jogos"]:
            leitura = NOME_CATEGORIA[j["categoria"]]
            if j["zebras"] and j["categoria"] != ZEBRA:
                leitura += f" · inclui zebra ({', '.join(j['zebras'])})"
            if j["sem_base_propria"]:
                leitura += " · sem base própria"
            celula_complexidade = (
                f"<td>{texto_da_complexidade(complexidade[j['num_jogo']])}</td>"
                if complexidade and j["num_jogo"] in complexidade else ""
            )
            linhas.append(
                f"<tr><td>{j['num_jogo']}. {_celula(j['casa'])} x {_celula(j['fora'])}</td>"
                f"<td>{', '.join(j['marcacoes'])}</td><td>{min(j['chance_coberta'], 100):.0f}%</td>"
                f"<td>{j['favorito']} ({j['pct_favorito']:.0f}%)</td><td>{html.escape(leitura)}</td>"
                f"{celula_complexidade}</tr>"
            )
        cabecalho_complexidade = "<th scope='col'>Complexidade do jogo</th>" if complexidade else ""
        st.markdown(
            "<div style='overflow-x:auto'><table style='min-width:560px'>"
            "<caption style='text-align:left;font-weight:600'>Jogo a jogo</caption>"
            "<thead><tr><th scope='col'>Jogo</th><th scope='col'>Você marcou</th><th scope='col'>Chance coberta</th>"
            f"<th scope='col'>Favorito dos dados</th><th scope='col'>Leitura</th>{cabecalho_complexidade}</tr></thead>"
            f"<tbody>{''.join(linhas)}</tbody></table></div>",
            unsafe_allow_html=True,
        )

        if analise["multiplos"]:
            st.markdown("**Seus duplos e triplos**")
            for m in analise["multiplos"]:
                vezes = 3 if m["tipo"] == "triplo" else 2
                st.markdown(
                    f"- Jogo {m['num_jogo']} ({m['tipo']}): a chance do jogo vai de {m['chance_antes']:.0f}% para "
                    f"{min(m['chance_depois'], 100):.0f}% (+{m['ganho']:.0f} pontos); o custo do bilhete é multiplicado por {vezes}."
                )
        if analise["melhores_duplos"]:
            st.markdown("**Onde um duplo rende mais** (entre os jogos marcados com um só resultado)")
            for d in analise["melhores_duplos"]:
                st.markdown(
                    f"- Jogo {d['num_jogo']}: acrescentar a coluna {d['coluna_extra']} soma {d['ganho']:.0f} pontos de chance."
                    " (Isso aumenta o custo do bilhete.)"
                )
        if conexao is not None:
            mostrar_sugestoes(conexao, analise, duplos, triplos)


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
            renderizar_cartao(
                f"1. Resultado do concurso {ultimo_encerrado['concurso_numero']} (encerrado)", linhas, "resultado vencedor"
            ),
            unsafe_allow_html=True,
        )
        st.caption("O que já aconteceu de fato -- o placar real, tal como saiu. Serve de referência para conferir contra os dois cards abaixo.")
        # Valores do concurso apurado (pedido do usuário, 30/09/2026): arrecadação, ganhadores, prêmio e acumulados.
        with st.expander(f"Valores do concurso {ultimo_encerrado['concurso_numero']}: arrecadação, ganhadores e prêmios", expanded=True):
            mostrar_premiacao(conexao, ultimo_encerrado["concurso_numero"], rotulo="Premiação do último concurso apurado")

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
        "vitória do visitante, sem odds de mercado. Clubes da mesma série A ou B: média entre o modelo da temporada "
        "da CBF e o Elo de clubes. Demais jogos entre clubes: Elo de clubes (com todos os jogos da Loteca). Duas "
        "seleções: Elo das seleções. "
        "A origem de cada jogo está em 'Ver como cada percentual foi corrigido'. Quando a varredura semanal de notícias já "
        "rodou para este concurso, o ajuste (limitado a "
        f"{config.AJUSTE_EXTERNO_TETO_PONTOS:.0f} pontos) já está aplicado: o número é o percentual final e o valor entre "
        "parênteses mostra quantos pontos vieram das notícias. Sem varredura, é só o histórico."
    )

    linhas_pct = []
    dados_por_jogo = {}
    ajustes = ajustes_do_concurso(conexao, numero_vigente)
    calculos = {}
    for j in jogos_vigente:
        calculo = percentuais_do_jogo(conexao, j["casa_id"], j["fora_id"], ajustes, j["data_jogo"])
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
        renderizar_cartao(f"2. Percentual -- concurso {numero_vigente}", linhas_pct, "maior percentual"),
        unsafe_allow_html=True,
    )
    if ajustes:
        ultima = max(a["coletado_em"] for a in ajustes.values())
        quando = dt.datetime.fromisoformat(ultima).strftime("%d/%m/%Y %H:%M")
        n_ajustados = sum(1 for a in ajustes.values() if a["ajuste"])
        st.caption(f"Última varredura de notícias: {quando} · {n_ajustados} de {len(ajustes)} participantes com ajuste.")
    else:
        st.caption("Sem varredura de notícias para este concurso: os percentuais são só o histórico.")
    mostrar_calibracao(jogos_vigente, calculos)
    mostrar_motivos_do_ajuste(jogos_vigente, calculos)
    mostrar_noticias_de_contexto(jogos_vigente, ajustes)
    mostrar_manchetes_lidas(
        conexao, numero_vigente,
        list({p["id"]: p for j in jogos_vigente
              for p in ({"id": j["casa_id"], "nome": j["casa"]}, {"id": j["fora_id"], "nome": j["fora"]})}.values()),
    )

    # Ano em curso sempre visível, logo antes do volante (pedido do usuário,
    # 30/09/2026): quem marca vê primeiro como cada time está indo no ano.
    st.markdown(renderizar_titulo_cartao(f"Ano em curso ({ano_atual}) -- concurso {numero_vigente}"), unsafe_allow_html=True)
    jogos_do_concurso_ano = participantes_do_concurso(conexao, numero_vigente)
    resumo_ano_concurso = resumo_do_ano(conexao, jogos_do_concurso_ano, ano_atual)
    # Complexidade de cada jogo (estudo E1-E4, aprovado em 30/09/2026): no teste com 16.973 jogos o favorito
    # acertou 49,7% nos de complexidade baixa, 44,0% nos de média e 37,2% nos de alta.
    sem_base_por_jogo = {j["id"]: calculos[j["id"]]["origem"] == "frequencia_global" for j in jogos_vigente}
    complexidade_por_jogo = complexidade_da_tela(
        [{"num_jogo": j["num_jogo"], "pct": dados_por_jogo[j["id"]]["pct"], "sem_base_propria": sem_base_por_jogo[j["id"]]}
         for j in jogos_vigente],
        resumo_ano_concurso,
    )
    mostrar_ano_em_curso(
        conexao, jogos_do_concurso_ano, ano_atual, "concurso", com_grafico=False, resumo=resumo_ano_concurso,
        complexidade={n: texto_da_complexidade(c) for n, c in complexidade_por_jogo.items()},
    )
    st.caption(
        "Complexidade do jogo: quão difícil ele é de marcar, pelos percentuais e pelo ano em curso. Nos concursos "
        "passados, o favorito dos dados acertou cerca de 50% nos jogos de complexidade baixa, 44% nos de média e 37% "
        "nos de alta. É uma leitura, não uma previsão."
    )
    # Cobertura de dados (item A2 do plano v2, 07/10/2026): o app diz quando sabe pouco de um jogo.
    cobertura_por_jogo = cobertura_do_concurso(conexao, jogos_vigente, resumo_ano_concurso, ajustes, dt.datetime.now(),
                                               {j["id"]: calculos[j["id"]]["origem"] for j in jogos_vigente})
    n_incertos = sum(1 for c in cobertura_por_jogo.values() if c["alta_incerteza"])
    with st.expander(f"Cobertura de dados dos jogos ({n_incertos} com alta incerteza)"):
        st.caption(
            "Quanto o app sabe de cada jogo: completa (temporada da CBF, Séries A e B), seleções (Elo), parcial "
            "(Série C ou só jogos da Loteca) ou baixa (sem base própria). Parcial e baixa levam o aviso de alta "
            "incerteza no volante. A sugestão do app não muda por causa disso."
        )
        st.markdown(
            renderizar_tabela(
                "Cobertura por jogo",
                ["Jogo", "Nível", "O que falta"],
                [
                    [
                        f"{j['num_jogo']}. {html.escape(j['casa'])} x {html.escape(j['fora'])}",
                        ("⚠ " if cobertura_por_jogo[j["id"]]["alta_incerteza"] else "")
                        + html.escape(cobertura_por_jogo[j["id"]]["nome_nivel"]),
                        "<br>".join(html.escape(f) for f in cobertura_por_jogo[j["id"]]["faltas"]) or "-",
                    ]
                    for j in jogos_vigente
                ],
            ),
            unsafe_allow_html=True,
        )

    # Termômetro do perfil do concurso (S6, aprovado em 08/10/2026): só informativo, com a medida de acerto ao lado.
    tipos = {linha["id"]: (linha["tipo"], linha["pais_ou_uf"]) for linha in conexao.execute(
        "SELECT id, tipo, pais_ou_uf FROM participantes")}
    mostrar_perfil_do_concurso(conexao, numero_vigente, [
        {"p": dados_por_jogo[j["id"]]["pct"], "casa": tipos[j["casa_id"]], "fora": tipos[j["fora_id"]]} for j in jogos_vigente
    ])

    # Card 3 -- volante: 3 quadrados por jogo (1, X, 2), como o volante da
    # CAIXA. Começa em branco (pedido do usuário, 29/09/2026); a sugestão do
    # app só entra se ele clicar no botão. Jogo em branco bloqueia o salvamento.
    st.info(
        "**3. Seu palpite** -- marque os quadrados como no volante: um quadrado é aposta simples, dois é "
        "duplo, três é triplo. Embaixo de cada quadrado está o percentual do card 2 (em negrito, o maior do jogo). "
        "O volante começa em branco; use **Preencher com a sugestão** se quiser partir da sugestão do app."
    )
    st.markdown(renderizar_titulo_cartao(f"3. Seu palpite -- concurso {numero_vigente}"), unsafe_allow_html=True)

    proposta = montar_bilhete([dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente])

    def _chave(jogo_id: int, coluna: str) -> str:
        return f"volante_{numero_vigente}_{jogo_id}_{coluna}"

    def _preencher_com_sugestao():
        for i, jogo in enumerate(jogos_vigente):
            for coluna in COLUNAS_VOLANTE:
                st.session_state[_chave(jogo["id"], coluna)] = coluna in proposta["marcacoes"][i]

    def _limpar_volante():
        for jogo in jogos_vigente:
            for coluna in COLUNAS_VOLANTE:
                st.session_state[_chave(jogo["id"], coluna)] = False

    with st.container(horizontal=True):
        st.button("Preencher com a sugestão", on_click=_preencher_com_sugestao)
        st.button("Limpar", on_click=_limpar_volante)
    jogo_multiplo = jogos_vigente[proposta["jogo_multiplo"]]
    tipo_multiplo = "triplo" if proposta["triplos"] else "duplo"
    st.caption(
        f"A sugestão do app é aposta simples em todos os jogos, com um único {tipo_multiplo} no jogo "
        f"{jogo_multiplo['num_jogo']} ({jogo_multiplo['casa']} x {jogo_multiplo['fora']}), o mais incerto pelo "
        f"histórico -- {proposta['apostas']} apostas, {reais(proposta['custo'])}. É uma estimativa: não garante acerto."
    )
    # Justificativa da sugestão (plano v2, item D3): só fatos guardados, sem texto livre.
    justificativa = justificativa_da_sugestao(
        [dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente], proposta,
        [f"{j['casa']} x {j['fora']}" for j in jogos_vigente], [cobertura_por_jogo[j["id"]] for j in jogos_vigente],
    )
    st.caption(
        f"**Por que o {justificativa['tipo']} no jogo {justificativa['jogo']}:** {justificativa['motivo']}"
        + (f"; apoio: {'; '.join(justificativa['apoio'])}" if justificativa["apoio"] else "")
        + f". Risco: {justificativa['risco']}."
        + (f" Alternativa descartada: {justificativa['alternativa']}." if justificativa["alternativa"] else "")
    )

    # Cada jogo é um bloco: times em cima, os 3 quadrados embaixo. Os blocos
    # ficam lado a lado em tela larga e um embaixo do outro no celular (com
    # st.columns, a linha inteira empilhava e os nomes ficavam espremidos).
    # Quadrado com só a coluna no rótulo, para nunca ser cortado, e o
    # percentual logo abaixo -- em negrito e com "(maior)" quando é o maior do
    # jogo, para não depender só do negrito.
    st.caption("1 = vitória do mandante · X = empate · 2 = vitória do visitante")
    with st.container(horizontal=True, wrap=True, gap="small"):
        for j in jogos_vigente:
            pct = dados_por_jogo[j["id"]]["pct"]
            maior = max(pct, key=pct.get)
            with st.container(border=True, width=LARGURA_BLOCO_JOGO):
                st.markdown(f"**{j['num_jogo']}.** {html.escape(j['casa'])} **x** {html.escape(j['fora'])}")
                if cobertura_por_jogo[j["id"]]["alta_incerteza"]:
                    st.caption(f":material/warning: **Alta incerteza:** poucos dados "
                               f"({cobertura_por_jogo[j['id']]['nome_nivel'].lower()})")
                with st.container(horizontal=True, wrap=False, gap="small"):
                    for coluna in COLUNAS_VOLANTE:
                        with st.container(width=LARGURA_QUADRADO, gap=None):
                            st.checkbox(coluna, key=_chave(j["id"], coluna))
                            percentual = f"{pct[coluna]:.0f}%"
                            st.caption(f"**{percentual}** (maior)" if coluna == maior else percentual)

    marcacoes_lista = [
        [coluna for coluna in COLUNAS_VOLANTE if st.session_state.get(_chave(j["id"], coluna))] for j in jogos_vigente
    ]
    volante = validar_volante(marcacoes_lista)
    if volante["marcados"] == 0:
        st.info(f"0 de {volante['total']} jogos marcados. Marque os quadrados ou use **Preencher com a sugestão**.")
    else:
        st.info(
            f"{volante['marcados']} de {volante['total']} jogos marcados · {volante['duplos']} duplo(s) · "
            f"{volante['triplos']} triplo(s) · **{volante['apostas']} aposta(s), {reais(volante['custo'])}** "
            "(ver página 'Fechamento de bolão' para organizar como Bolão CAIXA)."
        )
    if volante["apostas"] > config.BILHETE_MAX_APOSTAS:
        st.warning(f"Passa do máximo oficial de {config.BILHETE_MAX_APOSTAS} apostas. Tire algum duplo ou triplo.")
    elif not volante["jogos_sem_marcacao"]:
        # Chances do bilhete com as marcações atuais, sem precisar clicar (pedido do usuário, 01/10/2026).
        mostrar_chances_do_bilhete(
            jogos_vigente, [dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente], marcacoes_lista
        )

    # Análise do palpite (item 20): por regra, sob demanda, e guardada ao salvar.
    with st.expander("Anotar o motivo das marcações (opcional)"):
        st.caption(
            "O que você sabe e o app não coleta. Fica guardado com o bilhete para, com o tempo, mostrar em "
            "'Meus bilhetes' se esses motivos acertam mais ou menos."
        )
        for j in jogos_vigente:
            st.multiselect(
                f"{j['num_jogo']}. {j['casa']} x {j['fora']}",
                options=config.ANALISE_MOTIVOS,
                key=f"motivo_{numero_vigente}_{j['id']}",
                placeholder="Sem motivo anotado",
            )

    analise = None
    if not volante["jogos_sem_marcacao"]:
        analise = analisar_palpite(
            [
                {
                    "jogo_id": j["id"], "num_jogo": j["num_jogo"], "casa": j["casa"], "fora": j["fora"],
                    "pct": dados_por_jogo[j["id"]]["pct"], "marcacoes": marcadas,
                    "sem_base_propria": sem_base_por_jogo[j["id"]],
                }
                for j, marcadas in zip(jogos_vigente, marcacoes_lista)
            ]
        )

    chave_analise = f"analise_aberta_{numero_vigente}"
    if not st.session_state.get(chave_analise):
        st.button("Analisar meu palpite", on_click=lambda: st.session_state.update({chave_analise: True}))
    else:
        if analise is None:
            faltam = ", ".join(map(str, volante["jogos_sem_marcacao"]))
            st.info(f"Para analisar, marque todos os jogos. Falta(m): {faltam}.")
        else:
            mostrar_analise(analise, conexao, volante["duplos"], volante["triplos"], complexidade_por_jogo)
        st.button("Fechar análise", on_click=lambda: st.session_state.update({chave_analise: False}))

    # Versões do palpite (pedido do usuário, 30/09/2026): guardar cada tentativa,
    # reanalisar, comparar e voltar a uma versão antes de salvar. Gravadas no banco
    # (decisão do usuário) para, depois do resultado, aprender se as mudanças ajudaram.
    marcacoes_atuais = {j["id"]: m for j, m in zip(jogos_vigente, marcacoes_lista)}
    percentuais_atuais = {j["id"]: dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente}
    num_jogo_por_id = {j["id"]: j["num_jogo"] for j in jogos_vigente}
    with st.container(border=True):
        st.markdown("#### Versões deste palpite")
        st.caption(
            "Guarde cada tentativa para comparar: mude os quadrados, guarde de novo e veja o que mudou na chance e "
            "no custo. Dá para voltar a qualquer versão antes de salvar. Ficam gravadas só neste computador e, "
            "depois do resultado, 'Meus bilhetes' mostra se as suas mudanças ajudaram."
        )
        if st.button("Guardar esta versão", disabled=analise is None,
                     help=None if analise else "Marque todos os jogos para guardar uma versão."):
            try:
                guardada = guardar_versao(conexao, numero_vigente, marcacoes_atuais, percentuais_atuais, analise)
                conexao.commit()
                numero_da_versao = guardada["versao"]["numero_versao"]
                if guardada["nova"]:
                    st.success(f"Versão {numero_da_versao} guardada.")
                else:
                    st.info(f"Esta marcação já está guardada como versão {numero_da_versao}; nada foi repetido.")
            except LimiteDeVersoes as erro:
                st.warning(f"{erro} Salve um bilhete ou siga comparando as já guardadas.")

        versoes = listar_versoes(conexao, numero_vigente)
        if not versoes:
            st.caption("Nenhuma versão guardada para este concurso ainda.")
        else:
            n_jogos = len(jogos_vigente)
            linhas_versoes = []
            for v in versoes:
                chance_todos = formatar_uma_em(v["chance_todos"]) if v["chance_todos"] is not None else "-"
                chance_quase = (formatar_uma_em(v["chance_todos_menos_um"])
                                if v["chance_todos_menos_um"] is not None else "-")
                esperados = f"{v['acertos_esperados']:.1f}".replace(".", ",") if v["acertos_esperados"] is not None else "-"
                linhas_versoes.append([
                    f"{v['numero_versao']}", v["criado_em"][11:16],
                    f"{v['apostas']} ({reais(v['custo'])})", chance_todos, chance_quase, esperados,
                    f"{v['resumo'].get('duplos', 0)} / {v['resumo'].get('triplos', 0)}",
                    str(v["resumo"].get("zebras", "-")),
                    f"sim (nº {v['bilhete_id']})" if v["bilhete_id"] else "não",
                ])
            st.markdown(
                renderizar_tabela(
                    "Comparação das versões",
                    ["Versão", "Hora", "Apostas (custo)", f"Chance de {n_jogos} (pelos percentuais)",
                     f"Chance de {n_jogos - 1} ou mais (pelos percentuais)",
                     "Acertos esperados", "Duplos / triplos", "Zebras", "Virou bilhete"],
                    linhas_versoes,
                ),
                unsafe_allow_html=True,
            )
            st.caption(
                "As chances da tabela são as calculadas pelos percentuais do app e costumam ser otimistas: nos concursos "
                "passados, bilhetes de mesmo custo fizeram 13 ou mais bem menos vezes do que elas previam. Use a tabela "
                "para comparar versões entre si, não como expectativa. O número concreto aparece na 'Análise do seu palpite'."
            )
            for anterior, atual in zip(versoes, versoes[1:]):
                mudancas = diferencas(anterior["marcacoes"], atual["marcacoes"], num_jogo_por_id)
                st.markdown(
                    f"- **Versão {atual['numero_versao']}** em relação à {anterior['numero_versao']}: "
                    + ("; ".join(frase_da_mudanca(m) for m in mudancas) or "sem mudança")
                )
            ultima = versoes[-1]
            if not volante["jogos_sem_marcacao"]:
                agora = diferencas(ultima["marcacoes"], marcacoes_atuais, num_jogo_por_id)
                if agora:
                    st.info(
                        f"O volante agora difere da versão {ultima['numero_versao']} em {len(agora)} jogo(s): "
                        + "; ".join(frase_da_mudanca(m) for m in agora) + ". Guarde para comparar."
                    )
                else:
                    st.caption(f"O volante está igual à versão {ultima['numero_versao']}.")

            def _voltar_para_versao():
                escolhida = next(v for v in versoes if v["numero_versao"] == st.session_state[f"versao_escolhida_{numero_vigente}"])
                for jogo in jogos_vigente:
                    colunas = escolhida["marcacoes"].get(jogo["id"], [])
                    for coluna in COLUNAS_VOLANTE:
                        st.session_state[_chave(jogo["id"], coluna)] = coluna in colunas

            with st.container(horizontal=True, vertical_alignment="bottom"):
                numero_escolhido = st.selectbox("Versão", [v["numero_versao"] for v in versoes], index=len(versoes) - 1,
                                                key=f"versao_escolhida_{numero_vigente}", width=140)
                st.button("Voltar a esta versão", on_click=_voltar_para_versao,
                          help="Recoloca as marcações da versão no volante; depois é só salvar ou continuar mudando.")
            # Prévia da versão escolhida como volante de leitura (08/10/2026), com o percentual de quando foi guardada.
            escolhida = next(v for v in versoes if v["numero_versao"] == numero_escolhido)
            st.caption(f"Versão {numero_escolhido} no volante:")
            st.markdown(renderizar_volante([
                {"num_jogo": j["num_jogo"], "casa": j["casa"], "fora": j["fora"],
                 "marcacoes": escolhida["marcacoes"].get(j["id"], []), "pct": escolhida["percentuais"].get(j["id"])}
                for j in jogos_vigente
            ], f"Versão {numero_escolhido}"), unsafe_allow_html=True)

    # Salvamento único (volante e alternativas usam o mesmo caminho: análise, retrato imutável e, no volante, a versão).
    def _analise_de(lista: list[list[str]]) -> dict:
        return analisar_palpite(
            [
                {
                    "jogo_id": j["id"], "num_jogo": j["num_jogo"], "casa": j["casa"], "fora": j["fora"],
                    "pct": dados_por_jogo[j["id"]]["pct"], "marcacoes": marcadas,
                    "sem_base_propria": sem_base_por_jogo[j["id"]],
                }
                for j, marcadas in zip(jogos_vigente, lista)
            ]
        )

    def _gravar_bilhete(lista: list[list[str]], origem: str, base: dict | None) -> tuple[int, str]:
        marcacoes = {j["id"]: m for j, m in zip(jogos_vigente, lista)}
        percentuais_por_jogo = {j["id"]: dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente}
        # Motivo anotado vale para a marcação que o usuário fez: numa alternativa, só nos jogos que não mudaram.
        motivos = {j["id"]: st.session_state.get(f"motivo_{numero_vigente}_{j['id']}", []) for j in jogos_vigente
                   if base is None or base.get(j["id"]) == marcacoes[j["id"]]}
        analise_do_bilhete = _analise_de(lista)
        # A análise é guardada mesmo se não foi aberta: o aprendizado precisa
        # de todos os bilhetes, não só dos que foram analisados.
        bilhete_id = salvar_bilhete(conexao, numero_vigente, marcacoes, percentuais_por_jogo, analise=analise_do_bilhete,
                                    motivos=motivos, origem=origem, marcacoes_base=base)
        # Retrato imutável do que estava na tela (item A1 do plano v2): a revisão pós-jogo e a
        # comparação de modelos leem daqui, não do cálculo de hoje.
        ano_por_jogo = {r["num_jogo"]: r for r in resumo_ano_concurso}
        gravar_retrato(conexao, bilhete_id, retrato_geral(), {
            j["id"]: retrato_do_jogo(
                dict(j), calculos[j["id"]], ajustes, cobertura_por_jogo[j["id"]],
                complexidade_por_jogo.get(j["num_jogo"]),
                frase_do_lado(ano_por_jogo[j["num_jogo"]]["casa"]) if j["num_jogo"] in ano_por_jogo else None,
                frase_do_lado(ano_por_jogo[j["num_jogo"]]["fora"]) if j["num_jogo"] in ano_por_jogo else None,
                proposta["marcacoes"][i], marcacoes[j["id"]],
            )
            for i, j in enumerate(jogos_vigente)
        })
        # Bilhete do volante fica ligado a uma versão (a igual já guardada, ou uma nova), para o aprendizado
        # comparar a primeira tentativa com a que virou bilhete. A alternativa guarda o volante de onde saiu.
        aviso_versao = ""
        if origem == ORIGEM_VOLANTE:
            try:
                guardada = guardar_versao(conexao, numero_vigente, marcacoes, percentuais_por_jogo, analise_do_bilhete)
                ligar_ao_bilhete(conexao, guardada["versao"]["id"], bilhete_id)
                aviso_versao = f" Ligado à versão {guardada['versao']['numero_versao']}."
            except LimiteDeVersoes:
                aviso_versao = " (Limite de versões do concurso atingido: o bilhete foi salvo sem versão ligada.)"
        conexao.commit()
        return bilhete_id, aviso_versao

    def _chave_pendente(chave: str) -> str:
        return f"bilhete_igual_{numero_vigente}_{chave}"

    def _pedir_ou_salvar(chave: str, lista: list[list[str]], origem: str, base: dict | None, forcar: bool = False) -> None:
        """Bilhete igual a um já salvo no concurso: avisa e só grava se o usuário confirmar (decisão de 08/10/2026)."""
        marcacoes = {j["id"]: m for j, m in zip(jogos_vigente, lista)}
        igual = None if forcar else bilhete_igual(conexao, numero_vigente, marcacoes)
        if igual:
            st.session_state[_chave_pendente(chave)] = (igual, json.dumps(lista))
            return
        bilhete_id, aviso_versao = _gravar_bilhete(lista, origem, base)
        apostas = 1
        for colunas in lista:
            apostas *= len(colunas)
        de_onde = "" if origem == ORIGEM_VOLANTE else f" a partir da alternativa “{nome_da_origem(origem)}”"
        st.success(
            f"Bilhete salvo (nº {bilhete_id}){de_onde} -- {apostas} apostas, {reais(apostas * PRECO_APOSTA)}."
            f"{aviso_versao} Veja e confira depois em 'Meus bilhetes'. Fica só neste computador."
        )

    def _confirmacao(chave: str, lista: list[list[str]], origem: str, base: dict | None) -> None:
        pendente = st.session_state.get(_chave_pendente(chave))
        if not pendente:
            return
        igual, marcacao_pendente = pendente
        if marcacao_pendente != json.dumps(lista):  # o volante mudou depois do aviso: o aviso não vale mais
            st.session_state.pop(_chave_pendente(chave), None)
            return
        st.warning(
            f"Já existe o bilhete nº {igual} com estas mesmas marcações neste concurso. Se apostar os dois, o gasto "
            "dobra e as apostas se repetem. Quer salvar outro igual mesmo assim?"
        )
        with st.container(horizontal=True):
            confirmar = st.button("Salvar mesmo assim", key=f"confirmar_{numero_vigente}_{chave}")
            st.button("Cancelar", key=f"cancelar_{numero_vigente}_{chave}",
                      on_click=lambda: st.session_state.pop(_chave_pendente(chave), None))
        if confirmar:
            st.session_state.pop(_chave_pendente(chave), None)
            _pedir_ou_salvar(chave, lista, origem, base, forcar=True)

    # Bilhetes alternativos a partir do volante (pedido do usuário, 08/10/2026).
    with st.container(border=True):
        st.markdown("#### Bilhetes alternativos a partir do seu")
        st.caption(
            "Até três bilhetes montados a partir do que está no volante: ajuste leve e reorganizado (mesmo custo) e "
            "econômico (custo menor). Nenhum aumenta o custo nem o número de duplos e triplos que você escolheu. Para "
            "partir de uma versão guardada, use 'Voltar a esta versão' antes."
        )
        if not volante["pode_salvar"]:
            st.info("Aparece quando o volante estiver pronto para salvar: " + " ".join(volante["problemas"]))
        else:
            def _levar_ao_volante(lista: list[list[str]]) -> None:
                for jogo, colunas in zip(jogos_vigente, lista):
                    for coluna in COLUNAS_VOLANTE:
                        st.session_state[_chave(jogo["id"], coluna)] = coluna in colunas

            mostrar_variantes(
                conexao, numero_vigente, [dados_por_jogo[j["id"]]["pct"] for j in jogos_vigente], marcacoes_lista,
                [j["num_jogo"] for j in jogos_vigente], _levar_ao_volante,
                ao_salvar=lambda v: _pedir_ou_salvar(v["tipo"], v["marcacoes"], v["tipo"], marcacoes_atuais),
                ao_confirmar=lambda v: _confirmacao(v["tipo"], v["marcacoes"], v["tipo"], marcacoes_atuais),
            )

    with st.expander(f"Ver detalhes dos jogos (desempenho em {ano_atual}, classificação na CBF e zona)"):
        for j in jogos_vigente:
            dado = dados_por_jogo[j["id"]]
            pct, historico = dado["pct"], dado["historico"]
            forma_casa = resumo_curto(desempenho_no_ano(conexao, j["casa_id"], ano_atual))
            forma_fora = resumo_curto(desempenho_no_ano(conexao, j["fora_id"], ano_atual))
            cbf_casa = classificacao_do_participante(conexao, j["casa_id"])
            cbf_fora = classificacao_do_participante(conexao, j["fora_id"])
            selo_casa = (selo_da_posicao(cbf_casa["serie"], cbf_casa["ano"], cbf_casa["posicao"], cbf_casa.get("fase"))
                         if cbf_casa else None)
            selo_fora = (selo_da_posicao(cbf_fora["serie"], cbf_fora["ano"], cbf_fora["posicao"], cbf_fora.get("fase"))
                         if cbf_fora else None)
            extra_casa = (f" · {resumo_curto_cbf(cbf_casa)}" if cbf_casa else "") + (f" · zona: {selo_casa}" if selo_casa else "")
            extra_fora = (f" · {resumo_curto_cbf(cbf_fora)}" if cbf_fora else "") + (f" · zona: {selo_fora}" if selo_fora else "")
            st.markdown(
                f"**{j['num_jogo']}. {j['casa']}** ({_texto_percentual(pct['1'], historico['1'])} · {forma_casa}{extra_casa}) "
                f"x **{j['fora']}** ({_texto_percentual(pct['2'], historico['2'])} · {forma_fora}{extra_fora}) — "
                f"empate {_texto_percentual(pct['X'], historico['X'])}"
            )

    if st.button("Salvar bilhete"):
        if not volante["pode_salvar"]:
            for problema in volante["problemas"]:
                st.error(problema)
        else:
            _pedir_ou_salvar(ORIGEM_VOLANTE, marcacoes_lista, ORIGEM_VOLANTE, None)
    if volante["pode_salvar"]:
        _confirmacao(ORIGEM_VOLANTE, marcacoes_lista, ORIGEM_VOLANTE, None)

    # Bilhetes salvos do concurso (pedido do usuário, 08/10/2026): cada um como volante de leitura, com as marcações
    # e o percentual do dia em que foi salvo. O volante de cima continua abrindo em branco (decisão do usuário).
    salvos = listar_bilhetes(conexao, numero_vigente)
    with st.container(border=True):
        st.markdown("#### Bilhetes salvos para este concurso")
        if not salvos:
            st.caption("Nenhum bilhete salvo para este concurso ainda. Depois de salvar, ele aparece aqui com as marcações.")
        else:
            st.caption(
                f"{len(salvos)} bilhete(s); se apostar todos, o gasto soma {reais(sum(b['custo'] for b in salvos))}. "
                "Use 'Levar ao volante' para partir de um deles; a chance do conjunto está em 'Meus bilhetes'."
            )

            def _levar_bilhete(marcacoes_por_jogo: dict) -> None:
                for jogo in jogos_vigente:
                    colunas = marcacoes_por_jogo.get(jogo["id"], [])
                    for coluna in COLUNAS_VOLANTE:
                        st.session_state[_chave(jogo["id"], coluna)] = coluna in colunas

            for salvo in salvos:
                linhas_salvo = jogos_do_bilhete(conexao, salvo["id"])
                titulo_salvo = (f"Bilhete nº {salvo['id']} · {nome_da_origem(salvo.get('origem'))} · "
                                f"{salvo['apostas']} apostas · {reais(salvo['custo'])} · "
                                + ("apostado" if salvo["jogado_em"] else "rascunho"))
                with st.expander(titulo_salvo):
                    st.markdown(renderizar_volante(jogos_para_o_volante(linhas_salvo), f"Bilhete nº {salvo['id']}"),
                                unsafe_allow_html=True)
                    st.button("Levar ao volante", key=f"bilhete_levar_{salvo['id']}", on_click=_levar_bilhete,
                              args=({linha["jogo_id"]: linha["marcacoes"] for linha in linhas_salvo},),
                              help="Põe as marcações deste bilhete no volante, acima, para mexer e salvar outro.")
    st.caption(
        "Percentuais com o ajuste da última varredura de notícias (o valor entre parênteses mostra o efeito em pontos)."
        if ajustes
        else "Sem varredura de notícias para este concurso: os percentuais são só o histórico."
    )

conexao.close()

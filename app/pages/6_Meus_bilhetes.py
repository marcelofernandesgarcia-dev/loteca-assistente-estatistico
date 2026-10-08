"""Bilhetes salvos, conferência e controle de gasto x prêmio (etapa A3).
Dado fica só neste computador; nenhum dado pessoal é gravado, só a marcação
e o valor que você mesmo informar."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from chances_ui import mostrar_chances_do_bilhete, mostrar_conjunto, percentuais_atuais_do_concurso, reais, rotulo_do_bilhete
from retrato_ui import mostrar_retrato
from revisao_ui import mostrar_revisao
from util import formatar_data_br, mostrar_aviso_responsabilidade, obter_conexao

import config
from stats.analise_palpite import (
    NAO_BASTOU,
    NAO_FEZ_DIFERENCA,
    NOME_CATEGORIA,
    SALVOU,
    agregar_historico,
    avaliar_depois_do_resultado,
)
from stats.bilhetes_salvos import (
    conferir_bilhete,
    jogos_conferidos_para_historico,
    jogos_do_bilhete,
    listar_bilhetes,
    marcar_jogado,
    pode_conferir,
    registrar_premio,
    resumo_financeiro,
)
from stats.anti_manada import carregar_concursos
from stats.painel_bilhetes import DIMENSOES, jogos_conferidos
from stats.painel_bilhetes import painel as painel_por_tipo
from stats.frequencia import frequencia_global
from stats.premiacao import reais
from stats.retrato import retrato_do_bilhete
from stats.variantes_bilhete import (
    ORIGEM_VOLANTE,
    comparar_com_a_base,
    ler_marcacoes_base,
    leituras_das_variantes,
    nome_da_origem,
)
from stats.versoes_palpite import (
    agregar_aprendizado,
    aprendizado_de_todos_os_concursos,
    diferencas,
    frase_da_mudanca,
    historia_do_bilhete,
    listar_versoes,
    resultados_do_concurso,
)

NOME_RESULTADO = {"V": "Vitória", "E": "Empate", "D": "Derrota"}


def _decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def _taxa_ou_espera(registro: dict, minimo: int) -> str:
    if registro["taxa"] is not None:
        return f"{registro['taxa']:.0f}%"
    return f"aguardando amostra ({registro['marcacoes']} de {minimo})"


def mostrar_historico(historico: dict) -> None:
    """Só apresentação: as contas estão em stats/analise_palpite.py."""
    st.subheader("Meu histórico de palpites")
    if historico["bilhetes"] == 0:
        st.info("Aparece depois do primeiro bilhete conferido. Cada bilhete salvo guarda a análise do palpite.")
        return
    minimo = historico["amostra_minima"]
    st.caption(
        f"{historico['bilhetes']} bilhete(s) conferido(s). Uma taxa de acerto só aparece com pelo menos {minimo} "
        "marcações, para não tirar conclusão de poucos jogos. Isto mede os seus palpites e o app; não muda o modelo."
    )
    c1, c2 = st.columns(2)
    c1.metric("Seus acertos por bilhete (média)", _decimal(historico["acertos_medios"]))
    c2.metric("O que o app esperava (média)", _decimal(historico["acertos_esperados_medios"]))

    linhas = ["| Tipo de marcação | Marcações | Acertos | Taxa |", "|---|---|---|---|"]
    for categoria, registro in historico["por_categoria"].items():
        if registro["marcacoes"]:
            linhas.append(
                f"| {NOME_CATEGORIA[categoria]} | {registro['marcacoes']} | {registro['acertos']} "
                f"| {_taxa_ou_espera(registro, minimo)} |"
            )
    st.markdown("\n".join(linhas))

    if historico["por_motivo"]:
        linhas = ["| Motivo anotado | Marcações | Acertos | Taxa |", "|---|---|---|---|"]
        for motivo, registro in sorted(historico["por_motivo"].items()):
            linhas.append(f"| {motivo} | {registro['marcacoes']} | {registro['acertos']} | {_taxa_ou_espera(registro, minimo)} |")
        st.markdown("\n".join(linhas))

    divergencias = historico["divergencias"]
    if divergencias["jogos"]:
        texto = (
            f"Nos {divergencias['jogos']} jogos em que você marcou diferente da sugestão do app, você acertou "
            f"{divergencias['voce_acertou']} e a sugestão teria acertado {divergencias['app_acertou']}."
        )
        if divergencias["taxa_voce"] is not None:
            texto += f" Taxas: você {divergencias['taxa_voce']:.0f}%, app {divergencias['taxa_app']:.0f}%."
        st.markdown(texto)
    multiplos = historico["multiplos"]
    if sum(multiplos.values()):
        st.markdown(
            f"Duplos e triplos: {multiplos[SALVOU]} salvaram o jogo, {multiplos[NAO_FEZ_DIFERENCA]} não fizeram "
            f"diferença e {multiplos[NAO_BASTOU]} não bastaram."
        )


def mostrar_aprendizado_do_bilhete(jogos: list[dict]) -> None:
    """O que este bilhete conferido ensina (análise depois do resultado)."""
    avaliacao = avaliar_depois_do_resultado(jogos)
    st.markdown("**O que este bilhete ensina**")
    itens = [
        f"Pelos percentuais do momento, o app esperava cerca de {_decimal(avaliacao['acertos_esperados'])} "
        f"acertos; você fez {avaliacao['acertos']}."
    ]
    for categoria, registro in avaliacao["por_categoria"].items():
        if registro["marcacoes"]:
            itens.append(f"{NOME_CATEGORIA[categoria]}: {registro['acertos']} de {registro['marcacoes']}.")
    multiplos = avaliacao["multiplos"]
    if sum(multiplos.values()):
        itens.append(
            f"Duplos e triplos: {multiplos[SALVOU]} salvaram o jogo, {multiplos[NAO_FEZ_DIFERENCA]} não fizeram "
            f"diferença e {multiplos[NAO_BASTOU]} não bastaram."
        )
    for zebra in avaliacao["zebras_que_aconteceram"]:
        itens.append(f"Zebra no jogo {zebra['num_jogo']}: {'você marcou' if zebra['marcou'] else 'você não marcou'}.")
    st.markdown("\n".join(f"- {item}" for item in itens))

def mostrar_aprendizado_das_versoes(leituras: list[dict]) -> None:
    """Somatório de todos os concursos: as mudanças entre a primeira versão e a que
    virou bilhete ajudaram ou atrapalharam? Só as contas; nada de conclusão cedo."""
    st.subheader("Minhas versões: as mudanças ajudaram?")
    if not leituras:
        st.info(
            "Aparece quando um concurso tiver mais de uma versão guardada e o resultado sair. Compara a sua "
            "primeira versão com a que virou bilhete."
        )
        return
    agregado = agregar_aprendizado(leituras)
    st.markdown(
        f"Em {agregado['concursos']} concurso(s), as mudanças da primeira versão para a que virou bilhete "
        f"**ajudaram em {agregado['ajudaram']}**, **atrapalharam em {agregado['atrapalharam']}** e não mudaram o "
        f"número de acertos em {agregado['iguais']} (saldo: {agregado['saldo_total']:+d} acerto(s))."
    )
    if not agregado["amostra_suficiente"]:
        st.caption(
            f"Ainda são poucos concursos (menos de {config.VERSOES_CONCURSOS_MINIMOS}): não dá para dizer se "
            "mudar costuma ajudar. O número fica aqui para acompanhar."
        )


def mostrar_aprendizado_das_alternativas(leituras: list[dict]) -> None:
    """Bilhetes salvos a partir de uma alternativa: acertaram mais ou menos que o volante de onde saíram?"""
    st.subheader("Minhas alternativas: acertaram mais que o volante?")
    if not leituras:
        st.info(
            "Aparece quando um bilhete salvo a partir de uma alternativa (em 'Concurso atual') tiver o resultado. "
            "Compara a alternativa com o volante de onde ela saiu."
        )
        return
    agregado = agregar_aprendizado(leituras)
    st.markdown(
        f"Em {agregado['concursos']} bilhete(s) de alternativa, ela **acertou mais em {agregado['ajudaram']}**, "
        f"**menos em {agregado['atrapalharam']}** e o mesmo em {agregado['iguais']} (saldo: "
        f"{agregado['saldo_total']:+d} acerto(s))."
    )
    if not agregado["amostra_suficiente"]:
        st.caption(
            f"Ainda são poucos bilhetes (menos de {config.VERSOES_CONCURSOS_MINIMOS}): não dá para dizer se as "
            "alternativas costumam ajudar. O número fica aqui para acompanhar."
        )


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
c2.metric("Total gasto", reais(resumo["gasto_total"]))
c3.metric("Total em prêmios (informado por você)", reais(resumo["premio_total"]))
c4.metric("Saldo", reais(resumo["saldo"]), delta=None)
st.caption(
    "O prêmio só entra aqui se você informar (abaixo, em cada bilhete apurado) -- o app não consulta a CAIXA "
    "para saber se você ganhou. "
    f"Marcados como apostados de verdade: {resumo['jogados']} de {resumo['bilhetes']} bilhetes "
    f"({reais(resumo['gasto_jogado'])}); os demais são rascunhos. O total gasto soma todos os bilhetes salvos."
)

mostrar_historico(agregar_historico(jogos_conferidos_para_historico(conexao)))

# Painel por tipo de jogo (plano v2, item D5).
st.subheader("Acertos por tipo de jogo")
so_apostados = st.toggle("Só bilhetes apostados de verdade", key="painel_so_apostados")
jogos_painel = jogos_conferidos(conexao, so_apostados)
if not jogos_painel:
    st.info("Aparece depois do primeiro bilhete conferido" + (" e marcado como apostado." if so_apostados else "."))
else:
    dimensao = st.radio("Separar por", list(DIMENSOES), format_func=DIMENSOES.get, horizontal=True, key="painel_dimensao")
    st.markdown(
        "| Grupo | Marcações | Acertos | Taxa de acerto | Surpresa média do app |\n|---|---|---|---|---|\n"
        + "".join(
            f"| {g['grupo']} | {g['marcacoes']} | {g['acertos']} | {_taxa_ou_espera(g, config.ANALISE_AMOSTRA_MINIMA)} | {_decimal(g['surpresa_media'])} |\n"
            for g in painel_por_tipo(jogos_painel)[dimensao]
        )
    )
    st.caption(
        "Surpresa = −ln(chance que o app deu ao resultado), média dos jogos do grupo: quanto maior, mais o app foi "
        "surpreendido. Origem, cobertura e notícia só existem para bilhetes salvos a partir de 07/10/2026."
    )
mostrar_aprendizado_das_versoes(aprendizado_de_todos_os_concursos(conexao))
mostrar_aprendizado_das_alternativas(leituras_das_variantes(conexao))

_atuais_por_concurso: dict[int, tuple[list[dict], list[dict]]] = {}


def _atuais(numero_concurso: int) -> tuple[list[dict], list[dict]]:
    """Jogos e percentuais de hoje do concurso (calibrados, com notícias), calculados uma vez por execução da página."""
    if numero_concurso not in _atuais_por_concurso:
        _atuais_por_concurso[numero_concurso] = percentuais_atuais_do_concurso(conexao, numero_concurso)
    return _atuais_por_concurso[numero_concurso]


def _marcacoes_do_bilhete(bilhete_id: int, jogos: list[dict]) -> list[list[str]] | None:
    """Marcações do bilhete na ordem dos jogos do concurso; None se o bilhete não cobre todos os jogos."""
    por_jogo = {j["jogo_id"]: j["marcacoes"] for j in jogos_do_bilhete(conexao, bilhete_id)}
    if any(j["id"] not in por_jogo for j in jogos):
        return None
    return [por_jogo[j["id"]] for j in jogos]


_cache_revisao: dict[str, object] = {}


def _concursos_para_diagnostico() -> list[dict]:
    if "concursos" not in _cache_revisao:
        _cache_revisao["concursos"] = carregar_concursos(conexao)[0]
    return _cache_revisao["concursos"]


def _referencia() -> dict | None:
    if "referencia" not in _cache_revisao:
        freq = frequencia_global(conexao)
        _cache_revisao["referencia"] = {c: 100.0 * freq[c] for c in ("1", "X", "2")} if freq.get("total_jogos") else None
    return _cache_revisao["referencia"]


def _concurso_aberto(numero_concurso: int) -> bool:
    """Concurso com jogos ainda sem resultado: dá para decidir em que apostar."""
    sem_resultado, total = conexao.execute(
        "SELECT SUM(resultado IS NULL), COUNT(*) FROM jogos WHERE concurso_numero = ?", (numero_concurso,)
    ).fetchone()
    return bool(total) and bool(sem_resultado)


st.subheader("Conjunto de bilhetes do concurso")
concursos_abertos = sorted({b["concurso_numero"] for b in bilhetes if _concurso_aberto(b["concurso_numero"])}, reverse=True)
if not concursos_abertos:
    st.info(
        "Aparece quando houver bilhetes salvos de um concurso ainda não apurado. Escolha quais bilhetes pretende jogar e veja a "
        "chance do conjunto, quanto cada um acrescenta e quanto das apostas se repete."
    )
else:
    st.caption(
        "Escolha os bilhetes que pretende jogar no concurso. Os bilhetes disputam os mesmos jogos, então as chances não se somam: "
        "o app calcula o conjunto com os percentuais de hoje, já corrigidos pela calibração."
    )
    numero_conjunto = st.selectbox("Concurso", concursos_abertos, key="conjunto_concurso")
    do_concurso = [b for b in bilhetes if b["concurso_numero"] == numero_conjunto]
    escolhidos = st.multiselect(
        "Bilhetes que pretendo jogar", options=[b["id"] for b in do_concurso][:12],
        default=[b["id"] for b in do_concurso][:12], key=f"conjunto_bilhetes_{numero_conjunto}",
        format_func=lambda i: rotulo_do_bilhete(next(b for b in do_concurso if b["id"] == i)),
    )
    if len(do_concurso) > 12:
        st.caption("O conjunto aceita até 12 bilhetes por vez; os 12 mais recentes estão disponíveis.")
    if escolhidos:
        jogos_atuais, pcts_atuais = _atuais(numero_conjunto)
        montados, incompletos = [], []
        for b in do_concurso:
            if b["id"] in escolhidos:
                marcas = _marcacoes_do_bilhete(b["id"], jogos_atuais)
                (montados if marcas else incompletos).append({**b, "marcacoes": marcas} if marcas else b)
        if incompletos:
            st.warning("Estes bilhetes não cobrem todos os jogos do concurso e ficaram de fora: " + ", ".join(str(b["id"]) for b in incompletos) + ".")
        if montados:
            mostrar_conjunto(jogos_atuais, pcts_atuais, montados)
    else:
        st.info("Marque pelo menos um bilhete para ver as chances do conjunto.")

st.subheader("Bilhetes")

for bilhete in bilhetes:
    linhas_bilhete = conexao.execute(
        "SELECT j.resultado FROM bilhete_jogos bj JOIN jogos j ON j.id = bj.jogo_id WHERE bj.bilhete_id = ?",
        (bilhete["id"],),
    ).fetchall()
    total_jogos_bilhete = len(linhas_bilhete)
    jogos_apurados_antes = pode_conferir(linhas_bilhete)
    titulo = f"Concurso {bilhete['concurso_numero']} · salvo em {formatar_data_br(bilhete['criado_em'][:10])} · {bilhete['apostas']} apostas · {reais(bilhete['custo'])}"
    alternativa = bilhete.get("origem") not in (None, ORIGEM_VOLANTE)
    if alternativa:
        titulo += f" · alternativa: {nome_da_origem(bilhete['origem'])}"
    titulo += " · apostado" if bilhete["jogado_em"] else " · rascunho"
    if bilhete["conferido_em"] is not None:
        titulo += f" · {bilhete['acertos']}/{total_jogos_bilhete} acertos"
    with st.expander(titulo):
        num_jogo = {
            linha["id"]: linha["num_jogo"]
            for linha in conexao.execute("SELECT id, num_jogo FROM jogos WHERE concurso_numero = ?", (bilhete["concurso_numero"],))
        }
        base = ler_marcacoes_base(bilhete.get("marcacoes_base")) if alternativa else None
        if base:
            marcadas = {j["jogo_id"]: j["marcacoes"] for j in jogos_do_bilhete(conexao, bilhete["id"])}
            mudancas = diferencas(base, marcadas, num_jogo)
            texto = (f"Salvo a partir da alternativa “{nome_da_origem(bilhete['origem'])}” do seu volante. Do volante para "
                     "esta: " + ("; ".join(frase_da_mudanca(m) for m in mudancas) or "sem mudança") + ".")
            leitura = comparar_com_a_base(base, marcadas, resultados_do_concurso(conexao, bilhete["concurso_numero"]))
            if leitura:
                texto += (f" Com o resultado, o volante de partida teria feito {leitura['acertos_base']} acerto(s) e esta "
                          f"alternativa fez {leitura['acertos_variante']}.")
            st.caption(texto)
        historia = historia_do_bilhete(
            listar_versoes(conexao, bilhete["concurso_numero"]), bilhete["id"],
            resultados_do_concurso(conexao, bilhete["concurso_numero"]), num_jogo,
        )
        if historia:
            texto = f"Montado na versão {historia['numero']} de {historia['versoes']} guardada(s) para este concurso."
            if historia["mudancas"]:
                texto += " Da versão 1 para esta: " + "; ".join(frase_da_mudanca(m) for m in historia["mudancas"]) + "."
            if historia["acertos_primeira"] is not None and historia["acertos_bilhete"] is not None:
                texto += (
                    f" Com o resultado, a versão 1 teria feito {historia['acertos_primeira']} acerto(s) e esta fez "
                    f"{historia['acertos_bilhete']}."
                )
            st.caption(texto)
        # "Jogado de verdade" (plano v2, item D1): separa rascunho de aposta real sem importar o comprovante.
        jogado = st.checkbox(
            "Apostei este bilhete na lotérica", value=bilhete["jogado_em"] is not None, key=f"jogado_{bilhete['id']}",
            help="Só a marcação é guardada. O comprovante da CAIXA não é importado: ele tem dados pessoais.",
        )
        if jogado != (bilhete["jogado_em"] is not None):
            marcar_jogado(conexao, bilhete["id"], jogado)
            conexao.commit()
            st.rerun()
        mostrar_retrato(retrato_do_bilhete(conexao, bilhete["id"]), f"retrato_{bilhete['id']}")
        if bilhete["conferido_em"] is None and _concurso_aberto(bilhete["concurso_numero"]):
            jogos_atuais, pcts_atuais = _atuais(bilhete["concurso_numero"])
            marcas_atuais = _marcacoes_do_bilhete(bilhete["id"], jogos_atuais)
            if marcas_atuais:
                st.caption("Chances calculadas com os percentuais de hoje (corrigidos pela calibração), não com os do dia em que você salvou.")
                mostrar_chances_do_bilhete(jogos_atuais, pcts_atuais, marcas_atuais)
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
            if all(j["percentual_1"] is not None for j in resultado["jogos"]):
                mostrar_aprendizado_do_bilhete(
                    [
                        {
                            "num_jogo": j["num_jogo"], "marcacoes": j["marcacoes"], "resultado": j["resultado"],
                            "categoria": j["categoria"],
                            "pct": {"1": j["percentual_1"], "X": j["percentual_x"], "2": j["percentual_2"]},
                        }
                        for j in resultado["jogos"]
                    ]
                )
            mostrar_revisao(conexao, bilhete, resultado["jogos"], retrato_do_bilhete(conexao, bilhete["id"]),
                            _concursos_para_diagnostico(), _referencia())

            premio = st.number_input(
                "Prêmio recebido (R$, 0 se não ganhou)", min_value=0.0, step=0.01,
                value=float(bilhete["premio_informado"] or 0.0), key=f"premio_{bilhete['id']}",
            )
            if st.button("Salvar prêmio", key=f"salvar_premio_{bilhete['id']}"):
                registrar_premio(conexao, bilhete["id"], premio)
                conexao.commit()
                st.rerun()

conexao.close()

import datetime as dt

import streamlit as st
from ano_em_curso_ui import mostrar_ano_em_curso, resumo_do_ano
from util import mostrar_aviso_responsabilidade, obter_conexao

import config
import db
from stats.ano_em_curso import cobertura
from stats.concursos import concurso_a_jogar
from stats.painel import participantes_do_concurso
from stats.prazo import formatar_restante, situacao_do_prazo

NOMES_FONTE = {"caixa": "CAIXA (concursos e programação)", "cbf": "CBF (classificação e jogos)", "noticias": "Notícias (ajuste externo)"}
IDADE_ALERTA_HORAS = {"caixa": 24, "cbf": 7 * 24, "noticias": 8 * 24}

st.set_page_config(page_title="Loteca -- Assistente Estatístico", page_icon="⚽", layout="wide")

st.title("Loteca -- Assistente Estatístico")
st.write(
    "Ferramenta pessoal de análise estatística da Loteca, para fortalecer a "
    "análise e reduzir risco e erro na escolha -- não prevê nem garante "
    "resultado, é jogo de azar. Use as páginas na barra lateral: **Concurso "
    "atual**, **Por concurso**, **Por time** e **Fechamento de bolão**."
)
mostrar_aviso_responsabilidade()

conexao = obter_conexao()

# Ano em curso em primeiro lugar (pedido do usuário, 30/09/2026: "impacto visual importante").
ano_atual = dt.date.today().year
a_jogar = concurso_a_jogar(conexao)
st.header(f"Ano em curso ({ano_atual})")
if not a_jogar:
    st.info("Nenhum concurso a jogar no banco. Use 'Atualizar dados da CAIXA' na página 'Concurso atual'.")
else:
    jogos_do_concurso = participantes_do_concurso(conexao, a_jogar["numero"])
    resumo_ano = resumo_do_ano(conexao, jogos_do_concurso, ano_atual)
    cob = cobertura(resumo_ano)
    prazo = situacao_do_prazo(a_jogar["data_limite_aposta"], a_jogar["horario_fim_apostas"])
    with st.container(horizontal=True, wrap=True):
        st.metric("Concurso a jogar", a_jogar["numero"], border=True)
        st.metric(
            "Apostas", formatar_restante(prazo["restante"]) if prazo["limite"] else "prazo não informado",
            help="Tempo até o fim das apostas." + ("" if prazo["exato"] else " Prazo aproximado: horário não informado."),
            border=True,
        )
        st.metric(f"Participantes com dado de {ano_atual}", f"{cob['com_dado']} de {cob['total']}", border=True)
        st.metric("Com amostra pequena no ano", cob["amostra_pequena"],
                  help=f"Menos de {config.ANO_CURSO_AMOSTRA_PEQUENA} jogos no ano: leitura fraca.", border=True)
    mostrar_ano_em_curso(conexao, jogos_do_concurso, ano_atual, "inicio", resumo=resumo_ano)

st.subheader("Base de dados")
total_concursos = conexao.execute("SELECT COUNT(*) AS n FROM concursos").fetchone()["n"]
total_jogos = conexao.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
total_valorfinal = conexao.execute("SELECT COUNT(*) AS n FROM historico_valorfinal").fetchone()["n"]

col1, col2, col3 = st.columns(3)
col1.metric("Concursos importados (CAIXA)", total_concursos)
col2.metric("Jogos com time/placar", total_jogos)
col3.metric("Jogos no bootstrap (ValorFinal)", total_valorfinal)

if total_concursos == 0:
    st.info(
        "Ainda não foi importado nenhum concurso da CAIXA -- as páginas "
        "'Por time' e 'Concurso atual' vão ficar vazias até rodar a "
        "importação. Veja `README.md` para o comando."
    )

st.subheader("Status dos dados")
st.caption(
    "Última execução de cada fonte (`python scripts/atualizar_tudo.py`). Sem execução registrada, a fonte "
    "nunca rodou por este script -- pode ter sido atualizada por outro caminho (ex.: botão da página)."
)
execucoes = db.ultima_execucao_por_fonte(conexao)
for fonte, rotulo in NOMES_FONTE.items():
    execucao = execucoes.get(fonte)
    coluna_rotulo, coluna_status = st.columns([2, 3])
    coluna_rotulo.write(f"**{rotulo}**")
    if not execucao:
        coluna_status.caption("Nunca rodou por `atualizar_tudo.py`.")
        continue
    quando = dt.datetime.fromisoformat(execucao["concluido_em"])
    idade_horas = (dt.datetime.now() - quando).total_seconds() / 3600
    quando_texto = quando.strftime("%d/%m/%Y %H:%M")
    if not execucao["sucesso"]:
        coluna_status.error(f"Falhou em {quando_texto}: {execucao['erro'] or 'sem detalhe'}")
    elif idade_horas > IDADE_ALERTA_HORAS[fonte]:
        coluna_status.warning(f"OK em {quando_texto}, mas há {idade_horas / 24:.1f} dia(s) -- pode estar desatualizado.")
    else:
        quantidade_texto = f" · {execucao['quantidade']} registro(s)" if execucao["quantidade"] is not None else ""
        coluna_status.success(f"OK em {quando_texto}{quantidade_texto}.")

conexao.close()

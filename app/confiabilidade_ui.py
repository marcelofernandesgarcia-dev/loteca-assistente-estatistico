"""Topo da página 'Confiabilidade do modelo': o app de hoje (sugestão S1, 08/10/2026). As contas estão em
stats/confiabilidade.py; a medição é gravada pela atualização diária e aqui só é lida (ou refeita no botão)."""
import datetime as dt
import logging

import numpy as np
import streamlit as st
from util import obter_conexao

from stats import confiabilidade

logger = logging.getLogger(__name__)


def _n(valor: float, casas: int = 4) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _linha(nome: str, g: dict) -> str:
    return (f"| {nome} | {g['n']} | {_n(g['perda_log'])} | {_n(g['perda_log_frequencia'])} | {_n(g['ganho'], 3)} "
            f"({_n(g['ic_inferior'], 3)} a {_n(g['ic_superior'], 3)}) | {_n(g['rps'])} | {_n(g['acerto'], 1)}% |\n")


CABECALHO = ("| Grupo | Jogos | Perda log do app | Perda log da frequência | Ganho do app (IC 95%) | RPS do app | "
             "Acerto do favorito |\n|---|---|---|---|---|---|---|\n")


def mostrar_app_de_hoje(conexao) -> None:
    st.subheader("O app de hoje")
    st.caption(
        "Cada jogo apurado é previsto andando no tempo pela mesma regra que o app usa agora: temporada da CBF com o Elo "
        "de clubes nas Séries A e B, Elo das seleções, Elo de clubes nos demais jogos entre clubes e o modelo histórico "
        "calibrado no resto. Perda logarítmica: quanto menor, mais chance o app deu ao que aconteceu (é o critério de "
        "troca de modelo). RPS: mesma ideia, levando em conta a ordem 1-X-2."
    )
    if st.button("Medir agora (cerca de 2 minutos)"):
        conexao_medicao = obter_conexao()
        try:
            with st.spinner("Medindo o app de hoje..."):
                medicao = confiabilidade.medir(conexao_medicao)
                if medicao:
                    confiabilidade.gravar(conexao_medicao, medicao)
                    conexao_medicao.commit()
        except (ValueError, ArithmeticError, np.linalg.LinAlgError):
            logger.exception("Medição do app de hoje falhou")
            st.error("A medição não pôde ser concluída com os dados atuais. Tente de novo depois da próxima atualização.")
        finally:
            conexao_medicao.close()
    medicao = confiabilidade.ultima(conexao)
    if medicao is None:
        st.info("Ainda não há medição gravada. Ela é feita pela atualização diária, ou agora, pelo botão acima.")
        return
    total = medicao["total"]
    melhor = total["ic_inferior"] > 0
    pior = total["ic_superior"] < 0
    (st.success if melhor else st.error if pior else st.warning)(
        f"**Veredito:** o app de hoje é **{'melhor' if melhor else 'pior' if pior else 'igual'} que a frequência simples** "
        f"de 1/X/2, com 95% de confiança: perda logarítmica {_n(total['perda_log'])} contra {_n(total['perda_log_frequencia'])}, "
        f"em {total['n']} jogos de {medicao['desde_ano']} em diante. Acerto do favorito: {_n(total['acerto'], 1)}% contra "
        f"{_n(total['acerto_frequencia'], 1)}%."
    )
    st.markdown(CABECALHO + _linha("**Todos**", total)
                + "".join(_linha(tipo, g) for tipo, g in medicao["por_tipo"].items()))
    st.markdown("**Por ano**")
    st.markdown(CABECALHO.replace("Grupo", "Ano") + "".join(_linha(ano, g) for ano, g in medicao["por_ano"].items()))
    st.markdown("**Calibração do app de hoje** (quando o app diz, por exemplo, 60% a 70%, quanto acontece de fato)")
    st.markdown(
        "| Faixa prevista | Resultados | Previsto (média) | Observado (de fato) |\n|---|---|---|---|\n"
        + "".join(f"| {c['faixa']} | {c['n']} | {_n(c['previsto'], 1)}% | {_n(c['observado'], 1)}% |\n"
                  for c in medicao["calibracao"])
    )
    quando = dt.datetime.fromisoformat(medicao["calculado_em"]).strftime("%d/%m/%Y %H:%M")
    st.caption(f"Medido em {quando}, com os concursos apurados até o {medicao['ultimo_concurso']}. "
               "Refeito pela atualização diária quando entra concurso novo.")

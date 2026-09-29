"""Painel de confiabilidade (item B3 do roteiro, e Etapa V1/V2 do parecer
técnico de 28/09/2026): mede o percentual atual contra a própria base, sem
olhar o futuro (walk-forward), e compara com referências simples.

Sem `pandas` de propósito -- só HTML/markdown -- para a página funcionar
mesmo se o `pandas` estiver bloqueado (ver docs/resposta-ao-parecer-29-09-2026.md,
seção 4: Smart App Control do Windows bloqueando a DLL nativa do pandas)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from util import mostrar_aviso_responsabilidade, obter_conexao

from stats.backtest import executar_backtest

st.title("Confiabilidade do modelo")
mostrar_aviso_responsabilidade()
st.caption(
    "O percentual atual (card 2 de 'Concurso atual') acerta mais que a frequência histórica pura "
    "(47%/26%/27%)? Este painel mede, sem usar dado do futuro: cada concurso é avaliado só com os "
    "jogos de concursos anteriores a ele (walk-forward)."
)

conexao = obter_conexao()
with st.spinner("Calculando..."):
    resultado = executar_backtest(conexao)
conexao.close()

if resultado["jogos_avaliados"] == 0:
    st.info("Base pequena demais para avaliar (menos concursos do que o aquecimento mínimo).")
    st.stop()

st.write(
    f"**{resultado['jogos_avaliados']} jogos** avaliados, dos concursos **{resultado['primeiro_concurso']}** a "
    f"**{resultado['ultimo_concurso']}** ({resultado['concursos_avaliados']} concursos). Os primeiros "
    f"{resultado['aquecimento_concursos']} concursos servem só de aquecimento (o modelo precisa de histórico "
    "antes de ser avaliado) e não entram na conta."
)

atual, referencia = resultado["modelos"]["atual"], resultado["modelos"]["frequencia_global"]
veredito = resultado["comparacao_atual_vs_global"]["veredito"]
cor_veredito = {"melhor que a referência": "success", "pior que a referência": "error"}.get(veredito, "warning")
getattr(st, cor_veredito)(
    f"**Veredito:** o percentual atual (Poisson) é **{veredito}** da frequência histórica simples, "
    "com 95% de confiança (diferença medida na perda logarítmica -- quanto menor, melhor a probabilidade dada "
    "ao que de fato aconteceu)."
)

c1, c2, c3 = st.columns(3)
c1.metric("Acerto do favorito -- atual", f"{atual['acuracia']:.1f}%", delta=f"{atual['acuracia'] - referencia['acuracia']:+.1f} p.p. vs. frequência")
c2.metric("Brier (0 = perfeito) -- atual", f"{atual['brier']:.4f}", delta=f"{atual['brier'] - referencia['brier']:+.4f}", delta_color="inverse")
c3.metric("Perda log (menor é melhor) -- atual", f"{atual['perda_log']:.4f}", delta=f"{atual['perda_log'] - referencia['perda_log']:+.4f}", delta_color="inverse")
st.caption(
    f"Referência (frequência histórica simples): acerto {referencia['acuracia']:.1f}% · Brier {referencia['brier']:.4f} · "
    f"perda log {referencia['perda_log']:.4f}. \"Sempre mandante\" (chuta a coluna 1 em todo jogo): "
    f"{resultado['modelos']['sempre_mandante']['acuracia']:.1f}% de acerto."
)

st.subheader("Calibração")
st.caption(
    "Quando o modelo diz, por exemplo, \"60% a 70%\" de chance para um resultado, quanto esse resultado "
    "de fato acontece? Num modelo bem calibrado, a coluna \"previsto\" e a \"observado\" ficam próximas."
)
linhas_calibracao = "".join(
    f"| {c['faixa']} | {c['n']} | {c['previsto']:.1f}% | {c['observado']:.1f}% | "
    f"{'⚠️ excesso de confiança' if c['previsto'] - c['observado'] > 5 else ('falta de confiança' if c['observado'] - c['previsto'] > 5 else '-')} |\n"
    for c in resultado["calibracao_atual"]
)
st.markdown(
    "| Faixa prevista | Jogos | Previsto (média) | Observado (de fato) | Leitura |\n|---|---|---|---|---|\n" + linhas_calibracao
)

st.subheader("Se você tivesse seguido a sugestão do app em cada concurso passado")
bilhetes = resultado["bilhetes"]
if bilhetes["concursos"] == 0:
    st.caption("Nenhum concurso completo (14 jogos avaliáveis) na janela medida.")
else:
    st.caption(
        f"Média de acertos (de 14 jogos), em {bilhetes['concursos']} concursos completos avaliados, seguindo três "
        "estratégias simples: marcar sempre o mandante, marcar sempre o favorito do modelo atual (sem duplo/triplo), "
        "ou a sugestão real do app (favorito + 1 duplo/triplo no jogo mais incerto)."
    )
    media = bilhetes["media"]
    d1, d2, d3 = st.columns(3)
    d1.metric("Sempre mandante", f"{media['sempre_mandante']:.2f} / 14")
    d2.metric("Favorito do modelo", f"{media['favorito_do_modelo']:.2f} / 14")
    d3.metric("Sugestão do app", f"{media['com_cobertura']:.2f} / 14", help=f"Custo médio: R$ {bilhetes['custo_medio_com_cobertura']:.2f}")
    p10, p11 = bilhetes["pelo_menos_10"], bilhetes["pelo_menos_11"]
    st.write(
        f"Concursos com **10 ou mais acertos**: sempre mandante {p10['sempre_mandante']:.1f}%, favorito do modelo "
        f"{p10['favorito_do_modelo']:.1f}%, sugestão do app {p10['com_cobertura']:.1f}%. Com **11 ou mais**: "
        f"{p11['sempre_mandante']:.1f}%, {p11['favorito_do_modelo']:.1f}%, {p11['com_cobertura']:.1f}%."
    )

st.subheader("O que isso quer dizer")
if veredito == "pior que a referência":
    st.warning(
        "Hoje, o percentual calculado (Poisson sobre o histórico) **não supera** simplesmente usar a frequência "
        "histórica de 1/X/2 (47%/26%/27%) -- e é mais confiante do que deveria nas faixas altas (veja a calibração "
        "acima). Isso não muda o objetivo do app (organizar a análise), mas significa que os percentuais de hoje "
        "devem ser lidos como **estimativa exploratória**, não como vantagem estatística comprovada. Antes de "
        "adotar o modelo por competição (que usa os jogos completos da CBF) como padrão, ele precisa passar por "
        "esta mesma medição e superar esta referência."
    )
else:
    st.success("O percentual calculado supera a frequência histórica simples nesta medição.")
st.caption(
    "Metodologia: stats/backtest.py. Cada concurso usa só jogos de concursos anteriores (garantia testada em "
    "tests/test_backtest.py). Jogos decididos por sorteio são excluídos. Detalhes em "
    "docs/resposta-ao-parecer-29-09-2026.md."
)

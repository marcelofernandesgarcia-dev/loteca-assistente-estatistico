"""Executa a página 'Concurso atual' (Streamlit AppTest) sobre um banco SINTÉTICO:
percentual com o ajuste de notícias aplicado, motivo do ajuste e tratamento de
manchete vinda de fora."""
import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import config
import db

RAIZ = Path(__file__).resolve().parent.parent
PAGINA = RAIZ / "app" / "pages" / "1_Concurso_atual.py"


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    for pasta in (str(RAIZ), str(RAIZ / "app")):
        if pasta not in sys.path:
            sys.path.insert(0, pasta)
    db.inicializar_schema()
    with db.sessao() as c:
        alfa = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        beta = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero, data_apuracao, data_limite_aposta) VALUES (9001, '2026-03-05', '2026-03-01')")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta, horario_fim_apostas) VALUES (9002, '2099-01-01', 15)")
        historico = [(1, alfa, beta, 2, 0, "1"), (2, beta, alfa, 1, 1, "X"), (3, alfa, beta, 0, 1, "2")]
        for num, casa, fora, gc, gf, res in historico:
            c.execute(
                "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado, data_jogo)"
                " VALUES (9001, ?, ?, ?, ?, ?, ?, '2026-03-02')", (num, casa, fora, gc, gf, res),
            )
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9002, 1, ?, ?, '2099-01-02')", (alfa, beta))
        evidencias = [
            {"sinal": "lesao_titular", "manchete": "Zagueiro lesionado [clique](http://malicioso) _agora_", "fonte": "Veículo Teste", "url": "https://exemplo.test/materia-1"},
            {"sinal": "lesao_titular", "manchete": "Outra manchete", "fonte": "Outro", "url": "javascript:alert(1)"},
        ]
        c.execute(
            "INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em, resumo, ajuste_aplicado, evidencias)"
            " VALUES (?, 9002, '2026-09-24T10:00:00', 'lesao_titular (-4.0)', -4.0, ?)",
            (alfa, json.dumps(evidencias, ensure_ascii=False)),
        )
    return True


def _abrir() -> AppTest:
    at = AppTest.from_file(str(PAGINA), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _cartao_2(at: AppTest) -> str:
    return next(m.value for m in at.markdown if "2. Percentual -- concurso 9002" in m.value)


def test_card_2_mostra_o_percentual_final_com_o_efeito_das_noticias(banco):
    cartao = _cartao_2(_abrir())
    assert "(-" in cartao or "(+" in cartao  # diferença entre o final e o histórico
    assert "Percentual histórico" not in cartao


def test_pagina_informa_a_ultima_varredura(banco):
    at = _abrir()
    legendas = " ".join(c.value for c in at.caption)
    assert "Última varredura de notícias: 24/09/2026 10:00 · 1 de 1 participantes com ajuste." in legendas


def test_motivo_do_ajuste_traz_manchete_veiculo_e_link_seguro(banco):
    at = _abrir()
    expansor = next(e for e in at.expander if "Por que os percentuais foram ajustados" in e.label)
    texto = " ".join(m.value for m in expansor.markdown)
    assert "ALFA: -4.0 pontos" in texto and "Veículo Teste" in texto
    assert "lesao titular" in texto  # sublinhado vira espaço, não some
    assert "[abrir](https://exemplo.test/materia-1)" in texto
    assert "javascript:" not in texto  # link de esquema perigoso descartado
    assert "(http://malicioso)" not in texto and "[clique]" not in texto  # manchete não vira link
    assert "efeito líquido" in texto


def test_sem_varredura_mostra_so_o_historico_e_sem_expansor(banco):
    with db.sessao() as c:
        c.execute("DELETE FROM fatores_externos")
    at = _abrir()
    assert "Sem varredura de notícias para este concurso" in " ".join(c.value for c in at.caption)
    assert not [e for e in at.expander if "Por que os percentuais" in e.label]
    assert "(-" not in _cartao_2(at) and "(+" not in _cartao_2(at)


def test_noticias_de_contexto_aparecem_separadas_e_nao_mexem_no_percentual(banco):
    with db.sessao() as c:
        beta = c.execute("SELECT id FROM participantes WHERE nome = 'BETA'").fetchone()[0]
        evidencia = [{"sinal": "contratacao", "manchete": "Beta contrata meia", "fonte": "Veículo Teste",
                      "url": "https://exemplo.test/contratacao"}]
        c.execute(
            "INSERT INTO fatores_externos (participante_id, concurso_numero, coletado_em, resumo, ajuste_aplicado, evidencias)"
            " VALUES (?, 9002, '2026-09-24T10:00:00', 'contratacao (informativo)', 0.0, ?)",
            (beta, json.dumps(evidencia, ensure_ascii=False)),
        )
    at = _abrir()
    expansor = next(e for e in at.expander if e.label.startswith("Notícias de contexto"))
    texto = " ".join(m.value for m in expansor.markdown)
    assert "BETA** · Contratação: «Beta contrata meia»" in texto and "[abrir](https://exemplo.test/contratacao)" in texto
    assert "NÃO mexem no percentual" in " ".join(c.value for c in expansor.caption)


# --- Card 3: volante com 3 quadrados por jogo ---

def _quadrados(at: AppTest) -> list:
    return [c for c in at.checkbox if c.key and c.key.startswith("volante_9002_")]


def test_ano_em_curso_fica_visivel_antes_do_volante(banco):
    import datetime as dt

    at = _abrir()
    textos = [m.value for m in at.markdown]
    posicao_ano = next(i for i, t in enumerate(textos) if f"Ano em curso ({dt.date.today().year})" in t)
    posicao_volante = next(i for i, t in enumerate(textos) if "3. Seu palpite -- concurso 9002" in t)
    assert posicao_ano < posicao_volante
    assert any(f"Jogo a jogo em {dt.date.today().year}" in t for t in textos)


def test_volante_tem_3_quadrados_por_jogo_e_comeca_em_branco(banco):
    at = _abrir()
    quadrados = _quadrados(at)
    assert len(quadrados) == 3  # 1 jogo x (1, X, 2)
    assert [q.key.rsplit("_", 1)[1] for q in quadrados] == ["1", "X", "2"]
    assert not any(q.value for q in quadrados)
    assert any("0 de 1 jogos marcados" in i.value for i in at.info)


def test_preencher_com_a_sugestao_marca_os_quadrados(banco):
    at = _abrir()
    next(b for b in at.button if b.label == "Preencher com a sugestão").click().run()
    assert not at.exception
    assert sum(1 for q in _quadrados(at) if q.value) >= 2  # o único jogo vira duplo ou triplo
    next(b for b in at.button if b.label == "Limpar").click().run()
    assert not any(q.value for q in _quadrados(at))


def test_salvar_com_jogo_em_branco_e_bloqueado_e_nao_grava(banco):
    at = _abrir()
    next(b for b in at.button if b.label == "Salvar bilhete").click().run()
    assert any("Falta marcar o(s) jogo(s) 1." in e.value for e in at.error)
    with db.sessao() as c:
        assert c.execute("SELECT COUNT(*) FROM bilhetes").fetchone()[0] == 0


def test_salvar_com_duplo_marcado_grava_as_colunas_escolhidas(banco):
    at = _abrir()
    quadrados = {q.key.rsplit("_", 1)[1]: q for q in _quadrados(at)}
    quadrados["1"].check()
    quadrados["2"].check().run()
    assert any("1 de 1 jogos marcados · 1 duplo(s)" in i.value for i in at.info)
    next(b for b in at.button if b.label == "Salvar bilhete").click().run()
    assert not at.exception and not at.error
    with db.sessao() as c:
        assert c.execute("SELECT marcacoes FROM bilhete_jogos").fetchone()[0] == "1,2"


# --- Análise do palpite (item 20) ---

def _marcar_duplo_1_2(at: AppTest) -> AppTest:
    quadrados = {q.key.rsplit("_", 1)[1]: q for q in _quadrados(at)}
    quadrados["1"].check()
    return quadrados["2"].check().run()


def test_analisar_com_volante_incompleto_pede_para_marcar_tudo(banco):
    at = _abrir()
    next(b for b in at.button if b.label == "Analisar meu palpite").click().run()
    assert not at.exception
    assert any("Para analisar, marque todos os jogos. Falta(m): 1." in i.value for i in at.info)


def test_analisar_mostra_leitura_chance_e_duplo(banco):
    at = _marcar_duplo_1_2(_abrir())
    next(b for b in at.button if b.label == "Analisar meu palpite").click().run()
    assert not at.exception, [e.value for e in at.exception]
    textos = " ".join(m.value for m in at.markdown)
    assert "Análise do seu palpite" in textos
    assert "Jogo 1 (duplo): a chance do jogo vai de" in textos
    assert "sem base própria" in textos  # ALFA x BETA tem só 3 jogos na base sintética
    assert any(m.label == "Chance de 1 acertos (pelos percentuais)" for m in at.metric)
    # Recomendações do estudo E1-E4: o que aconteceu de fato ao lado da chance, e a complexidade do jogo.
    assert any("Ainda não há concursos passados suficientes" in i.value for i in at.info)
    assert "Complexidade do jogo" in textos and "pouco histórico dos dois times" in textos
    next(b for b in at.button if b.label == "Fechar análise").click().run()
    assert "Análise do seu palpite" not in " ".join(m.value for m in at.markdown)


# --- Versões do palpite (30/09/2026) ---

def _botao(at: AppTest, rotulo: str):
    return next(b for b in at.button if b.label == rotulo)


def test_guardar_versao_so_com_todos_os_jogos_marcados(banco):
    at = _abrir()
    assert _botao(at, "Guardar esta versão").disabled
    assert any("Nenhuma versão guardada" in c.value for c in at.caption)


def test_guardar_comparar_voltar_e_salvar_liga_a_versao(banco):
    at = _marcar_duplo_1_2(_abrir())
    _botao(at, "Guardar esta versão").click().run()
    assert any("Versão 1 guardada." in s.value for s in at.success)
    _botao(at, "Guardar esta versão").click().run()  # mesma marcação: não repete
    assert any("já está guardada como versão 1" in i.value for i in at.info)

    quadrados = {q.key.rsplit("_", 1)[1]: q for q in _quadrados(at)}
    quadrados["2"].uncheck().run()  # vira seco no 1
    assert any("difere da versão 1 em 1 jogo(s): jogo 1: 12 (duplo) virou 1 (seco)" in i.value for i in at.info)
    _botao(at, "Guardar esta versão").click().run()
    textos = " ".join(m.value for m in at.markdown)
    assert "Comparação das versões" in textos and "Versão 2** em relação à 1: jogo 1: 12 (duplo) virou 1 (seco)" in textos

    at.selectbox(key="versao_escolhida_9002").select(1).run()
    _botao(at, "Voltar a esta versão").click().run()
    assert {q.key.rsplit("_", 1)[1] for q in _quadrados(at) if q.value} == {"1", "2"}  # voltou ao duplo

    _botao(at, "Salvar bilhete").click().run()
    assert not at.exception and any("Ligado à versão 1." in s.value for s in at.success)
    with db.sessao() as c:
        ligadas = c.execute("SELECT numero_versao, bilhete_id FROM versoes_palpite ORDER BY numero_versao").fetchall()
    assert [(v[0], v[1] is not None) for v in ligadas] == [(1, True), (2, False)]


def test_salvar_sem_versao_guardada_cria_uma_e_liga(banco):
    at = _marcar_duplo_1_2(_abrir())
    _botao(at, "Salvar bilhete").click().run()
    assert not at.exception and any("Ligado à versão 1." in s.value for s in at.success)


def test_analise_com_dois_jogos_traz_sugestao_contra_o_favorito_e_economia(banco):
    """Recomendações do estudo E1-E4 (aprovadas em 30/09/2026) na tela, sem aumentar o custo."""
    with db.sessao() as c:
        alfa = c.execute("SELECT id FROM participantes WHERE nome = 'ALFA'").fetchone()[0]
        beta = c.execute("SELECT id FROM participantes WHERE nome = 'BETA'").fetchone()[0]
        c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9002, 2, ?, ?, '2099-01-02')",
                  (beta, alfa))
    at = _abrir()
    colunas = {q.key.split("_", 2)[2]: q for q in _quadrados(at)}  # "<jogo_id>_<coluna>"
    ids = sorted({chave.rsplit("_", 1)[0] for chave in colunas}, key=int)
    for coluna in ("1", "X", "2"):
        colunas[f"{ids[0]}_{coluna}"].check()  # jogo 1: triplo
    colunas[f"{ids[1]}_2"].check().run()  # jogo 2: só o visitante, contra o favorito dos dados
    next(b for b in at.button if b.label == "Analisar meu palpite").click().run()
    assert not at.exception, [e.value for e in at.exception]
    textos = " ".join(m.value for m in at.markdown)
    assert "Sugestões de alteração, pelo mesmo custo" in textos
    assert "Levar o triplo do jogo 1 para o jogo 2" in textos and "pelo mesmo custo" in textos
    # O jogo 2 é equilibrado (favorito com 37%): a linha "contra o favorito" não se aplica aqui (teste unitário cobre).
    assert "Você marcou contra o favorito dos dados" not in textos
    assert "Se quiser gastar menos" in textos and "Jogo 1: tirar a coluna" in textos
    assert not any("rendeu" in c.value for c in at.caption)  # banco sintético: sem concursos para medir o efeito
    coluna_complexidade = [m.value for m in at.markdown if "Complexidade do jogo" in m.value]
    assert len(coluna_complexidade) >= 2  # quadro do ano em curso e tabela da análise


def test_salvar_guarda_a_analise_e_o_motivo(banco):
    at = _marcar_duplo_1_2(_abrir())
    at.multiselect(key=next(k for k in (w.key for w in at.multiselect) if k.startswith("motivo_9002_"))).select("Intuição").run()
    next(b for b in at.button if b.label == "Salvar bilhete").click().run()
    assert not at.exception and not at.error
    with db.sessao() as c:
        linha = c.execute("SELECT categoria, motivos, sem_base_propria FROM bilhete_jogos").fetchone()
        assert linha["categoria"] is not None and linha["motivos"] == '["Intuição"]' and linha["sem_base_propria"] == 1
        assert c.execute("SELECT acertos_esperados FROM bilhetes").fetchone()[0] is not None

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


# --- Card 3: volante com 3 quadrados por jogo ---

def _quadrados(at: AppTest) -> list:
    return [c for c in at.checkbox if c.key and c.key.startswith("volante_9002_")]


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
    assert any(m.label == "Chance de 1 acertos" for m in at.metric)
    next(b for b in at.button if b.label == "Fechar análise").click().run()
    assert "Análise do seu palpite" not in " ".join(m.value for m in at.markdown)


def test_salvar_guarda_a_analise_e_o_motivo(banco):
    at = _marcar_duplo_1_2(_abrir())
    at.multiselect(key=next(k for k in (w.key for w in at.multiselect) if k.startswith("motivo_9002_"))).select("Intuição").run()
    next(b for b in at.button if b.label == "Salvar bilhete").click().run()
    assert not at.exception and not at.error
    with db.sessao() as c:
        linha = c.execute("SELECT categoria, motivos, sem_base_propria FROM bilhete_jogos").fetchone()
        assert linha["categoria"] is not None and linha["motivos"] == '["Intuição"]' and linha["sem_base_propria"] == 1
        assert c.execute("SELECT acertos_esperados FROM bilhetes").fetchone()[0] is not None

"""Etapa A3: salvar, reler, conferir e acompanhar gasto x prêmio do bilhete."""
import sqlite3

import pytest

import db
from stats.bilhetes_salvos import (
    arquivar_simulados,
    bilhete_igual,
    confirmar_situacao,
    conferir_bilhete,
    jogos_do_bilhete,
    listar_arquivados,
    quadro_do_concurso,
    restaurar_bilhete,
    listar_bilhetes,
    pode_conferir,
    registrar_premio,
    resumo_financeiro,
    salvar_bilhete,
)


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    a = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
    b = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
    d = db.obter_ou_criar_participante(c, "DELTA", "clube", "MG")
    e = db.obter_ou_criar_participante(c, "EPSILON", "clube", "BA")
    c.execute("INSERT INTO concursos (numero) VALUES (1271)")
    c.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
        " VALUES (1271, 1, ?, ?, 2, 0, '1')", (a, b),
    )
    c.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
        " VALUES (1271, 2, ?, ?, 1, 1, 'X')", (d, e),
    )
    return c


def _marcacoes_e_percentuais(conexao, jogo1=("1",), jogo2=("X",)):
    ids = [r["id"] for r in conexao.execute("SELECT id FROM jogos ORDER BY num_jogo")]
    marcacoes = {ids[0]: list(jogo1), ids[1]: list(jogo2)}
    percentuais = {
        ids[0]: {"1": 50.0, "X": 30.0, "2": 20.0},
        ids[1]: {"1": 34.0, "X": 33.0, "2": 33.0},
    }
    return marcacoes, percentuais


def test_salvar_calcula_apostas_e_custo_pelo_produto_das_marcacoes(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao, jogo1=("1", "X"), jogo2=("1", "X", "2"))
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    bilhete = listar_bilhetes(conexao)[0]
    assert bilhete["id"] == bilhete_id and bilhete["apostas"] == 6 and bilhete["custo"] == pytest.approx(12.0)


def test_salvar_reler_e_reabrir_mantem_a_marcacao(tmp_path):
    """Critério de aceite do plano: fecha o banco (simula fechar o app) e abre
    de novo -- a marcação salva continua lá, igual."""
    caminho = tmp_path / "bilhetes.db"
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.executescript(db.SCHEMA)
    a = db.obter_ou_criar_participante(conexao, "ALFA", "clube", "SP")
    b = db.obter_ou_criar_participante(conexao, "BETA", "clube", "RJ")
    d = db.obter_ou_criar_participante(conexao, "DELTA", "clube", "MG")
    e = db.obter_ou_criar_participante(conexao, "EPSILON", "clube", "BA")
    conexao.execute("INSERT INTO concursos (numero) VALUES (1271)")
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
        " VALUES (1271, 1, ?, ?, 2, 0, '1')", (a, b),
    )
    conexao.execute(
        "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, gols_casa, gols_fora, resultado)"
        " VALUES (1271, 2, ?, ?, 1, 1, 'X')", (d, e),
    )
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao, jogo1=("1", "2"), jogo2=("X",))
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    conexao.commit()
    conexao.close()

    reaberta = sqlite3.connect(caminho)
    reaberta.row_factory = sqlite3.Row
    jogos = jogos_do_bilhete(reaberta, bilhete_id)
    por_num = {j["num_jogo"]: j for j in jogos}
    assert sorted(por_num[1]["marcacoes"]) == ["1", "2"] and por_num[1]["percentual_1"] == 50.0
    assert por_num[2]["marcacoes"] == ["X"]
    reaberta.close()


def test_conferir_bate_com_resultado_conhecido_do_concurso_1271(conexao):
    # jogo 1 resultado real '1' (marcado certo), jogo 2 resultado real 'X' (marcado errado, apostou '2')
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao, jogo1=("1",), jogo2=("2",))
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)

    resultado = conferir_bilhete(conexao, bilhete_id)
    assert resultado["acertos"] == 1 and resultado["total_jogos"] == 2

    bilhete = listar_bilhetes(conexao)[0]
    assert bilhete["acertos"] == 1 and bilhete["conferido_em"] is not None

    jogos = jogos_do_bilhete(conexao, bilhete_id)
    por_num = {j["num_jogo"]: j for j in jogos}
    assert por_num[1]["acertou"] == 1 and por_num[2]["acertou"] == 0


def test_nao_confere_bilhete_com_jogo_ainda_sem_resultado(conexao):
    conexao.execute("UPDATE jogos SET resultado = NULL, gols_casa = NULL, gols_fora = NULL WHERE num_jogo = 2")
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    assert not pode_conferir(jogos_do_bilhete(conexao, bilhete_id))
    assert conferir_bilhete(conexao, bilhete_id) is None
    assert listar_bilhetes(conexao)[0]["conferido_em"] is None


def test_conferir_e_idempotente(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    r1 = conferir_bilhete(conexao, bilhete_id)
    r2 = conferir_bilhete(conexao, bilhete_id)
    assert r1["acertos"] == r2["acertos"]


def test_acertos_da_sugestao_do_modelo_e_calculado_sobre_o_percentual_salvo(conexao):
    # favorito (1) do jogo 1 é 50%; sugestão simples marca só o favorito -- bate com o real '1'
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao, jogo1=("2",), jogo2=("2",))  # usuário marcou diferente do favorito
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    resultado = conferir_bilhete(conexao, bilhete_id)
    assert resultado["acertos"] == 0  # usuário errou os dois
    assert resultado["acertos_sugestao_do_modelo"] >= 1  # a sugestão do modelo (favorito) acerta o jogo 1


def test_registrar_premio_e_resumo_financeiro(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    b1 = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    b2 = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    b3 = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    registrar_premio(conexao, b1, 25.50)
    registrar_premio(conexao, b3, 99.0)  # prêmio de bilhete simulado não entra
    # 10/10/2026: só o apostado conta no gasto, no prêmio e no saldo.
    assert resumo_financeiro(conexao)["gasto_total"] == 0 and resumo_financeiro(conexao)["rascunhos"] == 3
    confirmar_situacao(conexao, b1, "apostado")
    confirmar_situacao(conexao, b2, "apostado")
    confirmar_situacao(conexao, b3, "simulado")

    resumo = resumo_financeiro(conexao)
    assert (resumo["bilhetes"], resumo["apostados"], resumo["simulados"], resumo["rascunhos"]) == (3, 2, 1, 0)
    assert resumo["gasto_total"] == pytest.approx(4.0)  # 2 bilhetes de 1 aposta (2 jogos, 1 marcação cada) = R$2 cada
    assert resumo["premio_total"] == pytest.approx(25.50)
    assert resumo["saldo"] == pytest.approx(21.50)


# --- "Foi apostado?" e "Limpar simulados" (10/10/2026) ---

def test_situacao_responder_desfazer_limpar_e_restaurar(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    apostado = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    simulado = salvar_bilhete(conexao, 1271, {k: ["2"] for k in marcacoes}, percentuais)
    rascunho = salvar_bilhete(conexao, 1271, {k: ["X"] for k in marcacoes}, percentuais)
    assert {b["situacao"] for b in listar_bilhetes(conexao)} == {"rascunho"}

    confirmar_situacao(conexao, apostado, "apostado")
    confirmar_situacao(conexao, simulado, "apostado")
    confirmar_situacao(conexao, simulado, "simulado")  # trocar a resposta não deixa as duas datas
    linha = conexao.execute("SELECT jogado_em, simulado_em FROM bilhetes WHERE id = ?", (simulado,)).fetchone()
    assert linha["jogado_em"] is None and linha["simulado_em"] is not None
    with pytest.raises(ValueError, match="Situação desconhecida"):
        confirmar_situacao(conexao, rascunho, "talvez")

    # Limpar arquiva só o simulado: rascunho e apostado ficam.
    assert arquivar_simulados(conexao) == 1 and arquivar_simulados(conexao) == 0
    assert {b["id"]: b["situacao"] for b in listar_bilhetes(conexao)} == {apostado: "apostado", rascunho: "rascunho"}
    assert [b["id"] for b in listar_arquivados(conexao)] == [simulado]
    assert [l["id"] for l in quadro_do_concurso(conexao, 1271)] == [apostado, rascunho]
    assert bilhete_igual(conexao, 1271, {k: ["2"] for k in marcacoes}) is None  # arquivado não dispara o aviso
    assert resumo_financeiro(conexao)["simulados"] == 0
    with pytest.raises(ValueError, match="arquivado"):
        confirmar_situacao(conexao, simulado, "apostado")
    assert conexao.execute("SELECT COUNT(*) FROM bilhetes").fetchone()[0] == 3  # nada foi apagado

    restaurar_bilhete(conexao, simulado)
    assert {b["id"]: b["situacao"] for b in listar_bilhetes(conexao)}[simulado] == "simulado"
    confirmar_situacao(conexao, apostado, "rascunho")  # desfazer a resposta
    assert {b["id"]: b["situacao"] for b in listar_bilhetes(conexao)}[apostado] == "rascunho"


def test_listar_bilhetes_filtra_por_concurso(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    conexao.execute("INSERT INTO concursos (numero) VALUES (1272)")
    assert len(listar_bilhetes(conexao, concurso_numero=1271)) == 1
    assert listar_bilhetes(conexao, concurso_numero=1272) == []


# --- Análise do palpite guardada com o bilhete (item 20) ---
from stats.analise_palpite import analisar_palpite
from stats.bilhetes_salvos import jogos_conferidos_para_historico


def test_salvar_com_analise_e_motivos_guarda_para_aprendizado(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao, jogo1=("1", "X"), jogo2=("2",))
    ids = list(marcacoes)
    analise = analisar_palpite(
        [
            {"jogo_id": ids[0], "num_jogo": 1, "casa": "ALFA", "fora": "BETA", "pct": percentuais[ids[0]], "marcacoes": marcacoes[ids[0]]},
            {"jogo_id": ids[1], "num_jogo": 2, "casa": "DELTA", "fora": "EPSILON", "pct": percentuais[ids[1]],
             "marcacoes": marcacoes[ids[1]], "sem_base_propria": True},
        ]
    )
    motivos = {ids[0]: ["Clássico ou rivalidade", "motivo inventado"], ids[1]: []}
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais, analise=analise, motivos=motivos)

    bilhete = conexao.execute("SELECT * FROM bilhetes WHERE id = ?", (bilhete_id,)).fetchone()
    assert bilhete["chance_todos"] == pytest.approx(0.8 * 0.33)
    assert bilhete["acertos_esperados"] == pytest.approx(0.8 + 0.33)
    linhas = conexao.execute("SELECT * FROM bilhete_jogos WHERE bilhete_id = ? ORDER BY id", (bilhete_id,)).fetchall()
    assert [r["categoria"] for r in linhas] == ["a_favor", "equilibrado"]
    assert [r["sem_base_propria"] for r in linhas] == [0, 1]
    assert linhas[0]["motivos"] == '["Clássico ou rivalidade"]'  # motivo fora da lista é descartado
    assert linhas[1]["motivos"] is None


def test_salvar_sem_analise_continua_funcionando(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    bilhete_id = salvar_bilhete(conexao, 1271, marcacoes, percentuais)
    assert conexao.execute("SELECT chance_todos FROM bilhetes WHERE id = ?", (bilhete_id,)).fetchone()[0] is None


def test_historico_so_traz_bilhetes_conferidos(conexao):
    marcacoes, percentuais = _marcacoes_e_percentuais(conexao)
    conferido = salvar_bilhete(conexao, 1271, marcacoes, percentuais, motivos={list(marcacoes)[0]: ["Intuição"]})
    salvar_bilhete(conexao, 1271, marcacoes, percentuais)  # não conferido
    conferir_bilhete(conexao, conferido)
    assert jogos_conferidos_para_historico(conexao) == []  # rascunho não entra (10/10/2026)
    confirmar_situacao(conexao, conferido, "apostado")
    historico = jogos_conferidos_para_historico(conexao)
    assert len(historico) == 1 and len(historico[0]) == 2
    assert historico[0][0]["motivos"] == ["Intuição"] and historico[0][0]["resultado"] == "1"

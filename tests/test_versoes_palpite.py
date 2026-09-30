import pytest

import config
import db
from stats.versoes_palpite import (
    LimiteDeVersoes,
    acertos,
    agregar_aprendizado,
    aprendizado_das_versoes,
    aprendizado_de_todos_os_concursos,
    apostas_de,
    diferencas,
    frase_da_mudanca,
    guardar_versao,
    historia_do_bilhete,
    ligar_ao_bilhete,
    listar_versoes,
    resumo_da_analise,
)

PCT = {"1": 50.0, "X": 30.0, "2": 20.0}


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    db.inicializar_schema()
    with db.sessao() as c:
        a = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        b = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero) VALUES (9002)")
        for num in (1, 2):
            c.execute("INSERT INTO jogos (id, concurso_numero, num_jogo, casa_id, fora_id) VALUES (?, 9002, ?, ?, ?)",
                      (num, num, a, b))
    return True


def test_diferencas_na_ordem_do_concurso_e_frase():
    mudancas = diferencas({10: ["1"], 11: ["X", "1"]}, {10: ["1", "X"], 11: ["1", "X"]}, {10: 5, 11: 2})
    assert len(mudancas) == 1  # a ordem das colunas não conta como mudança
    assert mudancas[0]["acrescentou"] == ["X"] and mudancas[0]["retirou"] == []
    assert frase_da_mudanca(mudancas[0]) == "jogo 5: 1 (seco) virou 1X (duplo)"


def test_diferencas_aceita_chaves_em_texto_como_vem_do_json():
    assert diferencas({"1": ["2"]}, {1: ["2"]}) == []


def test_apostas_e_resumo_sem_analise():
    marc = {1: ["1"], 2: ["1", "X"], 3: ["1", "X", "2"]}
    assert apostas_de(marc) == 6
    assert resumo_da_analise(None, marc) == {"duplos": 1, "triplos": 1}


def test_acertos_espera_o_resultado_de_todos_os_jogos():
    assert acertos({1: ["1"], 2: ["X", "2"]}, {1: "1", 2: "2"}) == 2
    assert acertos({1: ["1"], 2: ["X"]}, {1: "1", 2: None}) is None


def test_aprendizado_compara_a_primeira_com_a_que_virou_bilhete():
    versoes = [
        {"numero_versao": 1, "marcacoes": {1: ["1"], 2: ["1"]}, "apostas": 1, "bilhete_id": None},
        {"numero_versao": 2, "marcacoes": {1: ["1"], 2: ["X"]}, "apostas": 1, "bilhete_id": 7},
        {"numero_versao": 3, "marcacoes": {1: ["2"], 2: ["X"]}, "apostas": 1, "bilhete_id": None},
    ]
    leitura = aprendizado_das_versoes(versoes, {1: "1", 2: "X"})
    assert (leitura["numero_final"], leitura["acertos_primeira"], leitura["acertos_final"], leitura["saldo"]) == (2, 1, 2, 1)
    assert aprendizado_das_versoes(versoes[:1], {1: "1", 2: "X"}) is None  # uma versão só: nada a comparar


def test_historia_do_bilhete():
    versoes = [
        {"numero_versao": 1, "marcacoes": {1: ["1"], 2: ["1"]}, "bilhete_id": None},
        {"numero_versao": 2, "marcacoes": {1: ["1"], 2: ["X", "2"]}, "bilhete_id": 7},
    ]
    historia = historia_do_bilhete(versoes, 7, {1: "1", 2: "2"}, {1: 1, 2: 2})
    assert (historia["versoes"], historia["numero"], historia["acertos_primeira"], historia["acertos_bilhete"]) == (2, 2, 1, 2)
    assert frase_da_mudanca(historia["mudancas"][0]) == "jogo 2: 1 (seco) virou X2 (duplo)"
    assert historia_do_bilhete(versoes, 99, {}) is None
    so_uma = historia_do_bilhete([{**versoes[0], "bilhete_id": 3}], 3, {1: None, 2: None})
    assert so_uma["mudancas"] == [] and so_uma["acertos_primeira"] is None and so_uma["acertos_bilhete"] is None


def test_agregar_marca_amostra_insuficiente():
    agregado = agregar_aprendizado([{"saldo": 1}, {"saldo": 0}, {"saldo": -2}])
    assert (agregado["ajudaram"], agregado["iguais"], agregado["atrapalharam"], agregado["saldo_total"]) == (1, 1, 1, -1)
    assert agregado["amostra_suficiente"] is False


def test_guardar_numera_nao_duplica_e_liga_ao_bilhete(banco):
    with db.sessao() as c:
        v1 = guardar_versao(c, 9002, {1: ["1"], 2: ["X"]}, {1: PCT, 2: PCT}, None)
        repetida = guardar_versao(c, 9002, {"2": ["X"], "1": ["1"]}, {1: PCT, 2: PCT}, None)
        v2 = guardar_versao(c, 9002, {1: ["1", "X"], 2: ["X"]}, {1: PCT, 2: PCT},
                            {"chance": {"chance_todos": 0.24, "chance_todos_menos_um_ou_mais": 1.0, "acertos_esperados": 1.1},
                             "resumo_categorias": {}, "zebras": [], "sem_base_propria": []})
        assert v1["nova"] and not repetida["nova"] and repetida["versao"]["id"] == v1["versao"]["id"]
        assert v2["versao"]["numero_versao"] == 2 and v2["versao"]["apostas"] == 2 and v2["versao"]["custo"] == 4.0
        c.execute("INSERT INTO bilhetes (id, concurso_numero, criado_em, apostas, custo) VALUES (7, 9002, 'x', 2, 4.0)")
        ligar_ao_bilhete(c, v2["versao"]["id"], 7)
        versoes = listar_versoes(c, 9002)
    assert [v["numero_versao"] for v in versoes] == [1, 2] and versoes[1]["bilhete_id"] == 7
    assert versoes[1]["chance_todos"] == 0.24 and versoes[0]["percentuais"][1] == PCT


def test_guardar_com_jogo_em_branco_e_recusado(banco):
    with db.sessao() as c, pytest.raises(ValueError):
        guardar_versao(c, 9002, {1: ["1"], 2: []}, {}, None)


def test_limite_de_versoes(banco, monkeypatch):
    monkeypatch.setattr(config, "VERSOES_MAX_POR_CONCURSO", 1)
    with db.sessao() as c:
        guardar_versao(c, 9002, {1: ["1"], 2: ["1"]}, {}, None)
        with pytest.raises(LimiteDeVersoes):
            guardar_versao(c, 9002, {1: ["X"], 2: ["1"]}, {}, None)


def test_aprendizado_de_todos_so_com_resultado_completo(banco):
    with db.sessao() as c:
        guardar_versao(c, 9002, {1: ["1"], 2: ["1"]}, {}, None)
        guardar_versao(c, 9002, {1: ["1"], 2: ["2"]}, {}, None)
        assert aprendizado_de_todos_os_concursos(c) == []  # ainda sem resultado
        c.execute("UPDATE jogos SET resultado = '1' WHERE id = 1")
        c.execute("UPDATE jogos SET resultado = '2' WHERE id = 2")
        leituras = aprendizado_de_todos_os_concursos(c)
    assert leituras == [{"concurso_numero": 9002, "versoes": 2, "numero_final": 2, "acertos_primeira": 1,
                         "acertos_final": 2, "saldo": 1, "apostas_primeira": 1, "apostas_final": 1}]

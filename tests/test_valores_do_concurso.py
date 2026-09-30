"""Valores de cada concurso (arrecadação, acumulados, premiação): importação e preenchimento do histórico."""
import pytest

import config
import db
from importer import caixa_client as caixa

CORPO = {
    "numero": 1272, "dataApuracao": "28/09/2026", "dataProximoConcurso": "03/10/2026", "acumulado": False,
    "valorEstimadoProximoConcurso": 600000.0, "valorArrecadado": 2570788.0,
    "valorAcumuladoConcurso_0_5": 298574.51, "valorAcumuladoConcursoEspecial": 630726.95,
    "valorAcumuladoProximoConcurso": 0.0, "listaResultadoEquipeEsportiva": [],
    "listaRateioPremio": [
        {"faixa": 1, "numeroDeGanhadores": 1, "valorPremio": 1294441.38},
        {"faixa": 2, "numeroDeGanhadores": 13, "valorPremio": 7613.49},
    ],
}


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    monkeypatch.setattr(config, "CAIXA_REQUEST_INTERVAL_SEGUNDOS", 0)
    db.inicializar_schema()
    return True


def test_valores_do_concurso_le_os_campos_e_nao_inventa_zero():
    assert caixa.valores_do_concurso(CORPO) == (2570788.0, 298574.51, 630726.95, 0.0)
    assert caixa.valores_do_concurso({}) == (None, None, None, None)
    assert caixa.valores_do_concurso({"valorArrecadado": None, "valorAcumuladoConcurso_0_5": "x", "valorAcumuladoConcursoEspecial": True}) == (
        None, None, None, None)


def test_arrecadacao_zero_da_api_e_sem_dado_mas_acumulado_zero_e_zero():
    """Concursos antigos: a API devolve valorArrecadado 0,0 quando não informa. Acumulado zero é zero de verdade."""
    assert caixa.valores_do_concurso({"valorArrecadado": 0.0, "valorAcumuladoProximoConcurso": 0.0,
                                      "valorAcumuladoConcurso_0_5": 187889.5}) == (None, 187889.5, None, 0.0)
    assert caixa.valores_do_concurso({"valorArrecadado": -5.0})[0] is None


def test_importar_concurso_grava_os_valores(banco, monkeypatch):
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": CORPO)
    with db.sessao() as c:
        assert caixa.importar_concurso(1272, c) == 1272
        linha = c.execute("SELECT valor_arrecadado, valor_acumulado_final_0_5, valor_acumulado_especial,"
                          " valor_acumulado_proximo FROM concursos WHERE numero = 1272").fetchone()
    assert tuple(linha) == (2570788.0, 298574.51, 630726.95, 0.0)


def _semear(conexao, numeros):
    """Concursos já importados (gravados), como no banco real: o preenchimento faz rollback em falha."""
    for n in numeros:
        conexao.execute("INSERT INTO concursos (numero) VALUES (?)", (n,))
    conexao.commit()


def test_importar_concurso_marca_que_ja_consultou_os_valores(banco, monkeypatch):
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": CORPO)
    with db.sessao() as c:
        caixa.importar_concurso(1272, c)
        assert c.execute("SELECT valores_consultados_em FROM concursos WHERE numero = 1272").fetchone()[0] is not None
        resumo = caixa.completar_valores_do_historico(c, 1272, 1272)
    assert resumo["ja_tinham"] == 1 and resumo["atualizados"] == 0


def test_normalizar_corrige_o_que_a_primeira_versao_gravou_e_e_idempotente(banco):
    with db.sessao() as c:
        _semear(c, [1, 2, 3])
        c.execute("UPDATE concursos SET valor_arrecadado = 0.0 WHERE numero = 1")  # gravado como zero
        c.execute("UPDATE concursos SET valor_arrecadado = 2500000.0 WHERE numero = 2")  # dado de verdade
        # o 3 nunca foi preenchido (valor_arrecadado NULL, sem marca)
        c.commit()
        assert caixa.normalizar_valores_ja_gravados(c) == {"marcados_como_consultados": 2, "arrecadacao_zero_virou_ausente": 1}
        linhas = {r[0]: (r[1], r[2] is not None) for r in c.execute("SELECT numero, valor_arrecadado, valores_consultados_em FROM concursos")}
        assert caixa.normalizar_valores_ja_gravados(c) == {"marcados_como_consultados": 0, "arrecadacao_zero_virou_ausente": 0}
    assert linhas == {1: (None, True), 2: (2500000.0, True), 3: (None, False)}


def test_completar_preenche_so_os_valores_e_a_premiacao_sem_tocar_nos_jogos(banco, monkeypatch):
    chamadas = []

    def falso(sufixo=""):
        chamadas.append(sufixo)
        return {**CORPO, "numero": int(sufixo[1:]), "valorArrecadado": 1000.0 * int(sufixo[1:])}

    monkeypatch.setattr(caixa, "_buscar_json", falso)
    with db.sessao() as c:
        _semear(c, [10, 11, 12])
        c.execute("UPDATE concursos SET valor_arrecadado = 55.0, valores_consultados_em = 'x' WHERE numero = 11")  # já consultado
        resumo = caixa.completar_valores_do_historico(c, 10, 12)
        valores = {r[0]: r[1] for r in c.execute("SELECT numero, valor_arrecadado FROM concursos ORDER BY numero")}
        faixas = c.execute("SELECT COUNT(*) FROM premiacoes").fetchone()[0]
        jogos = c.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
    assert resumo == {"atualizados": 2, "ja_tinham": 1, "sem_valor_na_api": [], "falhas": {}}
    assert chamadas == ["/10", "/12"] and valores == {10: 10000.0, 11: 55.0, 12: 12000.0}
    assert faixas == 4 and jogos == 0


def test_completar_ignora_concurso_nunca_importado_e_registra_falha_depois_de_duas_tentativas(banco, monkeypatch):
    def falho(sufixo=""):
        raise caixa.ErroImportacaoLoteca("HTTP 500")

    monkeypatch.setattr(caixa, "_buscar_json", falho)
    with db.sessao() as c:
        _semear(c, [20])
        resumo = caixa.completar_valores_do_historico(c, 19, 21)  # 19 e 21 não existem no banco
        assert c.execute("SELECT valor_arrecadado FROM concursos WHERE numero = 20").fetchone()[0] is None
    assert resumo["falhas"] == {20: "HTTP 500"} and resumo["atualizados"] == 0


def test_completar_anota_concurso_que_a_api_entrega_sem_arrecadacao(banco, monkeypatch):
    monkeypatch.setattr(caixa, "_buscar_json", lambda sufixo="": {"numero": 5, "listaRateioPremio": []})
    with db.sessao() as c:
        _semear(c, [5])
        resumo = caixa.completar_valores_do_historico(c, 5, 5)
    assert resumo["atualizados"] == 1 and resumo["sem_valor_na_api"] == [5]

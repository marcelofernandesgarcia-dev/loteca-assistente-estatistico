import pytest

import config
import db
from stats.premiacao import (
    estatisticas_do_historico,
    reais,
    resumo_do_concurso,
    resumo_por_numero,
    serie_historica,
)

CONCURSO_1272 = {
    "numero": 1272, "valor_arrecadado": 2570788.0, "valor_acumulado_final_0_5": 298574.51,
    "valor_acumulado_especial": 630726.95, "valor_acumulado_proximo": 0.0, "valor_estimado_proximo": 600000.0,
}
FAIXAS_1272 = [
    {"faixa": 1, "pontos": 14, "ganhadores": 1, "valor_premio": 1294441.38},
    {"faixa": 2, "pontos": 13, "ganhadores": 13, "valor_premio": 7613.49},
]


def test_reais_em_portugues():
    assert reais(1294441.38) == "R$ 1.294.441,38"
    assert reais(0) == "R$ 0,00" and reais(None) == "sem dado"


def test_resumo_do_1272_com_os_numeros_da_api():
    r = resumo_do_concurso(CONCURSO_1272, FAIXAS_1272)
    assert r["arrecadado"] == 2570788.0
    assert "destinado_a_premios" not in r  # o app não deriva valores da regra de divisão (decisão de 30/09/2026)
    assert r["faixas"][0]["total"] == 1294441.38
    assert round(r["faixas"][1]["total"], 2) == 98975.37  # 13 x 7.613,49
    assert round(r["total_pago"], 2) == 1393416.75 and r["ganhadores_total"] == 14
    assert r["sem_ganhador_14"] is False
    assert (r["acumulado_final_0_5"], r["acumulado_especial"], r["estimativa_proximo"]) == (298574.51, 630726.95, 600000.0)


def test_concurso_sem_ganhador_de_14_acumula():
    r = resumo_do_concurso(CONCURSO_1272, [
        {"faixa": 1, "pontos": 14, "ganhadores": 0, "valor_premio": 0.0},
        {"faixa": 2, "pontos": 13, "ganhadores": 40, "valor_premio": 2000.0},
    ])
    assert r["sem_ganhador_14"] is True and r["total_pago"] == 80000.0


def test_dado_ausente_fica_none_e_nunca_zero():
    r = resumo_do_concurso({"numero": 3}, [{"faixa": 1, "pontos": 14, "ganhadores": None, "valor_premio": None}])
    assert r["arrecadado"] is None and r["total_pago"] is None
    assert r["faixas"][0]["total"] is None
    assert r["sem_ganhador_14"] is False  # sem dado não é "sem ganhador"
    vazio = resumo_do_concurso({"numero": 4}, [])
    assert vazio["faixas"] == [] and vazio["total_pago"] is None and vazio["ganhadores_total"] is None


@pytest.fixture()
def banco(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "sintetico.db")
    db.inicializar_schema()
    with db.sessao() as c:
        for numero, arrec, g14, p14, g13, p13 in (
            (1, 1000.0, 0, 0.0, 10, 50.0), (2, 2000.0, 1, 5000.0, 20, 40.0), (3, None, 2, 900.0, 5, 30.0),
        ):
            c.execute("INSERT INTO concursos (numero, valor_arrecadado) VALUES (?, ?)", (numero, arrec))
            c.execute("INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (?, 1, 14, ?, ?)", (numero, g14, p14))
            c.execute("INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (?, 2, 13, ?, ?)", (numero, g13, p13))
        c.execute("INSERT INTO concursos (numero) VALUES (4)")  # concurso a jogar: sem premiação
    return True


def test_serie_historica_so_traz_apurados_e_calcula_o_total(banco):
    with db.sessao() as c:
        serie = serie_historica(c)
        resumo = resumo_por_numero(c, 2)
        assert resumo_por_numero(c, 999) is None
    assert [s["numero"] for s in serie] == [1, 2, 3]
    assert serie[1]["total_pago"] == 5000.0 + 20 * 40.0 and serie[0]["total_pago"] == 500.0
    assert resumo["total_pago"] == 5800.0 and resumo["faixas"][1]["ganhadores"] == 20


def test_estatisticas_do_historico(banco):
    with db.sessao() as c:
        est = estatisticas_do_historico(serie_historica(c))
    assert est["concursos"] == 3 and est["sem_ganhador_14"] == 1
    assert round(est["percentual_sem_ganhador_14"], 1) == 33.3
    assert est["maior_premio_14"] == {"numero": 2, "valor": 5000.0}
    assert est["arrecadacao_mediana"] == 1500.0 and est["com_arrecadacao"] == 2  # o 3 não tem arrecadação
    vazio = estatisticas_do_historico([])
    assert vazio["concursos"] == 0 and vazio["percentual_sem_ganhador_14"] is None and vazio["maior_premio_14"] is None

"""stats/anti_manada.py: estudo anti-manada (Q7). Banco em memória e dados sintéticos, sem rede."""
import sqlite3

import numpy as np
import pytest

import config
import db
from stats import anti_manada


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def _concurso(conexao, numero, resultados, arrecadacao=2_000_000.0, ganhadores=4, premio=1000.0, data="2024-05-01"):
    conexao.execute("INSERT INTO concursos (numero, data_apuracao, valor_arrecadado) VALUES (?, ?, ?)", (numero, data, arrecadacao))
    for i, (resultado, situacao) in enumerate(resultados, start=1):
        conexao.execute(
            "INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, resultado, situacao) VALUES (?, ?, 1, 2, ?, ?)",
            (numero, i, resultado, situacao),
        )
    if ganhadores is not None:
        conexao.execute(
            "INSERT INTO premiacoes (concurso_numero, faixa, pontos, ganhadores, valor_premio) VALUES (?, 1, 14, ?, ?)",
            (numero, ganhadores, premio),
        )


def _normais(*resultados):
    return [(r, "normal") for r in resultados]


def test_carrega_concurso_util_e_conta_o_que_ficou_de_fora_e_por_que(conexao):
    _concurso(conexao, 1, _normais(*["1"] * 8, *["X"] * 3, *["2"] * 3))  # útil
    _concurso(conexao, 2, _normais(*["1"] * 13))  # 13 jogos
    _concurso(conexao, 3, _normais(*["1"] * 13) + [("X", "sorteio")])  # um jogo decidido por sorteio
    _concurso(conexao, 4, _normais(*["1"] * 14), arrecadacao=0.0)  # sem arrecadação
    _concurso(conexao, 5, _normais(*["1"] * 14), ganhadores=None)  # sem a faixa de 14
    _concurso(conexao, 6, _normais(*["1"] * 13) + [(None, "normal")])  # jogo ainda sem resultado
    uteis, fora = anti_manada.carregar_concursos(conexao)
    assert [c["numero"] for c in uteis] == [1]
    u = uteis[0]
    assert (u["fora_da_coluna_1"], u["empates"], u["visitantes"], u["ano"]) == (6, 3, 3, 2024)
    assert u["ganhadores_por_milhao"] == pytest.approx(2.0)
    assert fora == {"sem_14_jogos_apurados": 2, "jogo_decidido_por_sorteio": 1, "sem_arrecadacao": 1, "sem_ganhadores_14": 1}


def test_conta_anterior_pearson_se_perde_nos_valores_extremos_e_spearman_nao(conexao):
    # 30 concursos: mais jogos fora da coluna 1 => menos ganhadores, mas um concurso com 700 ganhadores
    # (poucos fora da coluna 1) domina a correlação de Pearson sobre o número bruto
    for n in range(30):
        fora = n % 15
        resultados = _normais(*(["1"] * (14 - fora) + ["X"] * fora))
        _concurso(conexao, n + 1, resultados, ganhadores=max(0, 20 - 2 * fora) + (700 if n == 0 else 0))
    resumo = anti_manada.conta_anterior(conexao)
    assert resumo["n"] == 30
    assert resumo["spearman"] < -0.8  # a relação existe em quase todos os concursos
    assert resumo["pearson"] > resumo["spearman"] + 0.3  # o valor extremo enfraquece o Pearson


def test_conta_anterior_sem_concursos_ou_sem_variacao_devolve_none(conexao):
    assert anti_manada.conta_anterior(conexao) is None
    for n in range(5):
        _concurso(conexao, n + 1, _normais(*["1"] * 14), ganhadores=3)  # nunca há jogo fora da coluna 1
    assert anti_manada.conta_anterior(conexao) is None


def test_sem_nenhum_concurso_nao_quebra(conexao):
    assert anti_manada.carregar_concursos(conexao)[0] == []
    resultados = anti_manada.estudar([])
    assert [r["conclusao"] for r in resultados] == ["amostra insuficiente"] * 3


def test_dificuldade_prevista_soma_a_surpresa_do_favorito_so_em_concurso_completo():
    # Item C5 do plano v2: dificuldade que o app enxergava antes do prazo.
    registros = [{"concurso": 1, "p": {"1": 50.0, "X": 30.0, "2": 20.0}} for _ in range(14)]
    registros += [{"concurso": 2, "p": {"1": 90.0, "X": 5.0, "2": 5.0}} for _ in range(13)]  # incompleto
    dificuldade = anti_manada.dificuldade_prevista(registros)
    assert list(dificuldade) == [1] and dificuldade[1] == pytest.approx(-14 * np.log(0.5))


def test_dificuldade_prevista_que_acompanha_os_ganhadores_e_detectada(monkeypatch):
    monkeypatch.setattr(config, "Q7_PERMUTACOES", 500)
    monkeypatch.setattr(config, "Q7_REPETICOES_BOOTSTRAP", 200)
    concursos = [{"numero": n, "ano": 2020 + n % 3, "ganhadores_por_milhao": 100.0 / n} for n in range(1, 61)]
    r = anti_manada.testar_dificuldade_prevista(concursos, {n: float(n) for n in range(1, 61)})
    assert r["rho"] < -0.9 and r["conclusao"] == "associação detectada (negativa)"


def test_postos_medios_com_empates():
    assert list(anti_manada.postos_medios(np.array([10.0, 20.0, 20.0, 30.0]))) == [1.0, 2.5, 2.5, 4.0]


def test_correlacao_simples_valores_conhecidos_e_casos_de_borda():
    assert anti_manada.correlacao_simples([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert anti_manada.correlacao_simples([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert anti_manada.correlacao_simples([1, 2], [1, 2]) is None  # amostra mínima
    assert anti_manada.correlacao_simples([1, 1, 1], [1, 2, 3]) is None  # sem variação


def _dados(rng, inclinacao, anos=10, por_ano=40, tendencia=0.0):
    x, y, ano = [], [], []
    for a in range(anos):
        for _ in range(por_ano):
            zebras = int(rng.integers(0, 15))
            x.append(zebras)
            y.append(max(0.0, 3.0 + tendencia * a + inclinacao * zebras + rng.normal(0, 1.0)))
            ano.append(2015 + a)
    return x, y, ano


def _correlacao(x, y, ano, semente=1, permutacoes=300, repeticoes=200):
    return anti_manada.correlacao_estratificada(x, y, ano, permutacoes, repeticoes, semente, 10)


def test_associacao_negativa_plantada_e_detectada_com_intervalo_que_exclui_zero():
    x, y, ano = _dados(np.random.default_rng(1), inclinacao=-0.15)
    r = _correlacao(x, y, ano)
    assert r["rho"] < -0.2 and r["p"] < 0.01 and r["ic_superior"] < 0


def test_sem_associacao_nao_vira_achado_acima_do_esperado():
    falsos = sum(
        _correlacao(*_dados(np.random.default_rng(100 + s), 0.0, anos=5), semente=s)["p"] < 0.05 for s in range(20)
    )
    assert falsos <= 3  # esperado: 1 em 20


def test_tendencia_de_epoca_nao_fabrica_correlacao():
    """x e y sobem com o ano, mas não têm relação dentro de cada ano: a correlação ingênua é alta, a estratificada não."""
    rng = np.random.default_rng(7)
    x, y, ano = [], [], []
    for a in range(10):
        for _ in range(40):
            x.append(a + int(rng.integers(0, 3)))
            y.append(2.0 * a + rng.normal(0, 1.0))
            ano.append(2015 + a)
    ingenua = np.corrcoef(anti_manada.postos_medios(np.array(x, float)), anti_manada.postos_medios(np.array(y)))[0, 1]
    estratificada = _correlacao(x, y, ano)
    assert ingenua > 0.5
    assert abs(estratificada["rho"]) < 0.15 and estratificada["p"] > 0.01


def test_ano_com_poucos_concursos_fica_fora_do_calculo():
    x, y, ano = _dados(np.random.default_rng(2), -0.1, anos=3, por_ano=30)
    pequeno_x, pequeno_y = [1, 2, 3, 4, 5], [5, 4, 3, 2, 1]  # 5 concursos num ano: abaixo do mínimo de 10
    r = _correlacao(x + pequeno_x, y + pequeno_y, ano + [2099] * 5)
    assert r["n"] == 90


def test_resultado_e_reprodutivel_e_serie_constante_nao_tem_correlacao():
    x, y, ano = _dados(np.random.default_rng(3), -0.1)
    assert _correlacao(x, y, ano, semente=5) == _correlacao(x, y, ano, semente=5)
    constante = _correlacao([3] * 50, list(range(50)), [2020] * 50)
    assert constante["rho"] is None and constante["p"] is None


def test_estudar_aplica_q_e_conclui(monkeypatch):
    monkeypatch.setattr(config, "Q7_PERMUTACOES", 300)
    monkeypatch.setattr(config, "Q7_REPETICOES_BOOTSTRAP", 200)
    rng = np.random.default_rng(11)
    concursos = []
    for a in range(8):
        for n in range(40):
            zebras = int(rng.integers(0, 15))
            concursos.append(
                {"numero": a * 100 + n, "ano": 2015 + a, "fora_da_coluna_1": zebras,
                 "empates": int(rng.integers(0, 8)), "visitantes": int(rng.integers(0, 8)),
                 "ganhadores_por_milhao": max(0.0, 3.0 - 0.2 * zebras + rng.normal(0, 1.0))}
            )
    por_chave = {r["exposicao"]: r for r in anti_manada.estudar(concursos)}
    assert por_chave["fora_da_coluna_1"]["conclusao"] == "associação detectada (negativa)"
    assert por_chave["empates"]["conclusao"] == "sem diferença perceptível"


def test_tabela_por_faixa_agrupa_e_ignora_faixa_vazia():
    concursos = [
        {"fora_da_coluna_1": 3, "ganhadores_por_milhao": 2.0, "ganhadores_14": 4, "premio_14": 1000.0},
        {"fora_da_coluna_1": 4, "ganhadores_por_milhao": 0.0, "ganhadores_14": 0, "premio_14": 0.0},
        {"fora_da_coluna_1": 10, "ganhadores_por_milhao": 0.5, "ganhadores_14": 1, "premio_14": 5000.0},
    ]
    tabela = {linha["faixa"]: linha for linha in anti_manada.tabela_por_faixa(concursos)}
    assert set(tabela) == {"0 a 4", "9 a 14"}  # faixas sem concurso não aparecem
    assert tabela["0 a 4"]["concursos"] == 2 and tabela["0 a 4"]["sem_ganhador_14"] == 50.0
    assert tabela["0 a 4"]["premio_mediano"] == 1000.0  # só onde houve ganhador

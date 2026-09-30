from stats.ano_em_curso import (
    aproveitamento, cobertura, desempenho_selecao_no_ano, diferenca_no_ano, frase_do_lado, _completar, _lado_vazio,
)

BASE = [
    {"data": "2025-11-10", "casa": "Spain", "fora": "Italy", "gols_casa": 3, "gols_fora": 0},
    {"data": "2026-03-01", "casa": "Spain", "fora": "Italy", "gols_casa": 2, "gols_fora": 1},
    {"data": "2026-03-05", "casa": "France", "fora": "Spain", "gols_casa": 1, "gols_fora": 1},
    {"data": "2026-06-20", "casa": "Brazil", "fora": "Spain", "gols_casa": 2, "gols_fora": 0},
]


def test_aproveitamento_e_sem_jogos():
    assert round(aproveitamento(7, 3), 6) == round(700 / 9, 6)
    assert aproveitamento(0, 0) is None


def test_selecao_conta_so_os_jogos_do_ano_e_dos_dois_mandos():
    d = desempenho_selecao_no_ano(BASE, "Spain", 2026)
    assert (d["jogos"], d["vitorias"], d["empates"], d["derrotas"]) == (3, 1, 1, 1)
    assert (d["gols_pro"], d["gols_contra"]) == (3, 4) and d["ultimos"] == ["V", "E", "D"]
    assert d["ultimo_jogo"] == "2026-06-20"


def test_selecao_sem_jogo_no_ano_devolve_none():
    assert desempenho_selecao_no_ano(BASE, "Italy", 2027) is None


def _lado(fonte, v, e, d):
    lado = _lado_vazio("X", 2026)
    lado.update(fonte=fonte, jogos=v + e + d, vitorias=v, empates=e, derrotas=d)
    return _completar(lado)


def test_diferenca_aponta_o_melhor_e_avisa_fontes_diferentes_e_amostra_pequena():
    casa, fora = _lado("cbf", 20, 5, 5), _lado("loteca", 1, 1, 2)
    d = diferenca_no_ano(casa, fora)
    assert d["melhor"] == "casa" and d["fontes_diferentes"] and d["amostra_pequena"]


def test_diferenca_sem_dado_de_um_lado_nao_compara():
    assert diferenca_no_ano(_lado("cbf", 1, 1, 1), _lado_vazio("Y", 2026)) is None


def test_cobertura_conta_por_fonte():
    resumo = [{"casa": _lado("cbf", 10, 0, 0), "fora": _lado_vazio("Y", 2026)},
              {"casa": _lado("selecoes", 1, 0, 0), "fora": _lado("loteca", 5, 0, 0)}]
    c = cobertura(resumo)
    assert (c["total"], c["com_dado"], c["cbf"], c["selecoes"], c["loteca"], c["sem_dado"], c["amostra_pequena"]) == (
        4, 3, 1, 1, 1, 1, 1)


def test_frase_do_lado_sem_dado_e_com_amostra_pequena():
    assert frase_do_lado(_lado_vazio("Y", 2026)) == "sem jogos de 2026 encontrados"
    assert "amostra pequena" in frase_do_lado(_lado("loteca", 1, 1, 0))

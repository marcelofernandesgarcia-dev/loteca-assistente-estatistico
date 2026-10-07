"""Testes de stats/contexto.py contra os números REAIS do REC (Regulamento
Específico da Competição) 2026, lidos em docs/fontes-oficiais/."""
import pytest

from stats.contexto import contexto_da_classificacao, selo_da_posicao, zona_da_posicao


@pytest.mark.parametrize(
    "posicao,zona_esperada",
    [(1, "libertadores_grupos"), (4, "libertadores_grupos"), (5, "libertadores_preliminar"),
     (6, "sul_americana"), (11, "sul_americana"), (12, "meio_de_tabela"), (16, "meio_de_tabela"),
     (17, "rebaixamento"), (20, "rebaixamento")],
)
def test_zonas_da_serie_a_2026_conforme_o_rec(posicao, zona_esperada):
    assert zona_da_posicao("serie-a", 2026, posicao) == zona_esperada


@pytest.mark.parametrize(
    "posicao,zona_esperada",
    [(1, "acesso_direto"), (2, "acesso_direto"), (3, "playoff_acesso"), (6, "playoff_acesso"),
     (7, "meio_de_tabela"), (16, "meio_de_tabela"), (17, "rebaixamento"), (20, "rebaixamento")],
)
def test_zonas_da_serie_b_2026_conforme_o_rec(posicao, zona_esperada):
    assert zona_da_posicao("serie-b", 2026, posicao) == zona_esperada


def test_serie_ou_ano_sem_cadastro_nao_inventa_zona():
    assert zona_da_posicao("serie-c", 2026, 1) is None
    assert zona_da_posicao("serie-a", 2027, 1) is None
    assert zona_da_posicao("serie-a", 2026, None) is None


def test_selo_da_posicao_devolve_texto_pronto():
    assert selo_da_posicao("serie-a", 2026, 1) == "Libertadores (fase de grupos)"
    assert selo_da_posicao("serie-b", 2026, 4) == "Playoff de acesso à Série A"
    assert selo_da_posicao("serie-c", 2026, 1) is None


def _classificacao_serie_a():
    # 20 times fictícios, pontos decrescentes, posições 1-20
    return [{"cod_time": p, "posicao": p, "pontos": 100 - p} for p in range(1, 21)]


def test_contexto_da_classificacao_traz_zona_e_distancia_ate_a_fronteira():
    contexto = contexto_da_classificacao("serie-a", 2026, _classificacao_serie_a())
    quinto = contexto[5]  # zona sozinha (libertadores_preliminar), únicos vizinhos são de outras zonas
    assert quinto["zona"] == "libertadores_preliminar"
    assert quinto["pontos_para_subir_de_zona"] == 1  # 1 ponto atrás do 4º
    assert quinto["pontos_para_cair_de_zona"] == 1   # 1 ponto à frente do 6º
    primeiro = contexto[1]
    assert primeiro["pontos_para_subir_de_zona"] is None  # não há vizinho acima
    ultimo = contexto[20]
    assert ultimo["pontos_para_cair_de_zona"] is None  # não há vizinho abaixo
    sexto = contexto[6]
    assert sexto["zona"] == "sul_americana" and sexto["pontos_para_subir_de_zona"] == 1


def test_mesma_zona_entre_vizinhos_nao_gera_distancia():
    contexto = contexto_da_classificacao("serie-a", 2026, _classificacao_serie_a())
    segundo = contexto[2]  # 1º, 2º e 3º estão todos em libertadores_grupos
    assert segundo["pontos_para_subir_de_zona"] is None
    assert segundo["pontos_para_cair_de_zona"] is None


def test_contexto_sem_zonas_cadastradas_devolve_none():
    assert contexto_da_classificacao("serie-c", 2026, _classificacao_serie_a()) is None


@pytest.mark.parametrize("fase, posicao, selo", [
    ("1ª Fase", 1, "Classificação para a 2ª fase"),      # REC Série C 2026, Art. 15
    ("1ª Fase", 8, "Classificação para a 2ª fase"),
    ("1ª Fase", 12, "Fora da classificação para a 2ª fase"),
    ("1ª Fase", 19, "Rebaixamento para a Série D"),       # Art. 42
    ("2ª Fase", 1, "Acesso à Série B e vaga na final"),   # Arts. 5 e 19
    ("2ª Fase", 2, "Acesso à Série B"),                   # Art. 5
    ("2ª Fase", 3, "Fora da zona de acesso"),
])
def test_zonas_da_serie_c_2026_por_fase_conforme_o_rec(fase, posicao, selo):
    assert selo_da_posicao("serie-c", 2026, posicao, fase) == selo


def test_fase_sem_cadastro_nao_inventa_zona():
    assert selo_da_posicao("serie-c", 2026, 1, "3ª Fase") is None
    assert selo_da_posicao("serie-c", 2025, 1, "2ª Fase") is None

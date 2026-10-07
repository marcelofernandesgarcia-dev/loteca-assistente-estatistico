"""Cobertura de dados por jogo (item A2 do plano v2, 07/10/2026)."""
import datetime as dt

from stats.cobertura import cbf_do_lado, cobertura_do_jogo

AGORA = dt.datetime(2026, 10, 10, 9, 0)


def _lado(nome, cbf="pontos_corridos", tipo="clube", jogos=20, noticias="2026-10-10T08:00:00"):
    return {"nome": nome, "tipo": tipo, "cbf": cbf, "jogos_no_ano": jogos, "ano": 2026, "noticias_em": noticias}


def test_dois_times_da_serie_a_com_noticias_do_dia_tem_cobertura_completa_sem_faltas():
    c = cobertura_do_jogo(_lado("FLAMENGO"), _lado("FLUMINENSE"), "poisson", AGORA)
    assert c == {"nivel": "completa", "nome_nivel": "Completa (temporada da CBF)", "faltas": [], "alta_incerteza": False}


def test_serie_c_e_parcial_com_alta_incerteza_e_diz_por_que():
    c = cobertura_do_jogo(_lado("SANTA CRUZ", "com_fases"), _lado("MARINGA", "com_fases"), "poisson", AGORA)
    assert c["nivel"] == "parcial" and c["alta_incerteza"]
    assert "SANTA CRUZ: competição com fases (Série C), tabela da CBF só da fase atual" in c["faltas"]


def test_clube_sem_cbf_e_parcial():
    c = cobertura_do_jogo(_lado("REAL MADRID", None, jogos=3), _lado("VILLARREAL", None, jogos=2), "poisson", AGORA)
    assert c["nivel"] == "parcial"
    assert "REAL MADRID: sem dados da CBF na temporada, só os jogos que caíram na Loteca" in c["faltas"]
    assert "VILLARREAL: 2 jogo(s) encontrados em 2026" in c["faltas"]


def test_selecoes_pelo_elo_nao_sao_alta_incerteza_e_nao_cobram_cbf():
    c = cobertura_do_jogo(_lado("ESPANHA", None, "selecao", 8), _lado("ITALIA", None, "selecao", 8), "elo_selecoes", AGORA)
    assert c["nivel"] == "selecoes" and not c["alta_incerteza"] and c["faltas"] == []


def test_sem_base_propria_e_baixa_mesmo_com_cbf():
    c = cobertura_do_jogo(_lado("ALFA"), _lado("BETA"), "frequencia_global", AGORA)
    assert c["nivel"] == "baixa" and c["alta_incerteza"]


def test_noticias_ausentes_ou_velhas_entram_nas_faltas_sem_mudar_o_nivel():
    c = cobertura_do_jogo(_lado("ALFA", noticias=None), _lado("BETA", noticias="2026-10-06T08:00:00"), "poisson", AGORA)
    assert c["nivel"] == "completa"
    assert c["faltas"] == ["ALFA: notícias não lidas para este concurso", "BETA: notícias lidas há 4 dias"]


def test_cbf_do_lado():
    assert cbf_do_lado(None) is None
    assert cbf_do_lado({"serie": "serie-a", "fase": None}) == "pontos_corridos"
    assert cbf_do_lado({"serie": "serie-c", "fase": "2ª Fase"}) == "com_fases"
    assert cbf_do_lado({"serie": "serie-c", "fase": None}) == "com_fases"  # série fora dos pontos corridos

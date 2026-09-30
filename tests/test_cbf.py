"""Testes da leitura da CBF com páginas SINTÉTICAS montadas aqui (nomes
fictícios) -- nenhum conteúdo do site da CBF é guardado no repositório."""
import json
import sqlite3

import pytest

import db
from importer.cbf_client import (
    ErroColetaCBF,
    data_iso,
    gravar_classificacao,
    gravar_pagina_time,
    parse_classificacao,
    parse_pagina_time,
)
from importer.cbf_mapeamento import parear, tokens
from stats.cbf import (
    classificacao_do_participante,
    instrucao_consulta_bid,
    codigos_equivalentes,
    historico_saf_na_cbf,
    partidas_do_participante,
    registrado_como_saf,
    resumo_curto_cbf,
)


def _html(texto_fluxo: str) -> str:
    escapado = json.dumps(texto_fluxo)[1:-1]
    return f'<html><script>self.__next_f.push([1,"{escapado}"])</script></html>'


CLASSIFICACAO = [
    {"cod_time": "100", "uf_time": "SP", "time": "Time Alfa SAF", "posicao": "1", "pontos": "54", "jogos": "30",
     "vitorias": "16", "empates": "6", "derrotas": "8", "gols_pro": "43", "gols_contra": "31", "gols_saldo": "+12",
     "cartoes_vermelho": "8", "cartoes_amarelo": "77", "aproveitamento": "60", "rodada": "30",
     "ultimos_jogos": ["E", "V", "V"], "proximo_jogo": {"id": "200", "time": "Time Beta"}},
    {"cod_time": "200", "uf_time": "RJ", "time": "Time Beta", "posicao": "2", "pontos": "50", "jogos": "30",
     "vitorias": "15", "empates": "5", "derrotas": "10", "gols_pro": "40", "gols_contra": "35", "gols_saldo": "5",
     "cartoes_vermelho": "2", "cartoes_amarelo": "60", "aproveitamento": "55", "rodada": "30",
     "ultimos_jogos": ["D", "V", "E"], "proximo_jogo": {"id": "100", "time": "Time Alfa SAF"}},
]

ESTATISTICAS = {"gols_feitos": "43", "gols_sofridos": "31", "jogos_sem_sofrer_gol": "11",
                "jogos_disputados": "30", "vitorias": "16", "derrotas": "8", "empates": "6",
                "cartoes_amarelos": "77", "cartoes_vermelhos": "8"}

# formato já interpretado por parse_pagina_time (estatisticas = dict)
PAGINA_TIME = {
    "estatisticas": ESTATISTICAS,
    "jogos": [
        {"id_jogo": "1", "rodada": "29", "mandante": {"id": "100", "nome": "Time Alfa SAF", "gols": "1", "panaltis": "0"},
         "visitante": {"id": "200", "nome": "Time Beta", "gols": "0", "panaltis": "0"},
         "local": "Estádio Teste - Cidade - SP", "data": " 20/09/2026", "hora": "16:00"},
        {"id_jogo": "2", "rodada": "31", "mandante": {"id": "200", "nome": "Time Beta", "gols": "", "panaltis": ""},
         "visitante": {"id": "100", "nome": "Time Alfa SAF", "gols": "", "panaltis": ""},
         "local": "Outro Estádio - RJ", "data": " 04/10/2026", "hora": "19:00"},
    ],
}


@pytest.fixture()
def conexao():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(db.SCHEMA)
    return c


def test_parse_classificacao_le_a_tabela_embutida():
    html = _html("prefixo," + '"data":' + json.dumps(CLASSIFICACAO) + ",sufixo")
    linhas = parse_classificacao(html)
    assert [x["time"] for x in linhas] == ["Time Alfa SAF", "Time Beta"]


def test_parse_classificacao_sem_tabela_levanta_erro_claro():
    with pytest.raises(ErroColetaCBF):
        parse_classificacao(_html("página sem tabela"))


def test_pagina_sem_fluxo_levanta_erro_claro():
    with pytest.raises(ErroColetaCBF, match="site pode ter mudado"):
        parse_pagina_time("<html>nada</html>")


def test_parse_pagina_time_le_estatisticas_e_jogos():
    html = _html('"estatisticas":' + json.dumps([ESTATISTICAS]) + ',"jogos":' + json.dumps(PAGINA_TIME["jogos"]))
    dados = parse_pagina_time(html)
    assert dados["estatisticas"]["jogos_sem_sofrer_gol"] == "11"
    assert len(dados["jogos"]) == 2


def test_data_iso():
    assert data_iso(" 25/09/2026") == "2026-09-25"
    assert data_iso("") is None
    assert data_iso("lixo") is None


def test_gravar_e_consultar(conexao):
    participante = db.obter_ou_criar_participante(conexao, "TIME ALFA", "clube", "SP")
    gravar_classificacao(conexao, "serie-b", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    gravar_pagina_time(conexao, "serie-b", 2026, 100, PAGINA_TIME, "2026-09-27T10:00:00")
    resultado = parear(conexao)
    assert resultado["pareados"] == 1

    classif = classificacao_do_participante(conexao, participante)
    assert classif["posicao"] == 1 and classif["pontos"] == 54 and classif["saldo"] == 12
    assert classif["ultimos_jogos"] == "E,V,V"
    assert resumo_curto_cbf(classif) == "CBF: 1º · 60% aprov. · E V V"

    partidas = partidas_do_participante(conexao, participante)
    assert [p["rodada"] for p in partidas] == [31, 29]  # mais recente primeiro
    futura, passada = partidas
    assert futura["realizada"] is False and futura["gols_feitos"] is None
    assert passada["mando"] == "casa" and (passada["gols_feitos"], passada["gols_sofridos"]) == (1, 0)


@pytest.mark.parametrize(
    "nome",
    [
        "Coritiba SAF", "Vasco da Gama Saf", "Athletic SAF", "Atlético Goianiense Saf", "Fortaleza SAF",
        "Gremio Novorizontino - Saf", "Londrina SAF", "São Bernardo SAF",  # os 8 nomes reais da CBF em 30/09/2026
        "Time X S.A.F.", "Time X S.A.F",
    ],
)
def test_marca_saf_quando_o_nome_da_cbf_traz_saf(nome):
    assert registrado_como_saf(nome) is True


@pytest.mark.parametrize(
    "nome",
    ["Sport Recife", "Botafogo", "Cruzeiro", "Bahia", "Safira EC", "Casafe FC", "Ceará", "", None],
)
def test_sem_saf_no_nome_nao_marca_e_nao_afirma_o_contrario(nome):
    """Ausência do sufixo não prova que o clube não seja SAF (Botafogo, Cruzeiro e
    Bahia são apontados como SAF em fontes externas): a função só devolve True
    quando o nome mostra, e a tela não escreve 'não é SAF' em lugar nenhum."""
    assert registrado_como_saf(nome) is False


def _classificar(conexao, cod, nomes_por_ano):
    """Grava uma linha de classificação por ano, com o nome que o time tinha naquele ano."""
    conexao.execute("INSERT OR IGNORE INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, 'SP')", (cod, nomes_por_ano[max(nomes_por_ano)] or "x"))
    for ano, nome in nomes_por_ano.items():
        conexao.execute(
            "INSERT INTO cbf_classificacao (serie, ano, cod_time, rodada, coletado_em, nome_no_ano)"
            " VALUES ('serie-a', ?, ?, 38, 'x', ?)", (ano, cod, nome),
        )


def test_historico_saf_continuo_ate_hoje(conexao):
    _classificar(conexao, 1, {2019: "Time", 2022: "Time S.a.f.", 2023: "Time S.a.f.", 2024: "Time SAF"})
    saf = historico_saf_na_cbf(conexao, 1)
    assert (saf["desde"], saf["hoje"], saf["continuo_ate_hoje"]) == (2022, True, True)
    assert saf["texto_anos"] == "2022 a 2024" and saf["primeiro_ano_coletado"] == 2019


def test_historico_saf_que_some_do_nome_de_hoje_nao_e_continuo(conexao):
    """Como o Cruzeiro: 'Saf' no nome de 2022 a 2025, mas o nome de 2026 não traz."""
    _classificar(conexao, 2, {2021: "Time", 2022: "Time Saf", 2023: "Time Saf", 2025: "Time Saf", 2026: None})
    conexao.execute("UPDATE cbf_times SET nome = 'Time' WHERE cod_time = 2")  # nome atual, sem SAF
    saf = historico_saf_na_cbf(conexao, 2)
    assert saf["anos"] == [2022, 2023, 2025] and saf["texto_anos"] == "2022 a 2023 e 2025"
    assert saf["hoje"] is False and saf["continuo_ate_hoje"] is False


def test_historico_saf_usa_o_nome_atual_na_temporada_mais_recente_sem_nome_guardado(conexao):
    _classificar(conexao, 3, {2025: "Time", 2026: None})
    conexao.execute("UPDATE cbf_times SET nome = 'Time SAF' WHERE cod_time = 3")
    saf = historico_saf_na_cbf(conexao, 3)
    assert saf["anos"] == [2026] and saf["hoje"] is True and saf["continuo_ate_hoje"] is True


def test_historico_saf_com_lacuna_mostra_os_anos_e_nao_afirma_desde(conexao):
    """Como o Cuiabá: 'Saf' em 2019, sem em 2020 e 2021, com de 2022 em diante."""
    _classificar(conexao, 4, {2019: "T Saf", 2020: "T", 2021: "T", 2022: "T Saf", 2023: "T Saf"})
    saf = historico_saf_na_cbf(conexao, 4)
    assert saf["texto_anos"] == "2019 e 2022 a 2023" and saf["hoje"] is True
    assert saf["continuo_ate_hoje"] is False  # tem ano sem SAF no meio: "desde 2019" seria falso


def test_historico_saf_sem_saf_no_nome_ou_sem_dados_e_none(conexao):
    _classificar(conexao, 5, {2025: "Time", 2026: "Time"})
    assert historico_saf_na_cbf(conexao, 5) is None  # ausência não prova nada: não afirma
    assert historico_saf_na_cbf(conexao, 999) is None and historico_saf_na_cbf(conexao, None) is None


def test_faixas_de_anos():
    from stats.cbf import _faixas_de_anos

    assert _faixas_de_anos([2019, 2022, 2023, 2024]) == "2019 e 2022 a 2024"
    assert _faixas_de_anos([2026]) == "2026" and _faixas_de_anos([2022, 2023]) == "2022 a 2023"


def test_codigos_equivalentes_le_so_as_linhas_validadas(tmp_path):
    arquivo = tmp_path / "eq.csv"
    arquivo.write_text(
        "# comentário\n"
        "cod_atual;cod_anterior;clube;uf;anos_anterior;anos_atual;nome_anterior;nome_atual;status\n"
        "60646;20012;Vasco;RJ;2019-2021;2022-2026;a;b;validado\n"
        "61590;20025;Coritiba;PR;2019-2022;2023-2026;a;b;proposto\n"
        "60646;99999;Vasco;RJ;2000;2001;a;b;validado\n",
        encoding="utf-8",
    )
    assert codigos_equivalentes(str(arquivo)) == {60646: [20012, 99999]}  # a linha "proposto" fica de fora
    assert codigos_equivalentes(str(tmp_path / "nao-existe.csv")) == {}


def test_tabela_real_de_codigos_esta_validada_e_os_codigos_existem_no_banco_sintetico_de_nomes():
    equivalentes = codigos_equivalentes()
    assert len(equivalentes) == 11 and equivalentes[60646] == [20012] and equivalentes[62261] == [20093]
    todos = {c for cods in equivalentes.values() for c in cods} | set(equivalentes)
    assert len(todos) == 22  # 11 pares, nenhum código repetido


def test_instrucao_do_bid_usa_o_codigo_da_cbf_e_a_uf():
    # O código da CBF é o mesmo da lista do BID (Ceará: 20031, conferido em 30/09/2026).
    assert instrucao_consulta_bid(20031, "CE") == (
        "escolha uma data, a UF CE e o clube de código 20031 "
        "(o código aparece entre parênteses no fim do nome do clube)"
    )
    assert instrucao_consulta_bid(20031, None) is None and instrucao_consulta_bid(None, "CE") is None


def _antiga(nome_alfa="Time Alfa"):
    """A mesma classificação numa temporada passada, com o nome antigo do time 100."""
    linhas = [dict(l) for l in CLASSIFICACAO]
    linhas[0]["time"] = nome_alfa
    return linhas


def test_temporada_antiga_nao_sobrescreve_o_nome_atual_do_time(conexao):
    """Coletar 2019 depois de 2026 não pode trocar 'Time Alfa SAF' por 'Time Alfa'."""
    gravar_classificacao(conexao, "serie-a", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    gravar_classificacao(conexao, "serie-a", 2019, _antiga(), "2026-09-30T10:00:00")
    assert conexao.execute("SELECT nome FROM cbf_times WHERE cod_time = 100").fetchone()[0] == "Time Alfa SAF"
    nomes = dict(conexao.execute("SELECT ano, nome_no_ano FROM cbf_classificacao WHERE cod_time = 100").fetchall())
    assert nomes == {2026: "Time Alfa SAF", 2019: "Time Alfa"}  # o nome de cada temporada fica guardado


@pytest.mark.parametrize("proximo_jogo", [["nenhum"], [], None])
def test_temporada_encerrada_sem_proximo_jogo_grava_sem_erro(conexao, proximo_jogo):
    """Na CBF, temporada encerrada traz `proximo_jogo` como lista (["nenhum"]), não como objeto."""
    linhas = [dict(l, proximo_jogo=proximo_jogo) for l in CLASSIFICACAO]
    gravar_classificacao(conexao, "serie-a", 2019, linhas, "2026-09-30T10:00:00")
    linha = conexao.execute("SELECT proximo_adversario, proximo_adversario_id FROM cbf_classificacao WHERE ano = 2019").fetchone()
    assert (linha["proximo_adversario"], linha["proximo_adversario_id"]) == (None, None)


def test_time_novo_de_temporada_antiga_entra_com_o_nome_daquele_ano(conexao):
    gravar_classificacao(conexao, "serie-a", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    extra = [dict(CLASSIFICACAO[0], cod_time="300", time="Time Gama", uf_time="MG")]
    gravar_classificacao(conexao, "serie-a", 2019, extra, "2026-09-30T10:00:00")
    assert conexao.execute("SELECT nome FROM cbf_times WHERE cod_time = 300").fetchone()[0] == "Time Gama"


def test_temporada_mais_recente_continua_atualizando_o_nome_atual(conexao):
    gravar_classificacao(conexao, "serie-a", 2025, _antiga(), "2025-12-10T10:00:00")
    gravar_classificacao(conexao, "serie-a", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    assert conexao.execute("SELECT nome FROM cbf_times WHERE cod_time = 100").fetchone()[0] == "Time Alfa SAF"
    gravar_classificacao(conexao, "serie-a", 2026, _antiga("Time Alfa Renomeado"), "2026-10-05T10:00:00")  # nova coleta de 2026
    assert conexao.execute("SELECT nome FROM cbf_times WHERE cod_time = 100").fetchone()[0] == "Time Alfa Renomeado"


def test_preencher_nome_so_na_temporada_mais_recente(conexao):
    from importer.cbf_client import preencher_nome_do_ano_mais_recente

    gravar_classificacao(conexao, "serie-a", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    gravar_classificacao(conexao, "serie-a", 2019, _antiga(), "2026-09-30T10:00:00")
    conexao.execute("UPDATE cbf_classificacao SET nome_no_ano = NULL")  # como estava antes da coluna existir
    assert preencher_nome_do_ano_mais_recente(conexao) == 2  # só as 2 linhas de 2026
    nomes = {(a, c): n for a, c, n in conexao.execute("SELECT ano, cod_time, nome_no_ano FROM cbf_classificacao")}
    assert nomes[(2026, 100)] == "Time Alfa SAF" and nomes[(2019, 100)] is None  # 2019 fica sem nome: não dá para saber


def test_diferenca_so_de_gols_nao_invalida_a_temporada_mas_jogo_ou_ponto_diferente_sim():
    from importer.cbf_client import divergencias_de_resultado

    so_gols = {"divergencias_numeros": [{"cod_time": 1, "campo": "gols_pro", "reconstruido": 45, "cbf": 44}]}
    assert divergencias_de_resultado(so_gols) == []
    grave = {"divergencias_numeros": [
        {"cod_time": 1, "campo": "gols_pro", "reconstruido": 45, "cbf": 44},
        {"cod_time": 2, "campo": "pontos", "reconstruido": 50, "cbf": 47},
        {"cod_time": 3, "campo": "jogos", "reconstruido": 37, "cbf": 38},
        {"cod_time": 4, "motivo": "time sem jogos na base"},
    ]}
    assert [d["cod_time"] for d in divergencias_de_resultado(grave)] == [2, 3, 4]


def test_anomalia_conhecida_aceita_o_numero_de_jogos_que_a_cbf_publica(conexao, monkeypatch):
    """Série B 2023 tem 379 de 380 jogos nas páginas da CBF (a tabela conta o que falta):
    conta como completa porque a anomalia foi entendida e registrada, sem inventar o jogo."""
    from importer.cbf_client import temporada_completa

    monkeypatch.setattr("config.CBF_JOGOS_TEMPORADA_COMPLETA", 2)
    monkeypatch.setattr("config.CBF_ANOMALIAS_CONHECIDAS", {("serie-a", 2019): {"jogos_faltando": 1, "descricao": "x"}})
    assert temporada_completa(conexao, "serie-a", 2019) is False  # 0 jogos: nem o mínimo da anomalia (1)
    gravar_pagina_time(conexao, "serie-a", 2019, 100, PAGINA_TIME, "2026-09-30T10:00:00")  # 1 jogo com placar
    assert temporada_completa(conexao, "serie-a", 2019) is True
    assert temporada_completa(conexao, "serie-b", 2019) is False  # sem anomalia registrada, continua exigindo 2


def test_temporada_completa_exige_380_jogos_e_tabela_que_confere(conexao, monkeypatch):
    from importer.cbf_client import temporada_completa

    monkeypatch.setattr("config.CBF_JOGOS_TEMPORADA_COMPLETA", 2)
    assert temporada_completa(conexao, "serie-a", 2019) is False  # nada coletado
    gravar_pagina_time(conexao, "serie-a", 2019, 100, PAGINA_TIME, "2026-09-30T10:00:00")
    assert temporada_completa(conexao, "serie-a", 2019) is False  # só 1 jogo com placar (o outro é futuro)


def test_gravar_duas_vezes_nao_duplica(conexao):
    for _ in range(2):
        gravar_classificacao(conexao, "serie-b", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
        gravar_pagina_time(conexao, "serie-b", 2026, 100, PAGINA_TIME, "2026-09-27T10:00:00")
    assert conexao.execute("SELECT COUNT(*) FROM cbf_classificacao").fetchone()[0] == 2
    assert conexao.execute("SELECT COUNT(*) FROM cbf_partidas").fetchone()[0] == 2


def test_tokens_ignoram_acento_e_saf():
    assert tokens("Atlético Goianiense Saf") == frozenset({"ATLETICO", "GOIANIENSE"})
    assert tokens("VASCO DA GAMA") == frozenset({"VASCO", "GAMA"})


def _cbf(conexao, cod, nome, uf):
    conexao.execute("INSERT INTO cbf_times (cod_time, nome, uf) VALUES (?, ?, ?)", (cod, nome, uf))


def test_pareamento_usa_uf_para_separar_homonimos(conexao):
    _cbf(conexao, 1, "Botafogo", "RJ")
    _cbf(conexao, 2, "Botafogo", "SP")
    rj = db.obter_ou_criar_participante(conexao, "BOTAFOGO", "clube", "RJ")
    sp = db.obter_ou_criar_participante(conexao, "BOTAFOGO", "clube", "SP")
    parear(conexao)
    mapa = {r["participante_id"]: r["cod_time"] for r in conexao.execute("SELECT * FROM mapa_cbf_participante")}
    assert mapa == {rj: 1, sp: 2}


def test_pareamento_nomes_diferentes_da_cbf(conexao):
    _cbf(conexao, 1, "Red Bull Bragantino", "SP")
    _cbf(conexao, 2, "Athletic SAF", "MG")
    _cbf(conexao, 3, "Atlético Mineiro", "MG")
    bragantino = db.obter_ou_criar_participante(conexao, "BRAGANTINO", "clube", "SP")
    athletic = db.obter_ou_criar_participante(conexao, "ATHLETIC CLUB", "clube", "MG")
    atletico = db.obter_ou_criar_participante(conexao, "ATLETICO", "clube", "MG")
    parear(conexao)
    mapa = {r["participante_id"]: r["cod_time"] for r in conexao.execute("SELECT * FROM mapa_cbf_participante")}
    assert mapa == {bragantino: 1, athletic: 2, atletico: 3}


def test_pareamento_ambiguo_nao_adivinha(conexao):
    _cbf(conexao, 1, "Time Alfa Norte", "SP")
    _cbf(conexao, 2, "Time Alfa Sul", "SP")
    db.obter_ou_criar_participante(conexao, "TIME ALFA", "clube", "SP")
    resultado = parear(conexao)
    assert resultado["pareados"] == 0
    assert len(resultado["ambiguos"]) == 1
    assert conexao.execute("SELECT COUNT(*) FROM mapa_cbf_participante").fetchone()[0] == 0


def test_estrangeiro_e_selecao_nao_pareiam(conexao):
    _cbf(conexao, 1, "Barcelona", "SP")
    db.obter_ou_criar_participante(conexao, "BARCELONA", "clube", "ESP")
    db.obter_ou_criar_participante(conexao, "ALEMANHA", "selecao", "GER")
    assert parear(conexao)["pareados"] == 0


def test_classificacao_guarda_o_codigo_do_proximo_adversario(conexao):
    gravar_classificacao(conexao, "serie-a", 2026, CLASSIFICACAO, "2026-09-27T10:00:00")
    linha = conexao.execute(
        "SELECT proximo_adversario, proximo_adversario_id FROM cbf_classificacao WHERE cod_time = 100"
    ).fetchone()
    assert (linha["proximo_adversario"], linha["proximo_adversario_id"]) == ("Time Beta", 200)

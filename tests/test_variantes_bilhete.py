"""Bilhetes alternativos a partir do volante (08/10/2026): contas sobre percentuais SINTÉTICOS e banco temporário."""
import pytest

import config
import db
from stats import variantes_bilhete as vb
from stats.bilhetes_salvos import bilhete_igual, conferir_bilhete, salvar_bilhete

PCTS = [
    {"1": 70, "X": 20, "2": 10},  # favorito forte
    {"1": 40, "X": 30, "2": 30},
    {"1": 50, "X": 30, "2": 20},
    {"1": 34, "X": 33, "2": 33},  # o mais incerto
]
NUMEROS = [1, 2, 3, 4]


def _apostas(marcacoes):
    total = 1
    for m in marcacoes:
        total *= len(m)
    return total


def test_tres_tipos_respeitam_custo_e_nao_se_repetem():
    # Triplo desperdiçado no favorito forte e o jogo 2 marcado contra o favorito.
    base = [["1", "X", "2"], ["2"], ["1"], ["1"]]
    r = vb.gerar_variantes(PCTS, base, NUMEROS)
    por_tipo = {v["tipo"]: v for v in r["variantes"]}

    leve = por_tipo["ajuste_leve"]
    assert leve["marcacoes"] == [["1"], ["1"], ["1"], ["1", "X", "2"]]  # leva o triplo e desfaz o "contra o favorito"
    assert len(leve["passos"]) == 2 and leve["economia"] == 0
    assert leve["medidas"]["chance_14"] > r["base"]["chance_14"]
    assert [m["num_jogo"] for m in leve["mudancas"]] == [1, 2, 4]

    # A regra do app chega ao mesmo bilhete: não aparece duas vezes.
    assert "reorganizado" not in por_tipo
    assert {"tipo": "reorganizado", "motivo": "sairia igual ao bilhete “Ajuste leve”"} in r["sem_variante"]

    eco = por_tipo["economico"]
    assert eco["marcacoes"][0] == ["1", "X"] and eco["economia"] == pytest.approx(2.0)
    for v in r["variantes"]:
        assert _apostas(v["marcacoes"]) <= _apostas(base)
        assert sum(len(m) > 1 for m in v["marcacoes"]) <= sum(len(m) > 1 for m in base)


def test_bilhete_ja_organizado_nao_gera_variante_inventada():
    base = [["1"], ["1"], ["1"], ["1", "X"]]  # a própria regra do app com um duplo
    r = vb.gerar_variantes(PCTS, base, NUMEROS)
    assert r["variantes"] == []
    motivos = {s["tipo"]: s["motivo"] for s in r["sem_variante"]}
    assert "já estão onde a regra do app" in motivos["reorganizado"]
    assert "exige ao menos um duplo" in motivos["economico"]
    assert "nenhuma troca" in motivos["ajuste_leve"]


def test_reorganizado_mantem_quantidade_de_duplos_e_triplos():
    base = [["1", "X"], ["1"], ["1", "X"], ["1"]]  # duplos nos jogos errados
    r = vb.gerar_variantes(PCTS, base, NUMEROS)
    reorganizado = next(v for v in r["variantes"] if v["tipo"] == "reorganizado")
    assert sorted(len(m) for m in reorganizado["marcacoes"]) == sorted(len(m) for m in base)
    assert reorganizado["marcacoes"][3] != ["1"] and reorganizado["marcacoes"][1] != ["1"]  # vão para os jogos 2 e 4


def test_aviso_de_mais_favoritos_compara_com_a_base():
    base = [["X"], ["2"], ["2"], ["1", "X"]]  # nenhum seco no favorito
    r = vb.gerar_variantes(PCTS, base, NUMEROS)
    assert r["base"]["favoritos_secos"] == 0
    leve = next(v for v in r["variantes"] if v["tipo"] == "ajuste_leve")
    assert leve["favoritos_secos"] > 0 and leve["mais_favoritos_que_a_base"]


@pytest.mark.parametrize("base, trecho", [
    ([["1"], [], ["1"], ["1", "X"]], "Marque todos os jogos"),
    ([["1"], ["1"], ["1"]], "Marque todos os jogos"),  # tamanho diferente dos percentuais
])
def test_bilhete_de_partida_invalido_e_recusado(base, trecho):
    with pytest.raises(ValueError, match=trecho):
        vb.gerar_variantes(PCTS, base, NUMEROS)


def test_bilhete_acima_do_maximo_oficial_e_recusado(monkeypatch):
    monkeypatch.setattr(config, "BILHETE_MAX_APOSTAS", 4)
    with pytest.raises(ValueError, match="máximo oficial"):
        vb.gerar_variantes(PCTS, [["1", "X", "2"], ["1", "X"], ["1"], ["1"]], NUMEROS)


def test_comparar_com_a_base():
    resultados = {10: "1", 11: "X"}
    assert vb.comparar_com_a_base({10: ["1"], 11: ["1"]}, {10: ["1"], 11: ["X"]}, resultados) == {
        "acertos_base": 1, "acertos_variante": 2, "saldo": 1}
    assert vb.comparar_com_a_base({10: ["1"]}, {10: ["1"]}, {10: None}) is None


def test_nome_da_origem_trata_bilhete_antigo_como_volante():
    assert vb.nome_da_origem(None) == "Seu volante" and vb.nome_da_origem("economico") == "Econômico"


# --- Banco: origem, bilhete igual e leitura depois do resultado ---

@pytest.fixture()
def conexao(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "variantes.db")
    db.inicializar_schema()
    with db.sessao() as c:
        a = db.obter_ou_criar_participante(c, "ALFA", "clube", "SP")
        b = db.obter_ou_criar_participante(c, "BETA", "clube", "RJ")
        c.execute("INSERT INTO concursos (numero, data_limite_aposta) VALUES (9100, '2099-01-01')")
        for num in (1, 2):
            c.execute("INSERT INTO jogos (concurso_numero, num_jogo, casa_id, fora_id, data_jogo) VALUES (9100, ?, ?, ?, '2099-01-02')",
                      (num, a, b))
        ids = [r[0] for r in c.execute("SELECT id FROM jogos ORDER BY num_jogo")]
        yield c, ids


def test_salvar_variante_grava_origem_e_base_e_le_depois_do_resultado(conexao):
    c, (j1, j2) = conexao
    pct = {j1: {"1": 50, "X": 30, "2": 20}, j2: {"1": 50, "X": 30, "2": 20}}
    base = {j1: ["2"], j2: ["1", "X"]}
    variante = {j1: ["1"], j2: ["1", "X"]}
    bilhete = salvar_bilhete(c, 9100, variante, pct, origem="ajuste_leve", marcacoes_base=base)
    linha = c.execute("SELECT origem, marcacoes_base, custo FROM bilhetes WHERE id = ?", (bilhete,)).fetchone()
    assert linha["origem"] == "ajuste_leve" and vb.ler_marcacoes_base(linha["marcacoes_base"]) == base
    assert linha["custo"] == pytest.approx(4.0)

    assert vb.leituras_das_variantes(c) == []  # sem resultado ainda
    c.execute("UPDATE jogos SET resultado = '1'")
    conferir_bilhete(c, bilhete)
    assert vb.leituras_das_variantes(c) == [{"bilhete_id": bilhete, "concurso_numero": 9100, "origem": "ajuste_leve",
                                             "acertos_base": 1, "acertos_variante": 2, "saldo": 1}]


def test_variante_sem_base_e_origem_desconhecida_sao_recusadas(conexao):
    c, (j1, j2) = conexao
    with pytest.raises(ValueError, match="volante de onde saiu"):
        salvar_bilhete(c, 9100, {j1: ["1"], j2: ["1", "X"]}, {}, origem="economico")
    with pytest.raises(ValueError, match="desconhecida"):
        salvar_bilhete(c, 9100, {j1: ["1"], j2: ["1", "X"]}, {}, origem="outra")


def test_bilhete_igual_acha_a_mesma_marcacao_em_qualquer_ordem(conexao):
    c, (j1, j2) = conexao
    assert bilhete_igual(c, 9100, {j1: ["1"], j2: ["X", "1"]}) is None
    salvo = salvar_bilhete(c, 9100, {j1: ["1"], j2: ["1", "X"]}, {})
    assert bilhete_igual(c, 9100, {j1: ["1"], j2: ["X", "1"]}) == salvo
    assert bilhete_igual(c, 9100, {j1: ["2"], j2: ["1", "X"]}) is None

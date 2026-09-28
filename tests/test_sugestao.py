from stats.sugestao import sugerir_marcacao


def test_favorito_dominante_sugere_seco():
    resultado = sugerir_marcacao({"1": 70.0, "X": 20.0, "2": 10.0})
    assert resultado == {"tipo": "seco", "colunas": ["1"], "favorito": "1"}


def test_favorito_moderado_sugere_duplo_com_segundo_colocado():
    resultado = sugerir_marcacao({"1": 50.0, "X": 30.0, "2": 20.0})
    assert resultado["tipo"] == "duplo"
    assert resultado["colunas"] == ["1", "X"]
    assert resultado["favorito"] == "1"


def test_jogo_equilibrado_sugere_triplo():
    resultado = sugerir_marcacao({"1": 36.0, "X": 33.0, "2": 31.0})
    assert resultado["tipo"] == "triplo"
    assert resultado["colunas"] == ["1", "X", "2"]


def test_limiar_exato_do_seco_conta_como_seco():
    resultado = sugerir_marcacao({"1": 65.0, "X": 20.0, "2": 15.0})
    assert resultado["tipo"] == "seco"

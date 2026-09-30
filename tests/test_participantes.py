from stats.participantes import rotulos_de_participantes


def _p(id_, nome, uf=None, tipo="clube"):
    return {"id": id_, "nome": nome, "tipo": tipo, "pais_ou_uf": uf}


def test_nome_unico_mantem_o_rotulo_simples():
    assert rotulos_de_participantes([_p(1, "VASCO DA GAMA", "RJ"), _p(2, "ITALIA", None, "selecao")]) == {
        "VASCO DA GAMA (clube)": 1, "ITALIA (selecao)": 2}


def test_homonimos_ganham_a_uf_e_nenhum_fica_inalcancavel():
    rotulos = rotulos_de_participantes([_p(64, "CRUZEIRO", "MG"), _p(987, "CRUZEIRO", "RS"), _p(626, "CRUZEIRO", None)])
    assert rotulos == {"CRUZEIRO/MG (clube)": 64, "CRUZEIRO/RS (clube)": 987, "CRUZEIRO/UF não informada (clube)": 626}
    assert sorted(rotulos.values()) == [64, 626, 987]  # a falha antiga: só o último id sobrevivia


def test_mesma_uf_repetida_recebe_o_id_e_continua_unico():
    rotulos = rotulos_de_participantes([_p(10, "AMERICA", "MG"), _p(11, "AMERICA", "MG")])
    assert rotulos == {"AMERICA/MG (clube) #10": 10, "AMERICA/MG (clube) #11": 11}


def test_mesmo_nome_em_tipos_diferentes_nao_e_homonimo():
    assert rotulos_de_participantes([_p(1, "GUINE", None, "selecao"), _p(2, "GUINE", "SP")]) == {
        "GUINE (selecao)": 1, "GUINE (clube)": 2}


def test_lista_vazia():
    assert rotulos_de_participantes([]) == {}

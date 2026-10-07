"""Medição do filtro de notícias contra o gabarito do usuário (item A3 do plano v2)."""
import pytest

from externo.gabarito import gravar_csv, ler_csv, linhas_para_rotular, medir


def _l(decisao, correto):
    return {"concurso": "1274", "time": "T", "manchete": "m", "decisao_app": decisao, "sinais_app": "s", "correto": correto}


def test_precisao_e_cobertura():
    linhas = [_l("aplicada", "sim"), _l("aplicada", "sim"), _l("informativa", "nao"), _l("aplicada", "sim"),
              _l("descartada", "sim"), _l("descartada", "nao"), _l("aplicada", "")]
    r = medir(linhas)
    assert r["rotuladas"] == 6 and r["aceitas"] == 4
    assert r["precisao"] == pytest.approx(3 / 4)
    assert r["cobertura"] == pytest.approx(3 / 4)  # 3 aceitas certas de 4 que deveriam valer (1 descarte errado)
    baixo, alto = r["precisao_ic95"]
    assert baixo < 0.75 < alto  # com 4 manchetes a faixa é larga


def test_sem_rotulo_nao_mede():
    r = medir([_l("aplicada", ""), _l("descartada", " ")])
    assert r["rotuladas"] == 0 and r["precisao"] is None and r["cobertura"] is None and r["precisao_ic95"] is None


def test_exporta_so_manchetes_com_sinal_e_le_de_volta(tmp_path):
    lidas = [
        {"concurso_numero": 1274, "participante": "ALFA", "titulo": "Alfa; lesão", "situacao": "aplicada",
         "aceitos": ["lesao_titular"], "descartes": []},
        {"concurso_numero": 1274, "participante": "ALFA", "titulo": "Beta lesão", "situacao": "descartada",
         "aceitos": [], "descartes": [{"sinal": "lesao_titular", "motivo": "sujeito_outro_time"}]},
        {"concurso_numero": 1274, "participante": "ALFA", "titulo": "Agenda", "situacao": "sem_sinal",
         "aceitos": [], "descartes": []},
    ]
    linhas = linhas_para_rotular(lidas)
    assert [l["manchete"] for l in linhas] == ["Alfa; lesão", "Beta lesão"]
    caminho = tmp_path / "g" / "1274.csv"
    gravar_csv(linhas, caminho)
    lidas_de_volta = ler_csv(caminho)
    assert lidas_de_volta[0]["manchete"] == "Alfa; lesão" and lidas_de_volta[1]["sinais_app"] == "lesao_titular"

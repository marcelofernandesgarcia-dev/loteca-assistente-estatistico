"""Links de consulta manual (Transfermarkt): montagem do endereço, lista curada
e termo não verificado. Nada aqui faz rede."""
import csv

import config
from stats.links_externos import carregar_termos_transfermarkt, link_busca_transfermarkt

TERMOS = {20031: {"termo": "Ceará SC", "observacao": ""}, 59896: {"termo": "Athletic Club", "observacao": "Aparece abaixo do Bilbao"}}


def test_termo_curado_monta_a_busca_e_e_verificado():
    link = link_busca_transfermarkt("CEARA", 20031, "Ceará", termos=TERMOS)
    assert link["url"] == f"{config.TRANSFERMARKT_BUSCA_URL}?query=Cear%C3%A1+SC"
    assert link["termo"] == "Ceará SC" and link["verificado"] is True and link["observacao"] == ""


def test_observacao_da_lista_curada_acompanha_o_link():
    assert link_busca_transfermarkt("ATHLETIC CLUB", 59896, "Athletic SAF", termos=TERMOS)["observacao"] == "Aparece abaixo do Bilbao"


def test_clube_fora_da_lista_usa_o_nome_da_cbf_sem_saf_e_nao_e_verificado():
    link = link_busca_transfermarkt("LONDRINA", 62726, "Londrina SAF", termos=TERMOS)
    assert link["termo"] == "Londrina" and link["verificado"] is False
    assert link_busca_transfermarkt("X", 1, "Grêmio Novorizontino - Saf", termos={})["termo"] == "Grêmio Novorizontino"
    assert link_busca_transfermarkt("X", 1, "Sport Recife", termos={})["termo"] == "Sport Recife"  # sem sufixo: intacto


def test_selecao_sem_cbf_usa_o_nome_do_participante():
    link = link_busca_transfermarkt("PAIS DE GALES", None, None, termos=TERMOS)
    assert link["termo"] == "Pais De Gales" and link["verificado"] is False
    assert link["url"].endswith("query=Pais+De+Gales")


def test_termo_com_caractere_especial_e_codificado_na_url():
    link = link_busca_transfermarkt("X", None, "Time & Cia=1", termos={})
    assert "&Cia" not in link["url"] and "%26" in link["url"] and "%3D" in link["url"]


def test_arquivo_curado_real_carrega_e_cada_linha_e_valida():
    carregar_termos_transfermarkt.cache_clear()
    termos = carregar_termos_transfermarkt()
    assert len(termos) >= 12 and termos[20031]["termo"] == "Ceará SC"
    assert all(t["termo"] and not t["termo"].lower().endswith("saf") for t in termos.values())  # SAF zera a busca


def test_arquivo_ausente_devolve_vazio(tmp_path):
    carregar_termos_transfermarkt.cache_clear()
    assert carregar_termos_transfermarkt(str(tmp_path / "nao-existe.csv")) == {}


def test_arquivo_personalizado_ignora_comentarios(tmp_path):
    arquivo = tmp_path / "termos.csv"
    with open(arquivo, "w", encoding="utf-8", newline="") as f:
        f.write("# comentário\n")
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(["cod_time", "termo", "observacao"])
        escritor.writerow([7, "Time Sete", "dica"])
    assert carregar_termos_transfermarkt(str(arquivo)) == {7: {"termo": "Time Sete", "observacao": "dica"}}

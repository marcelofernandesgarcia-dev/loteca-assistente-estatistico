import datetime as dt

from lancador.regras import (
    comando_edge,
    comando_streamlit,
    ler_instancia,
    porta_livre,
    precisa_atualizar,
    texto_da_instancia,
    ultima_tentativa,
)

AGORA = dt.datetime(2026, 9, 30, 12, 0)


def test_porta_livre_pula_as_ocupadas_e_devolve_none_se_todas_estao():
    assert porta_livre(8700, 8705, lambda p: p in (8700, 8701)) == 8702
    assert porta_livre(8700, 8701, lambda p: True) is None


def test_ultima_tentativa_conta_falha_e_ignora_fonte_desconhecida():
    execucoes = {
        "caixa": {"concluido_em": "2026-09-30T08:00:00", "sucesso": 0},
        "cbf": {"concluido_em": "2026-09-29T08:00:00", "sucesso": 1},
        "outra": {"concluido_em": "2026-09-30T11:00:00"},
    }
    assert ultima_tentativa(execucoes) == dt.datetime(2026, 9, 30, 8, 0)
    assert ultima_tentativa({}) is None


def test_precisa_atualizar_por_idade_e_chave_desligada():
    assert precisa_atualizar(None, AGORA, 12)
    assert not precisa_atualizar(AGORA - dt.timedelta(hours=11), AGORA, 12)
    assert precisa_atualizar(AGORA - dt.timedelta(hours=12), AGORA, 12)
    assert not precisa_atualizar(None, AGORA, 12, ligado=False)


def test_comando_streamlit_so_neste_computador_e_sem_estatistica_de_uso():
    cmd = comando_streamlit("python.exe", "app/main.py", "127.0.0.1", 8700)
    assert cmd[:4] == ["python.exe", "-m", "streamlit", "run"]
    assert cmd[cmd.index("--server.address") + 1] == "127.0.0.1"
    assert cmd[cmd.index("--server.port") + 1] == "8700"
    assert cmd[cmd.index("--browser.gatherUsageStats") + 1] == "false"


def test_comando_edge_em_modo_aplicativo_com_perfil_proprio():
    cmd = comando_edge("msedge.exe", "http://127.0.0.1:8700", r"C:\perfil")
    assert "--app=http://127.0.0.1:8700" in cmd and r"--user-data-dir=C:\perfil" in cmd


def test_instancia_ida_e_volta_e_arquivo_corrompido():
    assert ler_instancia(texto_da_instancia(123, 8700)) == {"pid": 123, "porta": 8700}
    assert ler_instancia("{quebrado") is None
    assert ler_instancia('{"pid": 1}') is None
    assert ler_instancia(None) is None

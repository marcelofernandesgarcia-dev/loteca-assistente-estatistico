"""Regras do lançador (iniciar.pyw), sem efeito colateral para poderem ser testadas:
qual porta usar, se é hora de atualizar os dados, como montar os comandos e como
reconhecer uma instância já aberta. Quem abre processo, rede e arquivo é o
iniciar.pyw."""
import datetime as dt
import json

FONTES_ATUALIZADAS = ("caixa", "cbf", "noticias")


def porta_livre(inicio: int, fim: int, esta_ocupada) -> int | None:
    """A primeira porta da faixa que `esta_ocupada(porta)` diz estar livre."""
    for porta in range(inicio, fim + 1):
        if not esta_ocupada(porta):
            return porta
    return None


def ultima_tentativa(execucoes: dict[str, dict]) -> dt.datetime | None:
    """Quando foi a tentativa de atualização mais recente (com sucesso ou não), pelas linhas
    de `db.ultima_execucao_por_fonte`. Conta a falha também: sem internet, o app não fica
    tentando de novo a cada abertura."""
    datas = [
        dt.datetime.fromisoformat(execucao["concluido_em"])
        for fonte, execucao in execucoes.items()
        if fonte in FONTES_ATUALIZADAS and execucao.get("concluido_em")
    ]
    return max(datas) if datas else None


def precisa_atualizar(ultima: dt.datetime | None, agora: dt.datetime, horas: float, ligado: bool = True) -> bool:
    if not ligado:
        return False
    return ultima is None or (agora - ultima).total_seconds() >= horas * 3600


def comando_streamlit(python: str, caminho_app: str, endereco: str, porta: int) -> list[str]:
    """Os parâmetros vão também no comando (além de .streamlit/config.toml) para valerem
    mesmo se o arquivo de configuração sumir: só este computador e sem estatística de uso."""
    return [
        python, "-m", "streamlit", "run", caminho_app,
        "--server.address", endereco, "--server.port", str(porta), "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]


def comando_edge(edge: str, url: str, pasta_perfil: str) -> list[str]:
    """Edge em modo aplicativo (janela sem barra de navegador) com perfil próprio: vira um
    processo separado que termina quando a janela fecha, e é isso que encerra o app."""
    return [edge, f"--app={url}", f"--user-data-dir={pasta_perfil}", "--no-first-run", "--no-default-browser-check"]


def texto_da_instancia(pid: int, porta: int) -> str:
    return json.dumps({"pid": pid, "porta": porta})


def ler_instancia(texto: str | None) -> dict | None:
    """O arquivo de instância, ou None se não existe ou está corrompido (aí é ignorado)."""
    if not texto:
        return None
    try:
        dados = json.loads(texto)
        return {"pid": int(dados["pid"]), "porta": int(dados["porta"])}
    except (ValueError, KeyError, TypeError):
        return None

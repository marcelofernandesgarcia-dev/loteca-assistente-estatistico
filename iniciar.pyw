"""Abre o Loteca -- Assistente Estatístico com um clique (atalho na Área de
Trabalho e no Menu Iniciar, criados por scripts/criar_atalhos.ps1).

O que acontece ao abrir:
1. se o app já está aberto, só abre outra janela dele e sai;
2. sobe o servidor em segundo plano, só neste computador (127.0.0.1), numa porta livre;
3. abre a janela do app (Edge em modo aplicativo, perfil próprio); enquanto o
   servidor sobe, a janela mostra "Abrindo o aplicativo...";
4. se a última atualização dos dados tem mais de N horas, roda
   scripts/atualizar_tudo.py em segundo plano (o app abre na hora com o que já tem);
5. fechar a janela encerra o servidor. Uma atualização em andamento termina sozinha
   (cada fonte grava em transação própria).

Sem Edge, abre no navegador padrão; nesse caso o servidor só para quando o Windows
é encerrado (limitação registrada no README). Regras testáveis em lancador/regras.py.
Rode com pythonw.exe (sem janela preta). Log em logs/lancador.log, sem dado pessoal.
"""
import ctypes
import datetime as dt
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

PASTA_LOGS = RAIZ / "logs"
PASTA_ESTADO = Path(os.environ.get("LOCALAPPDATA", str(RAIZ))) / "LotecaAssistente"
ARQUIVO_INSTANCIA = PASTA_ESTADO / "instancia.json"
SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TITULO = "Loteca -- Assistente Estatístico"

PASTA_LOGS.mkdir(exist_ok=True)
PASTA_ESTADO.mkdir(parents=True, exist_ok=True)
_manipulador = logging.handlers.RotatingFileHandler(
    PASTA_LOGS / "lancador.log", maxBytes=500_000, backupCount=3, encoding="utf-8"
)
_manipulador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s execucao=%(execucao)s %(message)s"))
_log_base = logging.getLogger("lancador")
_log_base.addHandler(_manipulador)
_log_base.setLevel(logging.INFO)
log = logging.LoggerAdapter(_log_base, {"execucao": uuid.uuid4().hex[:8]})


def avisar(texto: str) -> None:
    """Caixa de mensagem do Windows (o lançador não tem console)."""
    try:
        ctypes.windll.user32.MessageBoxW(0, texto, TITULO, 0x10)
    except (AttributeError, OSError):
        print(texto, file=sys.stderr)


def porta_ocupada(porta: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def servidor_responde(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/_stcore/health", timeout=1) as resposta:
            return resposta.status == 200
    except OSError:
        return False


def achar_edge(config) -> str | None:
    return next((caminho for caminho in config.LANCADOR_EDGE if Path(caminho).exists()), None)


def pagina_carregando(url: str, limite_s: int) -> Path:
    modelo = (RAIZ / "lancador" / "carregando.html").read_text(encoding="utf-8")
    pagina = PASTA_ESTADO / "carregando.html"
    pagina.write_text(
        modelo.replace("__URL__", url).replace("__LIMITE_MS__", str(limite_s * 1000)), encoding="utf-8"
    )
    return pagina


PASTA_PERFIL = PASTA_ESTADO / "perfil-edge"


def abrir_janela(config, url: str, inicial: str) -> bool:
    """Abre a janela do app. True se abriu no Edge (dá para saber quando fecha); False
    quando caiu no navegador padrão."""
    from lancador.regras import comando_edge

    edge = achar_edge(config)
    if edge:
        subprocess.Popen(comando_edge(edge, inicial, str(PASTA_PERFIL)))
        return True
    log.warning("Edge não encontrado; abrindo no navegador padrão")
    webbrowser.open(url)
    return False


def esperar_janelas_fecharem() -> int:
    """O Edge relança o próprio processo ao abrir: em vez de esperar o processo iniciado,
    um PowerShell espera todas as janelas do perfil próprio fecharem."""
    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RAIZ / "lancador" / "esperar_janela.ps1"),
         "-Perfil", str(PASTA_PERFIL)],
        creationflags=SEM_JANELA,
    )
    return resultado.returncode


def atualizar_se_preciso(config, python: str) -> None:
    from lancador.regras import precisa_atualizar, ultima_tentativa

    import db

    try:
        db.inicializar_schema()
        with db.sessao() as conexao:
            ultima = ultima_tentativa(db.ultima_execucao_por_fonte(conexao))
    except Exception as erro:  # banco ilegível: o app abre mesmo assim; o erro fica no log
        log.error("não foi possível ler a última atualização: %s", type(erro).__name__)
        return
    if not config.LANCADOR_ATUALIZAR_AO_ABRIR:
        log.info("atualização ao abrir desligada (LOTECA_ATUALIZAR_AO_ABRIR=0)")
        return
    if not precisa_atualizar(ultima, dt.datetime.now(), config.LANCADOR_HORAS_ENTRE_ATUALIZACOES):
        log.info("atualização dispensada; última tentativa em %s", ultima)
        return
    saida = open(PASTA_LOGS / "atualizacao.log", "a", encoding="utf-8")
    subprocess.Popen([python, str(RAIZ / "scripts" / "atualizar_tudo.py")], cwd=RAIZ, stdout=saida,
                     stderr=subprocess.STDOUT, creationflags=SEM_JANELA)
    log.info("atualização iniciada em segundo plano; última tentativa em %s", ultima)


def principal() -> int:
    try:
        import config
        from lancador.regras import comando_streamlit, ler_instancia, porta_livre, texto_da_instancia
    except ImportError as erro:
        log.error("ambiente incompleto: %s", erro)
        avisar("O ambiente do aplicativo está incompleto (pasta .venv). Veja a seção 'Instalação' do README.")
        return 1

    # 1. Já aberto? Só abre outra janela.
    instancia = ler_instancia(ARQUIVO_INSTANCIA.read_text(encoding="utf-8") if ARQUIVO_INSTANCIA.exists() else None)
    if instancia:
        url = f"http://{config.LANCADOR_ENDERECO}:{instancia['porta']}"
        if servidor_responde(url):
            log.info("app já aberto na porta %s; abrindo outra janela", instancia["porta"])
            abrir_janela(config, url, url)
            return 0

    # 2. Servidor em segundo plano.
    porta = porta_livre(*config.LANCADOR_PORTAS, porta_ocupada)
    if porta is None:
        avisar("Não há porta livre para abrir o aplicativo. Feche outros programas e tente de novo.")
        log.error("nenhuma porta livre em %s", config.LANCADOR_PORTAS)
        return 1
    python = str(Path(sys.executable).with_name("python.exe"))
    url = f"http://{config.LANCADOR_ENDERECO}:{porta}"
    servidor = subprocess.Popen(
        comando_streamlit(python, str(RAIZ / "app" / "main.py"), config.LANCADOR_ENDERECO, porta),
        cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=open(PASTA_LOGS / "servidor.log", "a", encoding="utf-8"),
        creationflags=SEM_JANELA,
    )
    ARQUIVO_INSTANCIA.write_text(texto_da_instancia(servidor.pid, porta), encoding="utf-8")
    log.info("servidor iniciado pid=%s porta=%s", servidor.pid, porta)

    try:
        # 3. Janela com "Abrindo..." enquanto o servidor sobe.
        janela = abrir_janela(config, url, pagina_carregando(url, config.LANCADOR_TEMPO_MAX_ESPERA_S).as_uri())

        # 4. Atualização dos dados, sem segurar a abertura.
        atualizar_se_preciso(config, python)

        limite = time.monotonic() + config.LANCADOR_TEMPO_MAX_ESPERA_S
        while not servidor_responde(url):
            if servidor.poll() is not None or time.monotonic() > limite:
                log.error("servidor não respondeu (código de saída %s)", servidor.poll())
                avisar("O aplicativo não conseguiu abrir. Detalhes em logs/servidor.log, na pasta do projeto.")
                return 1
            time.sleep(0.5)
        log.info("servidor pronto")

        # 5. Fechar a janela encerra o servidor.
        if janela:
            codigo = esperar_janelas_fecharem()
            if codigo == 2:
                log.error("a janela do app não apareceu a tempo")
                avisar("A janela do aplicativo não abriu. Tente de novo pelo atalho.")
                return 1
            log.info("janelas fechadas (código %s)", codigo)
        else:
            servidor.wait()
        return 0
    finally:
        if servidor.poll() is None:
            servidor.terminate()
            try:
                servidor.wait(timeout=10)
            except subprocess.TimeoutExpired:
                servidor.kill()
        ARQUIVO_INSTANCIA.unlink(missing_ok=True)
        log.info("servidor encerrado")


if __name__ == "__main__":
    sys.exit(principal())

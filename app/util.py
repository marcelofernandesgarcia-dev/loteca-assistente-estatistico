"""Utilidades compartilhadas pelas páginas Streamlit -- sem lógica de
negócio aqui, só o que é específico de UI (conexão cacheada, avisos)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import config
import db
from importer.seed_valorfinal import carregar as carregar_seed_valorfinal


@st.cache_resource
def preparar_banco():
    db.inicializar_schema()
    with db.sessao() as conexao:
        ja_tem_seed = conexao.execute("SELECT 1 FROM historico_valorfinal LIMIT 1").fetchone()
        if not ja_tem_seed:
            carregar_seed_valorfinal(conexao)
    return True


def obter_conexao():
    preparar_banco()
    return db.conectar()


# O Streamlit serve a página como inglês (<html lang="en">), e o navegador oferece tradução automática: no print
# do usuário de 07/10/2026, "Por time" virou "Por tempo". O script declara a página como pt-BR e marca
# translate="no" (sugestão S5, aprovada em 07/10/2026). Roda num componente invisível, que alcança a página.
_DECLARAR_PORTUGUES = """
<script>
  const raiz = window.parent.document.documentElement;
  raiz.lang = "pt-BR";
  raiz.setAttribute("translate", "no");
  if (!window.parent.document.querySelector('meta[name="google"]')) {
    const meta = window.parent.document.createElement("meta");
    meta.name = "google"; meta.content = "notranslate";
    window.parent.document.head.appendChild(meta);
  }
</script>
"""


def declarar_portugues():
    import streamlit.components.v1 as componentes

    componentes.html(_DECLARAR_PORTUGUES, height=0)


def mostrar_aviso_responsabilidade():
    declarar_portugues()
    st.caption(config.AVISO_RESPONSABILIDADE)


def formatar_data_br(data_iso: str | None) -> str:
    """Datas ficam em ISO (AAAA-MM-DD) no banco -- mais fácil de ordenar e
    comparar -- e só são formatadas para dia/mês/ano na hora de exibir."""
    if not data_iso:
        return "-"
    try:
        ano, mes, dia = data_iso.split("-")
        return f"{dia}/{mes}/{ano}"
    except ValueError:
        return data_iso

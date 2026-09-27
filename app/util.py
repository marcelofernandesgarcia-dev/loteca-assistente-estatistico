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


def mostrar_aviso_responsabilidade():
    st.caption(config.AVISO_RESPONSABILIDADE)

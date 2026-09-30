"""Links para consulta MANUAL em sites de terceiros. O app só monta o endereço;
nada é coletado nem guardado. Existe porque os dois sites (BID da CBF e
Transfermarkt) não permitem coleta automática -- ver
docs/pesquisa-bid-cbf-30-09-2026.md e docs/pesquisa-transfermarkt-30-09-2026.md.
"""
import csv
import re
from functools import lru_cache
from urllib.parse import urlencode

import config

_SUFIXO_SAF = re.compile(r"\s*-?\s*\bS\.?A\.?F\.?\b\s*$", re.IGNORECASE)


@lru_cache(maxsize=4)
def carregar_termos_transfermarkt(caminho: str | None = None) -> dict[int, dict]:
    """{cod_time da CBF: {'termo', 'observacao'}}, de data/busca-transfermarkt.csv.
    Arquivo ausente devolve vazio (todo clube cai no termo não verificado)."""
    arquivo = caminho or str(config.TRANSFERMARKT_TERMOS_CSV)
    termos = {}
    try:
        with open(arquivo, encoding="utf-8") as f:
            for linha in csv.DictReader((l for l in f if not l.startswith("#")), delimiter=";"):
                termos[int(linha["cod_time"])] = {
                    "termo": linha["termo"].strip(),
                    "observacao": (linha.get("observacao") or "").strip(),
                }
    except FileNotFoundError:
        return {}
    return termos


def _termo_da_cbf(nome_cbf: str) -> str:
    """Nome da CBF sem o sufixo SAF, que zera os resultados da busca do Transfermarkt."""
    return _SUFIXO_SAF.sub("", nome_cbf).strip()


def link_busca_transfermarkt(
    nome: str,
    cod_time: int | None = None,
    nome_cbf: str | None = None,
    termos: dict[int, dict] | None = None,
) -> dict:
    """Link de busca por clube ou seleção. `verificado` é True só quando o termo
    veio da lista curada (testado ao vivo). Sem verificação, o termo é o nome da
    CBF (sem SAF) ou o nome do participante, e a busca pode não achar o clube
    certo -- a tela diz isso."""
    termos = carregar_termos_transfermarkt() if termos is None else termos
    curado = termos.get(cod_time) if cod_time else None
    if curado:
        termo, observacao, verificado = curado["termo"], curado["observacao"], True
    else:
        termo, observacao, verificado = _termo_da_cbf(nome_cbf) if nome_cbf else nome.strip().title(), "", False
    return {
        "url": f"{config.TRANSFERMARKT_BUSCA_URL}?{urlencode({'query': termo})}",
        "termo": termo,
        "observacao": observacao,
        "verificado": verificado,
    }

"""Desempenho de cada participante do concurso no ANO EM CURSO, pela melhor
fonte disponível (pedido do usuário, 30/09/2026: o ano em curso sempre visível
e em primeiro lugar). Só leitura e aritmética sobre dado coletado; nada aqui é
previsão.

Ordem das fontes, da mais completa para a mais pobre:
1. "cbf": temporada do ano nas Séries A, B e C (classificação oficial; na Série C, que tem fases,
   os totais somam os jogos de todas as fases);
2. "selecoes": jogos do ano na base aberta de resultados internacionais (CC0);
3. "loteca": jogos do ano que caíram na grade da Loteca;
4. None: nenhum jogo do ano encontrado.
"""
import config
from stats.cbf import classificacao_do_participante, rotulo_da_posicao, totais_da_temporada
from stats.contexto import selo_da_posicao
from stats.temporada import desempenho_no_ano

NOME_SERIE = config.CBF_NOMES_SERIE
TEXTO_FONTE = {
    "cbf": "classificação da CBF",
    "selecoes": "jogos de seleções do ano (base aberta)",
    "loteca": "só os jogos do ano na grade da Loteca",
}


def aproveitamento(pontos: int, jogos: int) -> float | None:
    """Percentual dos pontos disputados (vitória 3, empate 1)."""
    return 100.0 * pontos / (3 * jogos) if jogos else None


def _lado_vazio(nome: str, ano: int) -> dict:
    return {
        "nome": nome, "ano": ano, "fonte": None, "texto_fonte": "sem jogos do ano encontrados", "jogos": 0,
        "vitorias": 0, "empates": 0, "derrotas": 0, "pontos": 0, "gols_pro": 0, "gols_contra": 0,
        "aproveitamento": None, "posicao": None, "rotulo_posicao": None, "serie": None, "zona": None, "ultimos": [],
        "amostra_pequena": True,
    }


def _completar(lado: dict) -> dict:
    lado["pontos"] = 3 * lado["vitorias"] + lado["empates"]
    lado["aproveitamento"] = aproveitamento(lado["pontos"], lado["jogos"])
    lado["amostra_pequena"] = lado["jogos"] < config.ANO_CURSO_AMOSTRA_PEQUENA
    return lado


def desempenho_selecao_no_ano(jogos_base: list[dict], nome_base: str, ano: int) -> dict | None:
    """V/E/D, gols e últimos resultados de uma seleção nos jogos do ano da base aberta
    (`jogos_base` em ordem de data, como devolve stats.selecoes.carregar_resultados).
    None se a seleção não jogou no ano."""
    prefixo = f"{ano}-"
    jogos = [j for j in jogos_base if j["data"].startswith(prefixo) and nome_base in (j["casa"], j["fora"])]
    if not jogos:
        return None
    vitorias = empates = derrotas = gols_pro = gols_contra = 0
    sequencia = []
    for jogo in jogos:
        em_casa = jogo["casa"] == nome_base
        feitos = jogo["gols_casa"] if em_casa else jogo["gols_fora"]
        sofridos = jogo["gols_fora"] if em_casa else jogo["gols_casa"]
        gols_pro += feitos
        gols_contra += sofridos
        if feitos > sofridos:
            vitorias += 1
            sequencia.append("V")
        elif feitos == sofridos:
            empates += 1
            sequencia.append("E")
        else:
            derrotas += 1
            sequencia.append("D")
    return {
        "jogos": len(jogos), "vitorias": vitorias, "empates": empates, "derrotas": derrotas,
        "gols_pro": gols_pro, "gols_contra": gols_contra,
        "ultimos": sequencia[-config.ANO_CURSO_ULTIMOS:], "ultimo_jogo": jogos[-1]["data"],
    }


def lado_no_ano(conexao, participante: dict, ano: int, jogos_base=None, nomes_selecoes=None) -> dict:
    """`participante`: {'id', 'nome', 'tipo'}. `jogos_base` e `nomes_selecoes` são a base aberta de
    seleções já carregada (opcional: sem ela, seleções caem nos jogos da Loteca)."""
    nome = participante["nome"]
    lado = _lado_vazio(nome, ano)

    classif = classificacao_do_participante(conexao, participante["id"])
    if classif and classif.get("ano") == ano and classif.get("jogos"):
        ultimos = [r.strip() for r in (classif.get("ultimos_jogos") or "").split(",") if r.strip()]
        lado.update(
            fonte="cbf", jogos=classif["jogos"], vitorias=classif["vitorias"] or 0, empates=classif["empates"] or 0,
            derrotas=classif["derrotas"] or 0, gols_pro=classif["gols_pro"] or 0, gols_contra=classif["gols_contra"] or 0,
            posicao=classif["posicao"], rotulo_posicao=rotulo_da_posicao(classif), serie=classif["serie"],
            ultimos=ultimos[-config.ANO_CURSO_ULTIMOS:], zona=selo_da_posicao(classif["serie"], ano, classif["posicao"]),
        )
        lado["texto_fonte"] = f"{TEXTO_FONTE['cbf']} ({NOME_SERIE.get(classif['serie'], classif['serie'])})"
        if classif.get("fase"):
            # Competição com fases (Série C): a tabela traz só a fase atual; o ano soma todos os jogos.
            totais = totais_da_temporada(conexao, classif["cod_time"], classif["serie"], ano)
            if totais["jogos"]:
                lado.update({k: v for k, v in totais.items() if k != "sequencia"},
                            ultimos=totais["sequencia"][-config.ANO_CURSO_ULTIMOS:])
                lado["texto_fonte"] += ", todas as fases"
        return _completar(lado)

    if participante.get("tipo") == "selecao" and jogos_base is not None and nomes_selecoes:
        nome_base = nomes_selecoes.get(nome.strip().upper())
        dados = desempenho_selecao_no_ano(jogos_base, nome_base, ano) if nome_base else None
        if dados:
            lado.update(fonte="selecoes", **{k: v for k, v in dados.items() if k != "ultimo_jogo"})
            lado["texto_fonte"] = f"{TEXTO_FONTE['selecoes']}, até {_data_br(dados['ultimo_jogo'])}"
            return _completar(lado)

    loteca = desempenho_no_ano(conexao, participante["id"], ano)
    if loteca["jogos"]:
        lado.update(
            fonte="loteca", jogos=loteca["jogos"], vitorias=loteca["vitorias"], empates=loteca["empates"],
            derrotas=loteca["derrotas"], gols_pro=loteca["gols_marcados"], gols_contra=loteca["gols_sofridos"],
            texto_fonte=TEXTO_FONTE["loteca"],
        )
        return _completar(lado)
    return lado


def _data_br(data_iso: str) -> str:
    ano, mes, dia = data_iso[:10].split("-")
    return f"{dia}/{mes}/{ano}"


def diferenca_no_ano(casa: dict, fora: dict) -> dict | None:
    """Quem vai melhor no ano, em pontos percentuais de aproveitamento. Só compara quando
    os dois têm dado; avisa quando as fontes são diferentes (ex.: CBF x Loteca), porque aí
    a comparação é frágil. É aritmética sobre o ano, não previsão do jogo."""
    if casa["aproveitamento"] is None or fora["aproveitamento"] is None:
        return None
    diferenca = casa["aproveitamento"] - fora["aproveitamento"]
    return {
        "pontos_percentuais": diferenca,
        "melhor": "casa" if diferenca > 0 else "fora" if diferenca < 0 else None,
        "fontes_diferentes": casa["fonte"] != fora["fonte"],
        "amostra_pequena": casa["amostra_pequena"] or fora["amostra_pequena"],
    }


def resumo_do_concurso_no_ano(conexao, jogos: list[dict], ano: int, jogos_base=None, nomes_selecoes=None) -> list[dict]:
    """`jogos`: do concurso, cada um com num_jogo, casa_id, casa, casa_tipo, fora_id, fora, fora_tipo
    (formato de stats.painel.participantes_do_concurso)."""
    resumo = []
    for jogo in jogos:
        casa = lado_no_ano(conexao, {"id": jogo["casa_id"], "nome": jogo["casa"], "tipo": jogo.get("casa_tipo")},
                           ano, jogos_base, nomes_selecoes)
        fora = lado_no_ano(conexao, {"id": jogo["fora_id"], "nome": jogo["fora"], "tipo": jogo.get("fora_tipo")},
                           ano, jogos_base, nomes_selecoes)
        resumo.append({"num_jogo": jogo["num_jogo"], "casa": casa, "fora": fora, "diferenca": diferenca_no_ano(casa, fora)})
    return resumo


def cobertura(resumo: list[dict]) -> dict:
    """Quantos participantes têm dado do ano, por fonte."""
    lados = [lado for jogo in resumo for lado in (jogo["casa"], jogo["fora"])]
    por_fonte = {fonte: sum(1 for l in lados if l["fonte"] == fonte) for fonte in ("cbf", "selecoes", "loteca")}
    return {"total": len(lados), "com_dado": sum(por_fonte.values()), **por_fonte,
            "sem_dado": sum(1 for l in lados if l["fonte"] is None),
            "amostra_pequena": sum(1 for l in lados if l["fonte"] and l["amostra_pequena"])}


def frase_do_lado(lado: dict) -> str:
    """Ex.: '6º na Série A · 45 pts em 28 jogos · 54% · últimos: V E D V V'."""
    if lado["fonte"] is None:
        return f"sem jogos de {lado['ano']} encontrados"
    partes = []
    if lado["posicao"]:
        rotulo = lado.get("rotulo_posicao") or f"{lado['posicao']}º"
        artigo = "da" if " no " in rotulo else "na"  # "1º no Grupo B (2ª fase) da Série C" / "6º na Série A"
        partes.append(f"{rotulo} {artigo} {NOME_SERIE.get(lado['serie'], lado['serie'])}")
    partes.append(f"{lado['vitorias']}V {lado['empates']}E {lado['derrotas']}D em {lado['jogos']} jogos")
    partes.append(f"aproveitamento {lado['aproveitamento']:.0f}%")
    if lado["ultimos"]:
        partes.append("últimos: " + " ".join(lado["ultimos"]))
    if lado["zona"]:
        partes.append(f"zona: {lado['zona']}")
    if lado["amostra_pequena"]:
        partes.append("amostra pequena")
    return " · ".join(partes)

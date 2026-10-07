"""Extração de sinais estruturados a partir das notícias coletadas.

Puro (recebe a lista de notícias já coletada, não faz rede) -- testável com
notícias simuladas, sem depender de chamada real. Cada sinal é uma categoria
fechada (config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL), nunca texto livre
interpretado sem critério.

Duas barreiras contra falso positivo, adicionadas depois de revisão externa
(ver docs/plano-fase3-melhorias.md, item C2):
1. o nome do participante precisa aparecer no título -- corta notícia do
   adversário ou de outro assunto que só bateu na busca por coincidência;
2. título com expressão de negação/recuperação (config.VARREDURA_PALAVRAS_DE_NEGACAO)
   é descartado inteiro -- "sem lesão" não vira sinal de lesão;
3. título sobre outra equipe do clube (feminino, base, futsal --
   config.VARREDURA_PALAVRAS_DE_OUTRA_EQUIPE) é descartado inteiro.

Medido com notícia real em 30/09/2026: nome logo depois de "diante do",
"contra o", "enfrentar o", "visita o", "recebe o" é tratado como adversário
e não conta como menção.

Barreiras do contexto do concurso (análise do concurso 1273, 07/10/2026: 4 de 9 sinais
caíram no time errado). Valem quando a varredura informa o adversário e os nomes do concurso:
4. sujeito: se outro time do concurso aparece ANTES do participante, a manchete é do outro
   ("Atlético-MG pode ter desfalques contra o Bragantino" não é do Bragantino);
5. outro jogo: sinal de desfalque, lesão ou suspensão "contra" um time do concurso que não é o
   adversário desta partida fala de outra rodada ("Desfalques do Paysandu para jogo contra a
   Inter de Limeira", quando o Paysandu enfrenta a Ferroviária);
6. rivais na mesma manchete: sinal de sequência ou de tendência sem dono claro é descartado
   ("Grécia coloca água no chope da Alemanha, e Klopp segue sem vencer");
7. seleção: contratação, saída e atraso de salário não se aplicam;
8. especulação ("pode ser suspenso", "pode ter desfalques") vira sinal informativo de possibilidade.
"ex-Sport e Paysandu" não conta como menção a nenhum dos dois clubes.

Limitações que continuam: adversário citado de outro jeito ("salários atrasados do rival"),
time de fora do concurso como sujeito, e clube homônimo (Botafogo-RJ na busca pelo Botafogo-SP).
"""
import re
import unicodedata

import config

_CONECTIVOS = {
    "de", "da", "do", "das", "dos", "e", "fc", "sc", "ec", "afc", "saf",
    # palavras genéricas de futebol -- sozinhas, não identificam qual time é
    "time", "clube", "esporte", "esportivo", "futebol", "equipe", "jogo", "sport",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


# "ex-Sport e Paysandu", "ex-Vasco, Sport e Bahia": a lista inteira é de clubes ANTERIORES do jogador
# (achado no concurso 1273: a contratação do América "ex-Sport e Paysandu" virou sinal do Paysandu).
_EX_CLUBE = re.compile(r"\bex[- ][^\s,;]+(?:(?:\s*,\s*|\s+e\s+)[^\s,;]+)*")
# Nome logo depois destas expressões é o ADVERSÁRIO da frase, não o assunto:
# "Ceará tem cinco desfalques diante do Operário-PR" é notícia do Ceará.
# Achado com notícia real em 30/09/2026 (virava desfalque do Operário, com
# peso). "para o" ficou de fora de propósito: "reforço para o X" é do X.
_COMO_ADVERSARIO = re.compile(
    r"\b(?:diante|contra|enfrentar|enfrenta|enfrentam|visita|visitar|recebe|receber)"
    r"\s+(?:d?[oa]s?\s+)?\S+(?:\s+\S+)?"
)


def _tokens(nome_normalizado: str) -> list[str]:
    return [t for t in nome_normalizado.split() if len(t) >= 4 and t not in _CONECTIVOS] or [nome_normalizado]


def _primeira_posicao(titulo_normalizado: str, nome_normalizado: str, exigir_todos: bool = False) -> int | None:
    """Onde o nome aparece primeiro na manchete, ou None. Com `exigir_todos`, todas as palavras
    relevantes do nome precisam estar lá: "Vila Nova" não é reconhecido só por "nova" (palavra comum)."""
    posicoes = [m.start() if m else None
                for t in _tokens(nome_normalizado) for m in [re.search(rf"\b{re.escape(t)}\b", titulo_normalizado)]]
    achadas = [p for p in posicoes if p is not None]
    if not achadas or (exigir_todos and len(achadas) < len(posicoes)):
        return None
    return min(achadas)


def _sujeito_e_outro_time(titulo_limpo: str, participante: str, outros: list[str]) -> bool:
    """Barreira 4: outro time do concurso citado antes do participante é o sujeito da manchete."""
    minha = _primeira_posicao(titulo_limpo, participante)
    if minha is None:
        return False
    for outro in outros:
        posicao = _primeira_posicao(titulo_limpo, outro, exigir_todos=True)
        if posicao is not None and posicao < minha:
            return True
    return False


def _fala_de_outro_jogo(titulo_ex: str, adversario: str | None, outros: list[str]) -> bool:
    """Barreira 5: o time citado depois de "contra", "diante de" etc. é do concurso mas não é o adversário."""
    for trecho in _COMO_ADVERSARIO.findall(titulo_ex) + _COMO_ADVERSARIO_LONGO.findall(titulo_ex):
        for outro in outros:
            if adversario and outro == adversario:
                continue
            if (_primeira_posicao(trecho, outro, exigir_todos=True) is not None
                    and not (adversario and _primeira_posicao(trecho, adversario, exigir_todos=True) is not None)):
                return True
    return False


# Para achar o adversário citado, inclusive com nome de três palavras ("contra a Inter de Limeira").
_COMO_ADVERSARIO_LONGO = re.compile(
    r"\b(?:diante|contra|enfrentar|enfrenta|enfrentam|visita|visitar|recebe|receber)"
    r"\s+(?:d?[oa]s?\s+)?\S+(?:\s+\S+){0,3}"
)


def _menciona_participante(titulo_normalizado: str, participante_normalizado: str) -> bool:
    """Ao menos um token relevante do nome do participante precisa aparecer no
    título. Tokens curtos e conectivos são ignorados para não exigir demais de
    nomes compostos ('CLUBE DE REGATAS X') -- mas siglas curtas (ex. 'CRB')
    usam o nome inteiro, já que não sobra token longo para checar.
    "ex-Botafogo" não conta como menção: fala de quem JÁ SAIU do clube
    (achado com notícia real em 30/09/2026)."""
    titulo_normalizado = _COMO_ADVERSARIO.sub(" ", _EX_CLUBE.sub(" ", titulo_normalizado))
    tokens = [t for t in participante_normalizado.split() if len(t) >= 4 and t not in _CONECTIVOS]
    if not tokens:
        return participante_normalizado in titulo_normalizado
    return any(token in titulo_normalizado for token in tokens)


def extrair_sinais(noticias: list[dict], participante_nome: str | None = None, adversario_nome: str | None = None,
                   tipo_participante: str | None = None, nomes_do_concurso: list[str] | tuple = ()) -> list[dict]:
    """Retorna uma lista de {'sinal': str, 'evidencia': str, 'fonte': str, 'url': str,
    'publicado_em': str}, um por (sinal, notícia) encontrado -- o cálculo do ajuste, em
    ajuste.py, decide como agregar. `participante_nome`: quando informado, notícia
    cujo título não menciona o participante é ignorada (barreira 1); sempre
    recomendado -- só fica opcional para não quebrar chamada antiga sem esse dado.
    `adversario_nome`, `tipo_participante` ('clube' ou 'selecao') e `nomes_do_concurso`
    (todos os participantes do concurso) ligam as barreiras 4 a 8 (ver o topo do módulo)."""
    participante_normalizado = _normalizar(participante_nome) if participante_nome else None
    adversario_normalizado = _normalizar(adversario_nome) if adversario_nome else None
    outros = [_normalizar(n) for n in nomes_do_concurso if participante_nome and _normalizar(n) != participante_normalizado]
    negacoes_normalizadas = [_normalizar(frase) for frase in config.VARREDURA_PALAVRAS_DE_NEGACAO]
    outra_equipe_normalizadas = [_normalizar(frase) for frase in config.VARREDURA_PALAVRAS_DE_OUTRA_EQUIPE]
    especulativas = [_normalizar(frase) for frase in config.VARREDURA_PALAVRAS_ESPECULATIVAS]

    sinais = []
    for noticia in noticias:
        titulo_normalizado = _normalizar(noticia["titulo"])
        if participante_normalizado and not _menciona_participante(titulo_normalizado, participante_normalizado):
            continue
        if any(negacao in titulo_normalizado for negacao in negacoes_normalizadas):
            continue
        if any(outra in titulo_normalizado for outra in outra_equipe_normalizadas):
            continue  # feminino, base, futsal: não é o time da Loteca (barreira 3)
        titulo_sem_ex = _EX_CLUBE.sub(" ", titulo_normalizado)
        if participante_normalizado and outros and _sujeito_e_outro_time(titulo_sem_ex, participante_normalizado, outros):
            continue  # barreira 4: a manchete é de outro time do concurso
        outro_jogo = bool(outros) and _fala_de_outro_jogo(titulo_sem_ex, adversario_normalizado, outros)
        rivais_juntos = (bool(adversario_normalizado)
                         and _primeira_posicao(titulo_sem_ex, adversario_normalizado, exigir_todos=True) is not None)
        especulativa = any(frase in titulo_normalizado for frase in especulativas)

        tipos = []
        for palavra, tipo_sinal in config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL.items():
            palavra_normalizada = _normalizar(palavra)
            if palavra_normalizada not in titulo_normalizado or tipo_sinal in tipos:
                continue
            if palavra_normalizada == "acerta com" and participante_normalizado:
                # "Cuiabá rescinde com goleiro, que acerta com o Itaquá": quando a manchete é de SAÍDA do
                # jogador, o "acerta com" é o clube novo dele. Em "Flamengo acerta com atacante" (sem saída)
                # a contratação continua sendo do clube citado antes.
                saida = any(_normalizar(p) in titulo_normalizado
                            for p, t in config.VARREDURA_PALAVRAS_CHAVE_PARA_SINAL.items() if t == "saida_de_jogador")
                depois = titulo_normalizado.split(palavra_normalizada, 1)[1]
                if saida and _primeira_posicao(depois, participante_normalizado) is None:
                    continue
            tipos.append(tipo_sinal)
        for tipo_sinal in tipos:
            if especulativa:
                tipo_sinal = config.VARREDURA_SINAL_ESPECULATIVO.get(tipo_sinal, tipo_sinal)  # barreira 8
            if outro_jogo and tipo_sinal in config.VARREDURA_SINAIS_DO_JOGO:
                continue  # barreira 5
            if rivais_juntos and tipo_sinal in config.VARREDURA_SINAIS_AMBIGUOS_ENTRE_RIVAIS:
                continue  # barreira 6
            if tipo_participante == "selecao" and tipo_sinal in config.VARREDURA_SINAIS_SO_DE_CLUBE:
                continue  # barreira 7
            sinais.append(
                {
                    "sinal": tipo_sinal,
                    "evidencia": noticia["titulo"],
                    "fonte": noticia.get("fonte") or noticia.get("url", ""),
                    "url": noticia.get("url", ""),
                    "publicado_em": noticia.get("publicado_em", ""),
                }
            )
    return sinais

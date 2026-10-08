"""Configuração central do projeto. Nada de literal espalhado pelo código -- tudo aqui."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("LOTECA_DB_PATH", BASE_DIR / "loteca.db"))
VALORFINAL_CSV_PATH = BASE_DIR / "data" / "loteca-historico-valorfinal.csv"
BOLOES_OFICIAL_CSV_PATH = BASE_DIR / "data" / "loteca-boloes-oficial.csv"

# Endpoint não-oficial da CAIXA (ver docs/pesquisa-fontes-dados.md)
CAIXA_API_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api/loteca"
CAIXA_REQUEST_INTERVAL_SEGUNDOS = float(os.environ.get("LOTECA_RATE_LIMIT_S", "0.7"))
CAIXA_MAX_REQUISICOES_PARALELAS = int(os.environ.get("LOTECA_MAX_PARALELO", "2"))
CAIXA_REQUEST_TIMEOUT_SEGUNDOS = 15
CAIXA_USER_AGENT = "Mozilla/5.0"

# CBF -- páginas públicas do site (não há API documentada; ver docs/cbf-fonte-de-dados.md).
# Decisão do usuário em 27/09/2026: acessar o portal como um usuário comum, em
# agendamento, uso local. Os termos de uso da CBF (item 6) vedam uso não
# autorizado do conteúdo -- o risco é do usuário; por isso: baixa frequência,
# intervalo entre chamadas, nada de dado da CBF no GitHub, e chave para desligar.
CBF_HABILITADO = os.environ.get("LOTECA_CBF_HABILITADO", "1") == "1"
CBF_BASE_URL = "https://www.cbf.com.br"
CBF_COMPETICOES = [
    # (campeonato, serie, ano)
    ("campeonato-brasileiro", "serie-a", 2026),
    ("campeonato-brasileiro", "serie-b", 2026),
    # Série C (plano aprovado em 07/10/2026, Fase 2): no concurso 1273, 8 clubes de 4 jogos eram do
    # quadrangular do acesso da Série C e o app não tinha nenhum dado deles. A página pública da CBF tem o
    # mesmo formato das Séries A e B (conferido em 07/10/2026), com duas fases e grupos.
    ("campeonato-brasileiro", "serie-c", 2026),
]
# Séries disputadas em pontos corridos (turno e returno numa tabela só). Só nelas o app reconstrói a tabela
# rodada a rodada (Ficha do time "Evolução", Painel "Temporada"); a Série C tem fases e grupos, e misturar
# as fases daria posições falsas.
CBF_SERIES_PONTOS_CORRIDOS = ("serie-a", "serie-b")
CBF_NOMES_SERIE = {"serie-a": "Série A", "serie-b": "Série B", "serie-c": "Série C"}
CBF_MAX_TIMES_POR_COMPETICAO = 40  # teto de páginas de time por competição (Série C: os 20 clubes da 1ª fase)
# Temporadas passadas (P2 da priorização estatística, autorizado em 30/09/2026): coleta única, com
# `scripts/coleta_cbf_historico.py`. Conferidas ao vivo: 2019 a 2025 existem completas nas duas séries.
CBF_TEMPORADAS_PASSADAS = [
    ("campeonato-brasileiro", serie, ano) for ano in range(2019, 2026) for serie in ("serie-a", "serie-b")
]
CBF_JOGOS_TEMPORADA_COMPLETA = 380  # 20 times, turno e returno (REC 2026, art. 14 da Série A e art. 11 da Série B)
# Clubes que trocaram de código na CBF (11, validados pelo usuário em 30/09/2026).
CBF_CODIGOS_EQUIVALENTES_CSV = BASE_DIR / "data" / "cbf-codigos-equivalentes.csv"
# Diferenças entre a soma dos jogos e a tabela da própria CBF, encontradas na coleta de 30/09/2026 e
# entendidas. O roteiro de coleta as trata como conhecidas (não como falha). Nada foi inventado para
# "consertá-las": o jogo que falta continua faltando.
CBF_ANOMALIAS_CONHECIDAS = {
    ("serie-b", 2020): {
        "jogos_faltando": 0,
        "descricao": "Cruzeiro: 55 pontos na soma dos jogos e 49 na tabela da CBF (exatamente 6 a menos), compatível com "
                     "perda de pontos por punição; a causa não foi conferida.",
    },
    ("serie-b", 2023): {
        "jogos_faltando": 1,
        "descricao": "Falta 1 jogo (rodada 20, Juventude x Botafogo-SP) nas páginas dos times; a tabela da CBF o conta "
                     "(Juventude +3 pontos e +2 gols, Botafogo-SP +2 gols sofridos). 379 de 380 jogos.",
    },
}
CBF_INTERVALO_SEGUNDOS = float(os.environ.get("LOTECA_CBF_INTERVALO_S", "2.0"))
CBF_TIMEOUT_SEGUNDOS = 30
# Consulta pública do BID (contratações). Só link para consulta manual: exige
# CAPTCHA e traz dado pessoal de atleta, então o app não coleta nada dali
# (docs/pesquisa-bid-cbf-30-09-2026.md).
BID_CONSULTA_URL = "https://bid.cbf.com.br/home"
# Busca por clube no Transfermarkt (elenco, idade, valor de mercado). Também só
# link: os termos reservam a extração de dados (docs/pesquisa-transfermarkt-30-09-2026.md).
TRANSFERMARKT_BUSCA_URL = "https://www.transfermarkt.com.br/schnellsuche/ergebnis/schnellsuche"
TRANSFERMARKT_TERMOS_CSV = BASE_DIR / "data" / "busca-transfermarkt.csv"
CBF_VALIDADE_HORAS = int(os.environ.get("LOTECA_CBF_VALIDADE_H", "20"))
CBF_USER_AGENT = "Mozilla/5.0 (compatible; LotecaAssistenteLocal/1.0; uso pessoal)"
# Palavras que não ajudam a comparar nome de time da CBF com o da Loteca
# "CLUB" (07/10/2026): "ATHLETIC CLUB" na Loteca é o "Athletic SAF" da CBF; sem ignorar a palavra, a regra
# de pareamento (toda palavra da Loteca no nome da CBF) perderia esse par.
CBF_TOKENS_IGNORADOS = {"SAF", "FC", "S", "A", "F", "DE", "DA", "DO", "EC", "CLUB"}
# Nomes da Loteca com estes prefixos são de outra categoria e nunca pareiam com os times da CBF coletados
# (masculino profissional). "F ": todos os jogos com esse prefixo (concursos 624 a 627 e 682, 2014-2015) são
# entre times com o mesmo prefixo -- uma categoria à parte, provavelmente feminina (conferido em 07/10/2026).
LOTECA_PREFIXOS_OUTRA_CATEGORIA = ("F ",)
# Participantes (nome, UF) que nunca pareiam, por decisão do usuário. "RECIFE/PE" (4 jogos até o concurso 106)
# pareava com o Sport Recife sem confirmação; retirado em 07/10/2026.
CBF_PAREAMENTO_EXCLUIDO = {("RECIFE", "PE")}
# UF deduzida do estádio dos jogos em casa (decisão do usuário em 07/10/2026), só quando a CBF não informa a UF:
# exige este mínimo de jogos em casa com local conhecido, e TODOS no mesmo estado.
CBF_UF_ESTADIO_MINIMO_JOGOS = 3

# Regras de apuração (ver docs/manual-produtos-caixa-v21.md, item 10)
# Concurso mais antigo confirmado na API é o nº 1 (18/02/2002).
PRIMEIRO_CONCURSO = 1
APELIDOS_PARTICIPANTES_CSV = BASE_DIR / "data" / "apelidos-participantes.csv"

# Modelo estatístico -- pesos e tetos do ajuste externo (ver docs/plano do app)
AJUSTE_EXTERNO_TETO_PONTOS = float(os.environ.get("LOTECA_AJUSTE_TETO", "8.0"))
AJUSTE_EXTERNO_PESOS = {
    # sinal -> ajuste em pontos percentuais (positivo ajuda, negativo prejudica)
    "lesao_titular": -3.0,
    "suspensao_titular": -3.0,
    "desfalque_multiplo": -4.0,
    # tendencia_positiva_imprensa (+2) e tendencia_negativa_imprensa (-2) passaram a informativos em 07/10/2026
    # (decisão do usuário na análise do concurso 1273): ver AJUSTE_EXTERNO_SINAIS_INFORMATIVOS.
    "sequencia_invicta_destacada": 1.5,
    "sequencia_negativa_destacada": -1.5,
}
# Classificação clube x seleção nacional (ver docs/grade-real-e-prazos-confirmados.md).
# A API da CAIXA não distingue isso nos campos: time brasileiro sempre tem UF
# preenchida; time estrangeiro e seleção nacional vêm os dois sem UF, só com o
# código do país -- por isso a lista abaixo é necessária para separar seleção de
# clube estrangeiro (ex.: "ESPANHA" é seleção, "BARCELONA" é clube, mas os dois
# vêm com siglaPaisUm="ESP" e siglaUFUm vazio). Lista extensível, sem acento,
# maiúscula -- a comparação normaliza o nome recebido antes de checar.
NOMES_SELECOES_NACIONAIS = {
    "INGLATERRA", "ESPANHA", "DINAMARCA", "PAIS DE GALES", "SERVIA", "HOLANDA",
    "GIBRALTAR", "ANDORRA", "NORUEGA", "PORTUGAL", "ISRAEL", "IRLANDA",
    "ALEMANHA", "GRECIA", "BRASIL", "ARGENTINA", "FRANCA", "ITALIA", "BELGICA",
    "CROACIA", "SUICA", "AUSTRIA", "POLONIA", "UCRANIA", "TURQUIA", "ESCOCIA",
    "IRLANDA DO NORTE", "ISLANDIA", "FINLANDIA", "SUECIA", "RUSSIA", "ROMENIA",
    "BULGARIA", "HUNGRIA", "REPUBLICA TCHECA", "ESLOVAQUIA", "ESLOVENIA",
    "MONTENEGRO", "BOSNIA", "MACEDONIA DO NORTE", "ALBANIA", "KOSOVO", "CHIPRE",
    "MALTA", "LUXEMBURGO", "ESTONIA", "LETONIA", "LITUANIA", "BELARUS",
    "MOLDAVIA", "GEORGIA", "ARMENIA", "AZERBAIJAO", "CAZAQUISTAO", "URUGUAI",
    "CHILE", "COLOMBIA", "PERU", "EQUADOR", "PARAGUAI", "BOLIVIA", "VENEZUELA",
    "MEXICO", "ESTADOS UNIDOS", "CANADA", "JAPAO", "COREIA DO SUL", "AUSTRALIA",
    "MARROCOS", "SENEGAL", "NIGERIA", "GANA", "CAMAROES", "TUNISIA", "EGITO",
    "ARGELIA", "AFRICA DO SUL", "ARABIA SAUDITA", "CATAR", "IRA",
    "EMIRADOS ARABES",
}
VARREDURA_DIAS_ANTES_DO_PRAZO = int(os.environ.get("LOTECA_VARREDURA_DIAS_ANTES", "2"))
# Leituras de notícia por concurso: a primeira até 2 dias antes e a segunda no dia do prazo (desfalque
# confirmado e escalação; plano aprovado em 07/10/2026). A tarefa agendada roda às 08h e o prazo é às 15h.
VARREDURA_LEITURAS_POR_CONCURSO = int(os.environ.get("LOTECA_VARREDURA_LEITURAS", "2"))
# Hora a partir da qual a segunda leitura (a final) pode rodar no dia do prazo: decisão do usuário em 07/10/2026
# (13h, duas horas antes do prazo das 15h). A tarefa das 8h deixa de fazê-la; a tarefa das 13h faz.
VARREDURA_LEITURA_FINAL_HORA = int(os.environ.get("LOTECA_LEITURA_FINAL_HORA", "13"))
# Versão das regras do filtro de notícias, gravada com cada manchete lida (noticias_lidas). Mudou alguma
# barreira, palavra-chave ou peso? Atualize a data, para a medição separar as manchetes por versão.
VARREDURA_VERSAO_REGRAS = "2026-10-07"

# Veículos prioritários do monitoramento de notícias (lista indicada pelo
# usuário em 27/09/2026). Só os que têm site de notícias entram; TV
# (Globo, Premiere, BandSports) e YouTube não são fonte de dado aqui.
NOTICIAS_FONTES_PRIORITARIAS = [
    ("ge.globo.com", "ge (Globo/SporTV)"),
    ("espn.com.br", "ESPN Brasil"),
]
NOTICIAS_JANELA_DIAS = int(os.environ.get("LOTECA_NOTICIAS_JANELA_DIAS", "10"))
NOTICIAS_MAX_ITENS_POR_FONTE = 6
NOTICIAS_INTERVALO_SEGUNDOS = float(os.environ.get("LOTECA_NOTICIAS_INTERVALO_S", "0.5"))

# Palavra-chave encontrada no título/resumo da notícia -> sinal estruturado
# (chave de AJUSTE_EXTERNO_PESOS). Heurística por palavra-chave, não por
# modelo de linguagem -- ver docs/plano do app sobre essa escolha de
# implementação (sem custo de API paga, auditável, fácil de estender aqui).
VARREDURA_PALAVRAS_CHAVE_PARA_SINAL = {
    "lesionado": "lesao_titular",
    "lesão": "lesao_titular",
    "machucado": "lesao_titular",
    "desfalque": "desfalque_multiplo",
    "desfalques": "desfalque_multiplo",
    "suspenso": "suspensao_titular",
    "suspensão": "suspensao_titular",
    "crise": "tendencia_negativa_imprensa",
    "pressão": "tendencia_negativa_imprensa",
    "queda de rendimento": "tendencia_negativa_imprensa",
    "invicto": "sequencia_invicta_destacada",
    "sequência invicta": "sequencia_invicta_destacada",
    "sequência negativa": "sequencia_negativa_destacada",
    "sem vencer": "sequencia_negativa_destacada",
    # Fase Q1 (30/09/2026): sinais INFORMATIVOS -- ver AJUSTE_EXTERNO_SINAIS_INFORMATIVOS.
    "contrata": "contratacao",
    "reforço": "contratacao",
    "acerta com": "contratacao",
    "anuncia a chegada": "contratacao",
    "deixa o clube": "saida_de_jogador",
    "rescinde": "saida_de_jogador",
    "rescisão": "saida_de_jogador",
    "é vendido": "saida_de_jogador",
    "negociado com": "saida_de_jogador",  # "emprestado" ficou de fora: vale para chegada e para saída
    "demite": "troca_de_tecnico",
    "demitido": "troca_de_tecnico",
    "novo técnico": "troca_de_tecnico",
    "novo treinador": "troca_de_tecnico",
    "técnico interino": "troca_de_tecnico",
    "treinador interino": "troca_de_tecnico",
    "deixa o comando": "troca_de_tecnico",
    "salários atrasados": "atraso_salarial",
    "salário atrasado": "atraso_salarial",
    "salários em atraso": "atraso_salarial",
    "atraso salarial": "atraso_salarial",
    "atraso de salário": "atraso_salarial",
    "atraso nos salários": "atraso_salarial",
    "crise financeira": "atraso_salarial",
    "transfer ban": "atraso_salarial",
    "impedido de registrar": "atraso_salarial",
}

# Sinais que entram só como INFORMAÇÃO: aparecem na tela com manchete e link,
# mas não mexem no percentual (peso zero). Ninguém mediu ainda para que lado
# eles puxam o resultado (técnico novo às vezes melhora, às vezes piora); dar
# um peso agora seria inventar número. A Fase Q4 mede a associação com o
# desempenho seguinte antes de qualquer peso (decisão de 30/09/2026).
AJUSTE_EXTERNO_SINAIS_INFORMATIVOS = {
    "contratacao": "Contratação",
    "saida_de_jogador": "Saída de jogador",
    "troca_de_tecnico": "Troca de técnico",
    "atraso_salarial": "Atraso de salário ou crise financeira",
    # Decisão do usuário (07/10/2026, análise do concurso 1273): crise ou pressão relatada pela imprensa não é
    # desfalque confirmado; no 1273, Portugal perdeu 5 pontos por crise e venceu. Fica só como contexto até a
    # associação ser medida.
    "tendencia_negativa_imprensa": "Crise ou pressão relatada pela imprensa",
    "tendencia_positiva_imprensa": "Elogio da imprensa",
    # Manchete especulativa ("pode ser suspenso", "pode ter desfalques"): o fato ainda não aconteceu.
    "lesao_possivel": "Possível lesão (não confirmada)",
    "suspensao_possivel": "Possível suspensão (não confirmada)",
    "desfalque_possivel": "Possíveis desfalques (não confirmados)",
}
# Sinal de fato confirmado -> sinal informativo correspondente quando a manchete é só especulação.
VARREDURA_SINAL_ESPECULATIVO = {
    "lesao_titular": "lesao_possivel",
    "suspensao_titular": "suspensao_possivel",
    "desfalque_multiplo": "desfalque_possivel",
}
VARREDURA_PALAVRAS_ESPECULATIVAS = (
    "pode ser", "pode ter", "pode perder", "pode desfalcar", "pode ficar fora", "pode nao", "pode não",
    "deve desfalcar", "risco de", "ameaca", "ameaça", "ameacado", "ameaçado", "duvida", "dúvida",
)
# Sinais que dependem de qual partida é: manchete que cita outro jogo não vale para este concurso.
VARREDURA_SINAIS_DO_JOGO = ("lesao_titular", "suspensao_titular", "desfalque_multiplo",
                            "lesao_possivel", "suspensao_possivel", "desfalque_possivel")
# Sinais sem dono claro quando a manchete cita os dois times da mesma partida.
VARREDURA_SINAIS_AMBIGUOS_ENTRE_RIVAIS = ("sequencia_invicta_destacada", "sequencia_negativa_destacada",
                                         "tendencia_negativa_imprensa", "tendencia_positiva_imprensa")
# Seleção não contrata, não vende nem atrasa salário: esses sinais são ignorados para seleção.
VARREDURA_SINAIS_SO_DE_CLUBE = ("contratacao", "saida_de_jogador", "atraso_salarial")

# Se qualquer uma dessas expressões aparece no título, a notícia inteira é
# descartada como sinal -- ela nega ou reverte o problema, em vez de
# confirmá-lo (ex.: "sem lesão" contém a palavra-chave "lesão", mas quer dizer
# o oposto de lesao_titular). Lista deliberadamente simples (substring, não
# NLP) -- ver docs/avaliacao-plano-tecnico-29-09-2026.md sobre a escolha de
# não usar modelo de linguagem pago na v1.
VARREDURA_PALAVRAS_DE_NEGACAO = (
    "sem lesao", "sem lesão", "recuperado", "recuperada", "volta aos treinos",
    "de volta aos treinos", "esta de volta", "está de volta", "liberado",
    "liberada", "reintegrado", "reintegrada", "treina normalmente",
    "treinou normalmente", "nao e duvida", "não é dúvida", "descarta lesao",
    "descarta lesão", "fora de duvida", "fora de dúvida",
    # Fase Q1: negam ou desfazem contratação, saída, troca de técnico ou atraso.
    # Só expressões longas: "nega" sozinho bateria em "negativa".
    "desmente", "nega a contratação", "nega contratação", "descarta a contratação",
    "descarta contratação", "nega interesse", "descarta saída", "nega saída",
    "segue no clube", "permanece no clube", "fica no clube", "mantém o técnico",
    "mantém técnico", "salários em dia", "quita salários", "quita os salários",
    "paga os salários",
)

# Manchete sobre OUTRA equipe do mesmo clube é descartada inteira: a Loteca
# usa o futebol profissional masculino. Achado na leitura de teste com
# notícia real (30/09/2026): "jogadoras do Ceará paralisam treinos" e "novo
# técnico do futebol feminino do Sport" viravam sinal do time da Loteca.
VARREDURA_PALAVRAS_DE_OUTRA_EQUIPE = (
    "feminino", "feminina", "jogadoras", "sub-20", "sub-17", "sub-23", "sub 20",
    "sub 17", "categorias de base", "futsal", "futebol de areia", "e-sports", "esports",
)

# Sugestão de marcação (seco/duplo/triplo) -- ver stats/sugestao.py sobre
# qual das 3 propostas conflitantes da pesquisa foi escolhida como padrão.
SUGESTAO_LIMIAR_SECO = float(os.environ.get("LOTECA_LIMIAR_SECO", "65.0"))
SUGESTAO_LIMIAR_DUPLO = float(os.environ.get("LOTECA_LIMIAR_DUPLO", "45.0"))

# Máximo oficial de apostas por bilhete (Manual de Produtos v21, item 6.3.3).
BILHETE_MAX_APOSTAS = 864

# Análise do palpite (stats/analise_palpite.py; item 20, aprovado pelo usuário
# em 29/09/2026). Tudo por regra sobre os percentuais já calculados.
ANALISE_LIMIAR_ZEBRA = float(os.environ.get("LOTECA_LIMIAR_ZEBRA", "25.0"))  # % abaixo do qual a marcação é zebra (decisão do usuário)
ANALISE_LIMIAR_EQUILIBRADO = SUGESTAO_LIMIAR_DUPLO  # favorito abaixo disso = jogo equilibrado (mesmo corte que vira triplo na sugestão)
ANALISE_QUANTOS_MELHORES_DUPLOS = 3  # quantos jogos mostrar em "onde um duplo rende mais"
ANALISE_DIFERENCA_PARA_TROCA_PP = 10.0  # p.p. a mais de chance para sugerir mudar um duplo de jogo
ANALISE_AMOSTRA_MINIMA = 30  # marcações conferidas antes de mostrar uma taxa de acerto no histórico
# Estudo das sugestões para jogos complexos (E1 a E4, 30/09/2026). Só estudo: nada vai
# para a tela antes de o usuário ver o resultado do teste com os concursos passados.
OTIMIZACAO_MARGEM_APERTADA_PP = 10.0  # 1º e 2º resultado com diferença menor que isso = jogo apertado
OTIMIZACAO_GANHO_MINIMO_RELATIVO = 0.10  # só sugere troca que aumente a chance de 14 em 10% ou mais
OTIMIZACAO_ORCAMENTOS_TESTE = ((1, 0), (0, 1), (2, 0), (3, 0), (1, 1), (2, 1), (4, 1), (3, 2))  # (duplos, triplos)
# Sugestões e calibração na tela (recomendações do estudo E1-E4 aprovadas pelo usuário em 30/09/2026).
CALIBRACAO_MIN_CONCURSOS = 200  # concursos completos testados antes de mostrar "o que aconteceu de fato"
SUGESTOES_MAX_TROCAS = 3  # quantas sugestões de alteração pelo mesmo custo mostrar
SUGESTOES_MAX_ECONOMIAS = 2  # quantas leituras de economia mostrar
VERSOES_MAX_POR_CONCURSO = 20  # versões do palpite guardadas por concurso (decisão do usuário: gravadas no banco)
VERSOES_CONCURSOS_MINIMOS = 10  # concursos com mais de uma versão antes de tirar conclusão sobre as mudanças
# Motivos opcionais da marcação: o que o usuário sabe e o app não coleta.
ANALISE_MOTIVOS = (
    "Técnico novo",
    "Clássico ou rivalidade",
    "Time poupado",
    "Desfalque ou lesão",
    "Mando de campo",
    "Fase do time",
    "Intuição",
    # Plano v2, item D3 (07/10/2026): para separar quando a sua leitura acerta mais que a do app.
    "Notícia da semana",
    "Poucos dados (cobertura baixa)",
)

# Ficha do time (stats/competicao.py)
COMPETICAO_JANELA_MOVEL = int(os.environ.get("LOTECA_JANELA_MOVEL", "5"))  # jogos da média móvel
COMPETICAO_SEQUENCIA_MINIMA = 3  # a partir de quantos jogos uma sequência vira destaque
COMPETICAO_DIFERENCA_RELEVANTE_PP = 10.0  # p.p. entre aproveitamento recente e da temporada

# Zonas de classificação por (serie, ano), conforme o Regulamento Específico da
# Competição (REC) de cada série -- lido em 29/09/2026, nunca por suposição (ver
# stats/contexto.py e docs/fontes-oficiais/REC_Brasileiro_Serie_{A,B}_2026.pdf,
# Capítulo 2). Série/ano sem entrada aqui não recebe selo de zona.
ZONAS_CBF = {
    ("serie-a", 2026): {
        "libertadores_grupos": range(1, 5),      # 1º a 4º -- REC Série A, Art. 6, a-d
        "libertadores_preliminar": range(5, 6),  # 5º -- Art. 6, e
        "sul_americana": range(6, 12),            # 6º a 11º -- Art. 7
        "rebaixamento": range(17, 21),            # 4 últimos -- Art. 8
    },
    ("serie-b", 2026): {
        "acesso_direto": range(1, 3),      # 1º e 2º -- REC Série B, Art. 5
        "playoff_acesso": range(3, 7),     # 3º a 6º disputam playoff de acesso -- Art. 5 e 13
        "rebaixamento": range(17, 21),     # 4 últimos -- Art. 5
    },
}
# Competições com fases: zona pela posição DENTRO da fase (e do grupo). Lido no REC Série C 2026
# (docs/fontes-oficiais/REC_Brasileiro_Serie_C_2026.pdf, baixado do site da CBF em 07/10/2026 com autorização
# do usuário). Chave: (serie, ano, nome da fase como a CBF publica).
ZONAS_CBF_POR_FASE = {
    ("serie-c", 2026, "1ª Fase"): {
        "classificacao_2a_fase": range(1, 9),   # 8 primeiros vão à 2ª fase -- Art. 15
        "rebaixamento_serie_d": range(19, 21),  # 2 últimos descem para a Série D -- Art. 42
        "_demais": "fora_da_classificacao",     # 9º a 18º: terminam a competição na 1ª fase -- Art. 15
    },
    ("serie-c", 2026, "2ª Fase"): {
        "acesso_e_final": range(1, 2),  # 1º do grupo: acesso à Série B (Art. 5) e vaga na final (Art. 19)
        "acesso_serie_b": range(2, 3),  # 2º do grupo: acesso à Série B (Art. 5)
        "_demais": "fora_do_acesso",    # 3º e 4º do grupo
    },
}

# Jogos de cada time na temporada, por (série, ano), lido no regulamento --
# nunca suposto. Sem cadastro, o painel não projeta o fim da temporada.
# REC Série A 2026, Art. 14, e REC Série B 2026, Art. 11: pontos corridos,
# turno e returno, 19 jogos de ida e 19 de volta.
TEMPORADA_JOGOS_POR_TIME = {
    ("serie-a", 2026): 38,
    ("serie-b", 2026): 38,
}

# Painel comparativo (stats/painel.py; plano v2 aprovado em 29/09/2026).
# Mínimo de jogos na Loteca para um participante entrar no modo livre do
# histórico. Decisão do usuário: 10 por enquanto, podendo aumentar se mais
# informação favorecer a análise.
PAINEL_MIN_JOGOS_LOTECA = 10
PAINEL_MIN_JOGOS_ANO = 3  # ano com menos jogos que isso é sinal fraco na tendência anual
PAINEL_LINHAS_SOBREPOSTAS_MAX = 8  # acima disso, mini-gráficos (um por time) em vez de linhas sobrepostas
PAINEL_JANELA_RECENTE_LOTECA = 10  # jogos do "ritmo recente" no histórico da Loteca
PAINEL_RODADA_TESTE_PROJECAO = 19  # rodada de onde se mede quanto a projeção por ritmo teria errado
# Projeção cautelosa (decisão do usuário, 30/09/2026, depois de medir 13 temporadas completas das Séries A e B):
# o ritmo do time é misturado com a média da liga. Peso do time = jogos / (jogos + k): quanto mais jogos
# disputados, mais vale o ritmo do próprio time. k = 20 fica no meio da faixa 18 a 22 que a validação
# (deixando uma temporada de fora por vez) escolheu em todas as 13 vezes. Erro fora da amostra faltando
# 28, 19 e 10 jogos: 7,5, 5,4 e 3,7 pontos por time, contra 10,1, 5,8 e 3,8 só com o ritmo do time.
PROJECAO_JOGOS_DE_MEDIA_DA_LIGA = 20
PAINEL_ANOS_MINIMOS_RETA = 3  # anos com base mínima para desenhar a reta de tendência anual

# Ano em curso (pedido do usuário, 30/09/2026: "sempre visível, como prioridade").
# Fonte de cada participante, nesta ordem: temporada da CBF do ano, base aberta de
# seleções (jogos do ano), jogos do ano na grade da Loteca.
ANO_CURSO_AMOSTRA_PEQUENA = 5  # menos jogos que isso no ano: marcado como amostra pequena

# Diagnóstico do concurso (plano v2, item D4): "fácil", "médio" ou "difícil" pela POSIÇÃO do concurso entre os
# concursos com ganhador de 14 (ganhadores por milhão arrecadado), em tercis -- sem limiar absoluto inventado.
# Concurso sem ganhador de 14 é "acumulou". Cortes em fração da posição (0 a 1).
REVISAO_CORTE_DIFICIL = 1 / 3
REVISAO_CORTE_FACIL = 2 / 3
ANO_CURSO_ULTIMOS = 5  # quantos resultados recentes mostrar (V/E/D)

# Lançador (iniciar.pyw; plano aprovado em 30/09/2026). As 5 decisões ficaram nas
# opções recomendadas até o usuário dizer outra coisa: janela própria (Edge em modo
# aplicativo, sem dependência nova), atualizar ao abrir, só neste computador, ícone
# simples, não iniciar com o Windows.
LANCADOR_ENDERECO = "127.0.0.1"  # só este computador: outro aparelho da rede não abre o app
LANCADOR_PORTAS = (8700, 8799)  # faixa onde procurar porta livre (a 8600 fica para o desenvolvimento)
LANCADOR_TEMPO_MAX_ESPERA_S = int(os.environ.get("LOTECA_LANCADOR_ESPERA_S", "90"))
LANCADOR_ATUALIZAR_AO_ABRIR = os.environ.get("LOTECA_ATUALIZAR_AO_ABRIR", "1") == "1"
LANCADOR_HORAS_ENTRE_ATUALIZACOES = float(os.environ.get("LOTECA_HORAS_ENTRE_ATUALIZACOES", "12"))
LANCADOR_EDGE = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)

# Seleções (stats/selecoes.py; P1 da priorização estatística, 30/09/2026).
# Base aberta de resultados internacionais (licença CC0-1.0), baixada de
# github.com/martj42/international_results, e a lista curada de nomes.
SELECOES_BASE_CSV = BASE_DIR / "data" / "externos" / "international_results.csv"
SELECOES_NOMES_CSV = BASE_DIR / "data" / "selecoes-nomes.csv"
# Força por Elo. Estes valores seguem a convenção dos sistemas Elo de futebol de
# seleções (não conferida nesta sessão); são PARÂMETROS, e quem decide se servem é
# o teste jogo a jogo contra o resultado real (stats/selecoes.backtest_selecoes).
ELO_RATING_INICIAL = 1500.0
ELO_VANTAGEM_MANDANTE = 100.0  # pontos de Elo somados a quem joga em casa (só se o campo não é neutro)
ELO_K = {  # quanto um jogo mexe no rating, por tipo de torneio
    "copa_do_mundo": 60.0,
    "continental": 50.0,
    "eliminatorias_e_liga_das_nacoes": 40.0,
    "outros": 30.0,
    "amistoso": 20.0,
}
ELO_TORNEIOS_CONTINENTAIS = {  # nomes como aparecem na base, em minúsculas
    "uefa euro", "copa américa", "african cup of nations", "afc asian cup", "gold cup",
    "confederations cup", "oceania nations cup", "concacaf championship",
}
# Elo de clubes com os jogos da própria Loteca (sugestão S2, aprovada em 07/10/2026). Valores de convenção,
# fixados ANTES do teste e não ajustados ao resultado; o ajuste do K é a variação S3, testada à parte.
ELO_CLUBES_ATIVO = os.environ.get("LOTECA_ELO_CLUBES", "1") == "1"
ELO_CLUBES_RATING_INICIAL = 1500.0
ELO_CLUBES_K = 20.0
ELO_CLUBES_VANTAGEM_MANDANTE = 65.0
# Margem de gols no ajuste do rating (variação V1, aprovada no estudo S3 de 08/10/2026: ganho +0,0014, q 0,014).
# K ajustado, pi-ratings e jogos da CBF no rating não passaram no critério e não entram.
ELO_CLUBES_MARGEM_DE_GOLS = os.environ.get("LOTECA_ELO_MARGEM", "1") == "1"
ELO_CLUBES_TESTE_DESDE = 2020  # o estudo testa de 2020 em diante (mesma janela do modelo da temporada)
CONFIABILIDADE_DESDE_ANO = 2020  # a página mede o app de hoje desde este ano (todas as peças do modelo existem)
ELO_CLUBES_JOGOS_POUCOS = 10  # time com menos jogos da Loteca no rating: cobertura "baixa" (aviso de alta incerteza)
SELECOES_TREINO_DESDE = "1990-01-01"  # o ajuste da curva Elo -> probabilidade usa jogos a partir daqui
SELECOES_CORTE_TESTE = "2010-01-01"  # a curva é ajustada só com jogos ANTES disto; o teste usa jogos DEPOIS
SELECOES_TOLERANCIA_DIAS = 3  # dias de diferença aceitos ao casar um jogo da Loteca com a base
# Modelo dos jogos entre duas seleções: "elo" (força pela base aberta) ou "historico" (o modelo
# anterior, só com os jogos da Loteca). Mudar o padrão exige o teste mostrar ganho; para voltar
# ao anterior: variável de ambiente LOTECA_MODELO_SELECOES=historico.
MODELO_SELECOES = os.environ.get("LOTECA_MODELO_SELECOES", "elo")
# Clubes das Séries A e B na mesma série: modelo da temporada da CBF (stats/modelo_cbf.py), adotado pelo
# usuário em 07/10/2026 depois do estudo B2. "historico" volta ao modelo anterior (Poisson da Loteca).
MODELO_CLUBES = os.environ.get("LOTECA_MODELO_CLUBES", "retrospecto_cbf")

# Ficha do time: abaixo disso, a amostra é sinalizada como pequena (baixa confiança)
FICHA_AMOSTRA_PEQUENA = 10

# Modelo experimental da temporada (stats/modelo_temporada.py): peso do prior, em
# "jogos de um time médio"; parâmetro a calibrar no backtest (etapa B3).
MODELO_TEMPORADA_PESO_PRIOR = float(os.environ.get("LOTECA_MODELO_PESO_PRIOR", "4.0"))

# Forma recente -- quantidade de jogos considerados
FORMA_JANELA_JOGOS = int(os.environ.get("LOTECA_FORMA_JANELA", "8"))

# Estudo de associação (stats/associacao.py, Fase Q4/P3). Limiares fixados ANTES de ver o resultado,
# para não ajustar o critério ao achado; mudar um deles exige registrar o motivo no relatório.
# Método: o fator "melhora a previsão fora da amostra?" (treino nas outras temporadas, teste na temporada
# deixada de fora). A 1ª versão comparava dentro do time com permutação de rótulos e foi descartada em
# 01/10/2026: o fator é calculado do histórico do próprio time, o que cria viés negativo e valor p inflado.
ASSOCIACAO_AMOSTRA_MINIMA = 30  # jogos por grupo (com e sem o fator); abaixo, "amostra insuficiente"
ASSOCIACAO_REPETICOES_BOOTSTRAP = 2000  # reamostragens de times na temporada, para o ganho de previsão
ASSOCIACAO_REPETICOES_COEFICIENTE = 500  # idem, para o intervalo do coeficiente (refaz o ajuste a cada vez)
ASSOCIACAO_NIVEL_SIGNIFICANCIA = 0.05  # aplicado ao valor q (correção de Benjamini-Hochberg entre todos os testes)
ASSOCIACAO_SEMENTE = 20261001  # resultado reprodutível
ASSOCIACAO_JOGOS_ANTERIORES_MINIMOS = 5  # só entra o jogo com pelo menos 5 jogos do time antes dele na temporada
ASSOCIACAO_FORMA_JANELA = 5  # forma = pontos por jogo nos 5 jogos anteriores
ASSOCIACAO_FORMA_BOA = 2.0  # pontos por jogo >= isto
ASSOCIACAO_FORMA_RUIM = 0.8  # pontos por jogo <= isto
ASSOCIACAO_SEQUENCIA_MINIMA = 3  # 3 vitórias seguidas / 3 jogos seguidos sem vencer
ASSOCIACAO_ZONA_TAMANHO = 4  # "topo" = 4 primeiros; "fundo" = 4 últimos, pela tabela da rodada anterior
# Fatores acrescentados em 01/10/2026 (limiares fixados antes de ver o resultado):
ASSOCIACAO_DESCANSO_CURTO_DIAS = 3  # jogo a até 3 dias do anterior; datas fora de ordem (jogo adiado) ficam de fora
ASSOCIACAO_RETA_FINAL_A_PARTIR_DA_RODADA = 29  # as 10 últimas das 38 rodadas das Séries A e B
# Força do adversário (pontos por jogo dele até o jogo) entra como CONTROLE do modelo base, não como fator.

# Teste do modelo por competição (B2, stats/backtest_competicao.py): três modelos de 1/X/2 contra a
# frequência simples, andando no tempo (treino só em anos anteriores ao testado).
B2_JOGOS_ANTERIORES_MINIMOS = 5  # os dois times com pelo menos 5 jogos já conhecidos na temporada
B2_REPETICOES_BOOTSTRAP = 2000
B2_SEMENTE = 20261002

# Calibração aplicada nos percentuais do app (E4, Fase 2, aprovada pelo usuário em 01/10/2026): clubes e
# frequência simples são corrigidos; o Elo das seleções NÃO (o estudo mostrou que a correção não ajuda).
# Para voltar ao cálculo anterior: variável de ambiente LOTECA_CALIBRACAO=0.
CALIBRACAO_ATIVA = os.environ.get("LOTECA_CALIBRACAO", "1") == "1"
CALIBRACAO_ORIGENS_APLICADAS = ("poisson", "frequencia_global")

# Calibração dos percentuais (E4, stats/calibracao.py), fixada antes de ver o resultado (01/10/2026).
# Correção: q ∝ p^expoente (expoente < 1 achata percentuais confiantes demais), misturada com a frequência
# simples: q = mistura * q + (1 - mistura) * frequência. Expoente 1 e mistura 1 = sem correção.
# Método principal (pré-definido): expoente e mistura juntos; os dois isolados aparecem só para comparação.
CALIBRACAO_GRADE_EXPOENTE = tuple(round(0.05 * i, 2) for i in range(0, 31))  # 0,00 a 1,50
CALIBRACAO_GRADE_MISTURA = tuple(round(0.05 * i, 2) for i in range(0, 21))  # 0,00 a 1,00
CALIBRACAO_REAJUSTE_A_CADA = 25  # concursos: os parâmetros são reajustados com o passado a cada bloco
CALIBRACAO_MINIMO_JOGOS = {"poisson": 500, "frequencia_global": 500, "elo_selecoes": 150}  # treino mínimo por origem
CALIBRACAO_REPETICOES_BOOTSTRAP = 2000
CALIBRACAO_SEMENTE = 20261004
# Bilhetes usados para conferir a chance (duplos, triplos, como as colunas são escolhidas):
# "regra" = colunas de maior percentual, múltiplos nos jogos mais incertos (como a sugestão do app);
# "sorteada" = jogos e colunas sorteados, para testar também marcações contra o favorito.
CALIBRACAO_BILHETES_DE_TESTE = (
    (1, 0, "regra"), (0, 1, "regra"), (3, 0, "regra"), (2, 1, "regra"), (5, 3, "regra"),
    (1, 0, "sorteada"), (3, 0, "sorteada"), (2, 1, "sorteada"),
)

# Estudo anti-manada (Q7, stats/anti_manada.py): concursos com mais jogos fora da coluna 1 têm menos
# ganhadores de 14 acertos, descontadas a arrecadação e a época?
Q7_PERMUTACOES = 5000
Q7_REPETICOES_BOOTSTRAP = 2000
Q7_SEMENTE = 20261003
Q7_CONCURSOS_MINIMOS_POR_ANO = 10  # ano com menos concursos úteis fica fora do cálculo estratificado
Q7_FAIXAS_DE_JOGOS_FORA_DA_COLUNA_1 = ((0, 4), (5, 6), (7, 8), (9, 14))  # só para a tabela descritiva

# Aviso de responsabilidade (ver docs/carta-servicos-caixa-oficial.md e
# docs/pesquisa-complementar-27-09.md -- certificação WLA nível 3 e Soto Costa 1980)
AVISO_RESPONSABILIDADE = (
    "A Loteca é uma loteria regulada pela CAIXA -- jogo de azar. Os percentuais "
    "aqui exibidos são estimativa estatística histórica, não previsão nem garantia "
    "de resultado. A CAIXA Loterias possui certificação Nível 3 (de 4) em Jogo "
    "Responsável pela World Lottery Association. Uso restrito a maiores de 18 anos, "
    "com recursos que você pode perder."
)

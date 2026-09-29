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
]
CBF_INTERVALO_SEGUNDOS = float(os.environ.get("LOTECA_CBF_INTERVALO_S", "2.0"))
CBF_TIMEOUT_SEGUNDOS = 30
CBF_VALIDADE_HORAS = int(os.environ.get("LOTECA_CBF_VALIDADE_H", "20"))
CBF_USER_AGENT = "Mozilla/5.0 (compatible; LotecaAssistenteLocal/1.0; uso pessoal)"
# Palavras que não ajudam a comparar nome de time da CBF com o da Loteca
CBF_TOKENS_IGNORADOS = {"SAF", "FC", "S", "A", "F", "DE", "DA", "DO", "EC"}

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
    "tendencia_positiva_imprensa": 2.0,
    "tendencia_negativa_imprensa": -2.0,
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
}

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
# Motivos opcionais da marcação: o que o usuário sabe e o app não coleta.
ANALISE_MOTIVOS = (
    "Técnico novo",
    "Clássico ou rivalidade",
    "Time poupado",
    "Desfalque ou lesão",
    "Mando de campo",
    "Fase do time",
    "Intuição",
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
PAINEL_ANOS_MINIMOS_RETA = 3  # anos com base mínima para desenhar a reta de tendência anual

# Ficha do time: abaixo disso, a amostra é sinalizada como pequena (baixa confiança)
FICHA_AMOSTRA_PEQUENA = 10

# Modelo experimental da temporada (stats/modelo_temporada.py): peso do prior, em
# "jogos de um time médio"; parâmetro a calibrar no backtest (etapa B3).
MODELO_TEMPORADA_PESO_PRIOR = float(os.environ.get("LOTECA_MODELO_PESO_PRIOR", "4.0"))

# Forma recente -- quantidade de jogos considerados
FORMA_JANELA_JOGOS = int(os.environ.get("LOTECA_FORMA_JANELA", "8"))

# Aviso de responsabilidade (ver docs/carta-servicos-caixa-oficial.md e
# docs/pesquisa-complementar-27-09.md -- certificação WLA nível 3 e Soto Costa 1980)
AVISO_RESPONSABILIDADE = (
    "A Loteca é uma loteria regulada pela CAIXA -- jogo de azar. Os percentuais "
    "aqui exibidos são estimativa estatística histórica, não previsão nem garantia "
    "de resultado. A CAIXA Loterias possui certificação Nível 3 (de 4) em Jogo "
    "Responsável pela World Lottery Association. Uso restrito a maiores de 18 anos, "
    "com recursos que você pode perder."
)

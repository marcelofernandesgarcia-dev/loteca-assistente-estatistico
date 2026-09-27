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

# Regras de apuração (ver docs/manual-produtos-caixa-v21.md, item 10)
# Concurso mais antigo confirmado na API é o nº 1 (18/02/2002).
PRIMEIRO_CONCURSO = 1

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

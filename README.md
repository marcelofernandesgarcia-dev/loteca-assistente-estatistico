# Loteca — Assistente Estatístico

Aplicativo local (instalado na máquina, não exposto à internet) para acompanhamento estatístico da Loteca (loteria esportiva de prognóstico da CAIXA — resultado 1/X/2 em 14 jogos por concurso), pensado para uso numa lotérica.

Projeto pessoal, sem vínculo institucional. Ver `CLAUDE.md`.

**Objetivo declarado (governa todo o app):** por se tratar de jogo de azar, o app existe para fortalecer a análise e reduzir risco e erro na escolha do apostador — nunca para prometer ou garantir resultado.

## Instalação e uso

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Rodar a interface (abre no navegador em `http://localhost:8501`):

```bash
.venv\Scripts\streamlit run app/main.py
```

Rodar os testes:

```bash
.venv\Scripts\pytest tests/
```

Importar histórico (opcional — o app já bootstrapa com `data/loteca-historico-valorfinal.csv` na primeira execução; para dado por clube/placar completo, importar da API da CAIXA):

```python
import db
from importer.caixa_client import importar_historico
db.inicializar_schema()
with db.sessao() as conexao:
    importar_historico(conexao)  # concurso 1 até o vigente -- leva alguns minutos
```

## Estrutura

- `importer/` — cliente da API da CAIXA (rate-limited, incremental) e bootstrap do dataset ValorFinal.
- `stats/` — regra de negócio pura: cálculo de resultado, frequência, forma, percentual histórico (Poisson), sugestão seco/duplo/triplo, desempenho no ano, painel de desempenho por time (`desempenho.py`), fechamento de bolão.
- `externo/` — varredura semanal de notícias (RSS público, sem chave de API; janela de 10 dias; veículos prioritários ge/Globo-SporTV e ESPN Brasil, ver `docs/fontes-de-noticias.md`) e cálculo do ajuste externo limitado.
- `importer/cbf_client.py`, `importer/cbf_mapeamento.py`, `stats/cbf.py`, `scripts/coleta_cbf.py` — leitura das páginas públicas da CBF, pareamento com os times da Loteca (UF + nome) e consultas.
- `app/` — páginas Streamlit (Concurso atual com 3 cards, Por concurso, Por time como painel com gráficos, Fechamento de bolão), sem lógica de negócio própria.
- `tests/` — pytest para `stats/`, `externo/` e um teste de integração leve contra a API real.
- `scripts/varredura_semanal.py` — ponto de entrada para o Agendador de Tarefas do Windows.
- `config.py` — todos os parâmetros (rate-limit, pesos do ajuste externo, janela de forma, lista de seleções nacionais).

## Dados oficiais da CBF (Séries A e B)

A CBF não tem API pública documentada; o app lê as **páginas públicas** (classificação, estatísticas e jogos de cada time) como um usuário comum, com intervalo de 2 s entre páginas e sem repetir a coleta em menos de 20 h. Os termos de uso da CBF vedam uso não autorizado do conteúdo -- o uso foi decisão e risco do usuário (ver `docs/cbf-fonte-de-dados.md`). Os dados ficam só no banco local; nada da CBF vai ao GitHub. Para desligar: `LOTECA_CBF_HABILITADO=0`.

Coletar agora: `.venv\Scripts\python scripts\coleta_cbf.py` (`--forcar` ignora a validade de 20 h).

Agendar (você mesmo cria; o Claude não altera configuração do sistema) -- segunda, quinta e sexta às 07:30:

```
schtasks /Create /SC WEEKLY /D MON,THU,FRI /ST 07:30 /TN "Loteca - Coleta CBF" /TR "C:\Users\marce\Projetos\loteca-assistente-estatistico\.venv\Scripts\python.exe C:\Users\marce\Projetos\loteca-assistente-estatistico\scripts\coleta_cbf.py"
```

## Varredura semanal de notícias (ajuste externo)

Roda 2 dias antes do prazo de aposta de cada concurso (`config.VARREDURA_DIAS_ANTES_DO_PRAZO`). Busca notícias por participante via RSS público do Google Notícias, extrai sinais estruturados por palavra-chave (lesão, suspensão, desfalque, tendência de imprensa) e aplica um ajuste limitado (`config.AJUSTE_EXTERNO_TETO_PONTOS`) sobre o percentual histórico. Log completo em `fatores_externos`, visível na página "Por time".

**Decisão de implementação:** a v1 usa palavra-chave sobre notícia real (RSS), não um modelo de linguagem pago — auditável, sem custo de API de terceiro. Se quiser trocar por leitura de IA depois, o ponto de extensão é `externo/analise.py`.

Para agendar (Windows, roda mesmo com o app fechado — crie você mesmo, o Claude não altera configuração do sistema):

```
schtasks /Create /SC DAILY /ST 08:00 /TN "Loteca - Varredura Semanal" /TR "C:\Users\marce\Projetos\loteca-assistente-estatistico\.venv\Scripts\python.exe C:\Users\marce\Projetos\loteca-assistente-estatistico\scripts\varredura_semanal.py"
```

(Roda diariamente, mas o script só faz algo nos dias em que algum concurso está a 2 dias do prazo — ver `externo.varredura.concurso_alvo_da_semana`.)

## Escopo definido com o usuário (27/09/2026, revisado)

- **Uso:** aplicativo de monitoramento e análise estatística — não é uma ferramenta de "palpite", e sim de orientação baseada em probabilidade e no histórico de cada participante (clube ou seleção nacional).
- **Percentual de vitória:** calculado por participante em cada jogo (método Poisson sobre o histórico próprio), ajustado por uma varredura semanal de notícias/análises externas, limitada e auditável.
- **Fonte de dados dos concursos:** endpoint não-oficial da CAIXA (dado por clube/placar) + dataset aberto ValorFinal (bootstrap rápido do 1/X/2 geral) — ver `docs/pesquisa-fontes-dados.md`.
- **Canais oficiais de acompanhamento:** https://loterias.caixa.gov.br/Paginas/Programacao-Loteca.aspx e https://loterias.caixa.gov.br/Paginas/default.aspx.

## Status atual

App funcional (v1): importador, banco SQLite, motor estatístico (frequência, forma, percentual Poisson, fechamento de bolão), camada de ajuste externo por notícias e as 4 páginas Streamlit. Testado localmente com dado real (47 concursos importados, varredura semanal executada, 17 testes automatizados passando). Toda a pesquisa que fundamenta as regras de negócio está em `docs/` e no cofre Obsidian (`Loteca/`). Plano completo em `C:\Users\marce\.claude\plans\velvety-toasting-squid.md`.

**Fora do escopo da v1 (decisão deliberada):** odds de mercado, suporte a Lotogol, enriquecimento com escalação oficial detalhada.

## Aviso importante

Loteca é loteria regulada pela CAIXA — jogo de azar. As análises deste projeto são estatística histórica e probabilidade, nunca previsão garantida de resultado. A CAIXA Loterias possui certificação Nível 3 (de 4) em Jogo Responsável pela World Lottery Association.

## Próximos passos

Ver pendências no cofre Obsidian Cerebro Pessoal (`Loteca/02 - Pendências.md`) para a lista viva de decisões pendentes (ex.: importação histórica completa, refinar regras de prorrogação/suspensão no importador).

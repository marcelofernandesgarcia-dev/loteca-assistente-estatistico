# Dados de fontes abertas

## international_results.csv

- **Fonte:** projeto público `martj42/international_results` no GitHub (resultados de partidas internacionais de futebol masculino).
- **Licença:** CC0-1.0 (domínio público). Uso livre, sem restrição.
- **Baixado em:** 30/09/2026. Cobre 1872 a 26/08/2026 (49.547 jogos).
- **Uso no app:** força das seleções por Elo (`stats/selecoes.py`). Ver `docs/p1-selecoes-elo-30-09-2026.md`.

Atualizar (o app relê o arquivo a cada hora, ou ao reiniciar):

```bash
curl -L -o data/externos/international_results.csv https://raw.githubusercontent.com/martj42/international_results/master/results.csv
```

Depois de atualizar, rodar `pytest tests/test_selecoes.py`: um teste confere que todos os nomes de `data/selecoes-nomes.csv` continuam existindo na base.

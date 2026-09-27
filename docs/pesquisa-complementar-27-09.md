# Pesquisa complementar (27/09/2026) — links, dataset aberto e relatório consolidado

Estado vivo desta nota fica no cofre Obsidian Cerebro Pessoal (`Loteca/Notas/Pesquisa complementar - links, dataset aberto e relatório consolidado.md`). Cópia de trabalho abaixo.

## 1. Links sobre o endpoint da CAIXA — confirmado e descartado
- Confirma o padrão já testado (`servicebus2.caixa.gov.br/portaldeloterias/api/<modalidade>[/<concurso>]`), não-oficial, amplamente usado pela comunidade.
- **Testado e descartado:** `.../api/resultados/download?modalidade=X` (citado como forma de baixar planilha completa) devolve 404 para qualquer modalidade testada, inclusive Mega-Sena (`"O documento '<NOME>.xlsx' não foi encontrado."`). Não é viável hoje — mantém-se a importação concurso a concurso.
- **Link morto:** `projetos.cptec.inpe.br/store1234/caixa-loterias-api` → HTTP 404. Não usado.
- **Descartado por não cobrir Loteca:** `apiloterias.com` (pago) e `github.com/guto-alves/loterias-api` (grátis, Heroku) — nenhum lista Loteca entre as modalidades. O app "LFPlus" (LinkedIn, Edson Ferrari) também cobre só as 10 loterias numéricas, com estatística de dezenas que não se aplica ao problema da Loteca.
- **Conclusão:** todo o ecossistema comunitário de APIs/apps de loteria da CAIXA ignora a Loteca — reforça que o uso direto do endpoint da CAIXA é o único caminho disponível, não escolha de conveniência.

## 2. Dataset aberto validado — ValorFinal
`https://valorfinal.com.br/dados/loteria-loteca`, CC BY 4.0. Baixado, hash SHA-256 conferido (`b1794ca3...`), 1.261 concursos (10 ausentes e documentados pelo próprio site). Formato `concurso;data;resultados` (14 caracteres 1/X/2), sem nome de time/placar.

**Validação cruzada:** recontagem própria deu 47,25%/26,20%/26,55% — bate com o benchmark do NotebookLM (47,23%/26,15%/26,62% sobre 1.271 concursos completos; a diferença é exatamente os 10 concursos ausentes). Cópia do arquivo em `data/loteca-historico-valorfinal.csv` deste repositório, com atribuição em `data/README.md`.

**Uso recomendado:** fonte rápida para o 1/X/2 geral (sem risco de bloqueio); não substitui a API da CAIXA para dado por clube (nome/placar), que continua central para o projeto.

## 3. Relatório consolidado do NotebookLM (17 fontes, era 8)

### 3.1 Histórico e normas citadas — não verificado contra o Diário Oficial
Decreto-Lei nº 594/1969 (instituiu a Loteria Esportiva), Decreto nº 66.118/1970 (regulamentou), 1ª rodada 19/04/1970 (Fla-Flu), 13→16 jogos (1987, "A Gorda")→13 (1989, nome "Loteca")→14 (atual). **Confirmar em fonte oficial antes de publicar.**

### 3.2 Benchmark histórico oficial (confirmado por mim)
Coluna 1: 47,23% (8.404 jogos) · Coluna X: 26,15% (4.654) · Coluna 2: 26,62% (4.736), sobre 1.271 concursos completos.

### 3.3 Tabela de probabilidade por faixa — fórmula validada
`Pn = C(14,n) × 2^(14-n)`: 14pts=1 (1 em 4.782.969; 1 em 2.391.485 com 1 duplo), 13pts=28 (1 em 170.820; 1 em 85.410), 12pts=364 (1 em 13.140, não premiado), 11pts=2.912 (1 em 1.673), 10pts=16.016 (1 em 298).

### 3.4 Extremos históricos (não verificados por mim)
Maior prêmio: R$ 12.541.271,96 (concurso 1210, 08/09/2025, 868 ganhadores). Maior prêmio solo: R$ 6.206.587,13 (concurso 943, 28/06/2021). Menor prêmio: R$ 32,67 (concurso 256, 19/03/2007, 7.792 ganhadores).

### 3.5 Modelo de pesos final — ainda depende de odds de mercado
Terceira proposta de pesos vista (as outras duas estão em `docs/metodologia-estatistica-material-usuario.md`): Mando de Campo 20% · xG 15% · Defensivo/Clean Sheets 12% · **Odds de mercado 12%** · Forma recente 10% · Contexto de tabela 8% · Demanda popular 8% · Desfalques 5% · H2H (resto). Pipeline de 5 fases: Mapeamento → Seleção de secos (5-8) → Matriz (impostores, duplos/triplos) → Filtros (Coluna 1: 5-9, Coluna X: 2-5, Coluna 2: 2-5; 1-3 zebras obrigatórias) → Registro até 14h de sábado.

### 3.6 Fundamentação acadêmica real, verificada
Paulo Henrique Soto Costa (PUC-Rio), "Loteria esportiva: uma aplicação de teoria da decisão", RAE, jun/1980, CC BY 4.0: https://www.scielo.br/j/rae/a/FPc6dvjQWqjvx6ZVVFpKtSv/?format=html&lang=pt — **real e verificado**, mas trata do formato antigo de 13 jogos (3¹³, não 3¹⁴) e valores em Cruzeiro; só o raciocínio se aproveita, não os números. Conclusão do autor: apostar nos favoritos (o que a maioria faz) tem valor esperado PIOR que apostar aleatoriamente; a estratégia "Anti-Manada" (contra o consenso) tem o melhor valor esperado das três, mas mesmo assim não torna o jogo favorável — reforça com peso acadêmico o aviso de responsabilidade já presente no projeto.

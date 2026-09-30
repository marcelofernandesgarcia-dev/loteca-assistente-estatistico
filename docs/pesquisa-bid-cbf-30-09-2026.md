# Pesquisa: BID da CBF como fonte de contratações (Fase Q2, 30/09/2026)

Pedido do usuário: "pode seguir com a pesquisa do BID" (Fase Q2 do estudo de fontes qualitativas, aprovada na rodada 7). Regra da fase: **ler antes de propor, sem codificar**, e trazer o achado antes de decidir coletar. Tudo abaixo foi visto ao vivo nesta data, no navegador, sem login.

## O que é

`https://bid.cbf.com.br` é a "Central de Serviços da DRT" da CBF. A opção **Consultar o BID** (`/home`) dá acesso às "publicações oficiais de registros de atletas no Boletim Informativo Diário". As outras opções (SNR, FIFA TMS, DRT Conecta) são sistemas de gestão para clubes e federações, com login.

## Como a consulta funciona (lido no código público da página)

1. **Filtros:** data (obrigatória, um dia exato por consulta), UF e clube (opcional). A lista de clubes vem de `POST /combo-clubes-json` (clubes de todas as modalidades, inclusive futsal e escolinhas; o Ceará, por exemplo, é "Ceará-CE(20031)").
2. **CAPTCHA obrigatório:** ao clicar em buscar, a página abre uma janela de CAPTCHA (`/get-captcha-base64`). Só depois de resolvê-lo a pesquisa é enviada para `POST /busca-json`.
3. **O que volta, por atleta:** nome completo, apelido, data de nascimento, foto (`/foto-atleta/<código>`), código do atleta, clube, UF, tipo de contrato, número do contrato, data de publicação e data de início.

`robots.txt`: `User-agent: * / Disallow:` (não restringe nada). Mas o CAPTCHA em toda consulta é uma barreira explícita contra acesso automatizado, e ela prevalece sobre o `robots.txt`.

## Conclusão

**A coleta automática do BID não é viável e não será feita.** Três motivos, em ordem de peso:

1. **CAPTCHA em toda consulta.** Automatizar exigiria contornar o CAPTCHA, o que não faço: é a forma de o site dizer que a consulta é para pessoas. Não há API alternativa pública.
2. **Dados pessoais.** Cada resposta traz nome completo, data de nascimento, foto e número de contrato de atletas. O projeto só precisaria de uma contagem ("quantas entradas e saídas o clube teve na semana"), mas, para contar, teria de receber e tratar esses dados pessoais, o que contraria o princípio de minimização já adotado no projeto.
3. **Uma data por consulta.** Acompanhar um clube ao longo da temporada exigiria uma consulta por dia, cada uma com CAPTCHA. Nem manualmente isso é prático em escala (40 clubes).

## O que dá para aproveitar

- **Consulta manual, por link:** o app pode oferecer um link "Consultar o BID (consulta manual, exige CAPTCHA)" perto do time, para o usuário conferir por conta própria uma contratação que viu em notícia. Nada é coletado nem guardado.
- **O sinal de "giro de elenco" continua possível por outras vias já planejadas:**
  - **Q1:** palavras-chave de contratação e saída nas notícias que o app já lê (ge, ESPN Brasil), com as mesmas barreiras do C2;
  - **Q2d:** Transfermarkt (aprovado pelo usuário), que publica transferências por clube. Antes de qualquer coleta, preciso ler os termos de uso completos.
- **Autorização formal:** a pendência antiga "autorização formal à CBF" poderia incluir um pedido de acesso aos dados agregados do BID (contagens por clube, sem dado pessoal). A decisão é do usuário.

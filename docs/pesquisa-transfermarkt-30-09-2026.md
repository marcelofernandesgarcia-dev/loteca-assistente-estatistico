# Pesquisa: termos de uso do Transfermarkt (Fase Q2d, 30/09/2026)

Autorização do usuário (rodada 7 e 30/09/2026): reabrir a decisão de não coletar elenco, **condicionada a ler os termos de uso completos antes de codificar** e trazer o achado. Nada foi coletado nem codificado. Lido ao vivo em `https://www.transfermarkt.com.br/intern/anb` ("Termos e Condições Gerais"), texto integral (16.327 caracteres; o texto está em alemão, com trechos traduzidos para português).

## O que os termos dizem sobre o que interessa

| Cláusula | Conteúdo | Peso para o app |
|---|---|---|
| **3.2** | Todos os direitos sobre programas, serviços, processos, software, tecnologia e **base de dados** pertencem exclusivamente ao Transfermarkt. Reprodução, "para qualquer finalidade", é ilegal. | Reserva a base de dados inteira. |
| **11.1** | O uso dos conteúdos digitais para treinar ou desenvolver IA é proibido, e "as utilizações para **extração de texto e dados (§ 44b UrhG)** estão **expressamente reservadas**". | Reserva explícita da mineração de dados, que é exatamente o que uma coleta automática faz. (O § 44b UrhG é a regra alemã de direitos autorais sobre mineração de texto e dados; a reserva é a forma de o titular proibi-la.) |
| 2.1 | O site pode ser usado sem cadastro. | Não muda o resultado. |

O texto **não** menciona "robô", "raspagem" ou "crawler" com essas palavras, e o `robots.txt` (lido em 29/09/2026) não restringe o acesso geral. Mas a cláusula 11.1 é mais específica que o `robots.txt`: reserva a extração de dados.

## Conclusão

**A coleta automática do Transfermarkt não está autorizada pelos termos.** A situação é diferente da CBF:

- **CBF:** os termos vedam uso não autorizado do conteúdo, de forma geral, e você decidiu assumir o risco conscientemente (registrado em `docs/cbf-fonte-de-dados.md`).
- **Transfermarkt:** há uma **reserva expressa** da extração de dados, o que torna o risco maior e mais direto, e o titular é uma empresa privada que vive da venda desses dados.

Somam-se dois pontos do próprio projeto:

1. **Dado pessoal.** Elenco é nome, data de nascimento e valor de mercado de pessoas identificáveis. O app só precisaria de uma média de idade por time, mas teria de receber e tratar os dados individuais para calculá-la, o que contraria o princípio de coletar só o necessário.
2. **Fragilidade.** Sem API pública, a coleta dependeria do HTML do site, que muda sem aviso.

**Recomendação: não coletar.** A decisão de assumir o risco, como na CBF, é sua; se preferir seguir, registro o risco formalmente antes de qualquer código.

## O que dá para fazer sem coletar

1. **Link de busca por clube, como no BID.** Testado ao vivo: `https://www.transfermarkt.com.br/schnellsuche/ergebnis/schnellsuche?query=<nome do clube>` abre o resultado da busca (por exemplo, "Fortaleza Esporte Clube" leva a "Fortaleza EC"). O app só aponta o caminho; você consulta idade e valor do elenco por conta própria. Nada é coletado nem guardado.
2. **Idade do elenco por fonte oficial.** Ainda não verificado: se as páginas do próprio clube ou as súmulas da CBF trazem elenco com data de nascimento. Se trouxerem, o Q2c (sites oficiais dos clubes) cobre a necessidade.
3. **Pedido de autorização ao Transfermarkt.** A empresa licencia dados (não verifiquei as condições). Um pedido formal cobriria o uso, mas custo e prazo são desconhecidos.
4. **Deixar para depois.** Se a Fase Q4 mostrar que idade e valor do elenco importam pouco para o desempenho, o problema desaparece sozinho.

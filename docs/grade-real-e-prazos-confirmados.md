# Grade real e prazos confirmados — verificação ao vivo (27/09/2026)

Estado vivo no cofre Obsidian (`Loteca/Notas/Grade real e prazos confirmados (fontes oficiais ao vivo).md`). Cópia de trabalho abaixo.

Fontes: página oficial de programação da CAIXA (visitada ao vivo), release oficial CAIXA Notícias (31/07/2026, Loteca do Dia dos Pais), notícia da Extra/Globo (01/06/2026, Copa da Loteca) — links trazidos pelo usuário, abertos e lidos diretamente.

## Grade real do concurso 1272 (ao vivo, 27/09/2026)
14 jogos, misturando futebol de clube nacional (Operário/PR, Ceará/CE, Náutico/PE, Sport/PE, Botafogo/PB, Maringá/PR, Goiás/GO, Atlético/GO, Criciúma/SC, Avaí/SC, CRB/AL, Cuiabá/MT, Fortaleza/CE, Athletic Club/MG) com **seleções nacionais europeias** (Inglaterra x Espanha, Dinamarca x País de Gales, Sérvia x Holanda, Gibraltar x Andorra, Noruega x Portugal, Israel x Irlanda, Alemanha x Grécia) — provavelmente jogos de qualificação para a Copa do Mundo 2026.

**Achado importante para o modelo de dados:** "acompanhar cada clube participante" não é suficiente — quase metade da grade pode ser seleção nacional, com estatística e conceito de "mando de campo" diferentes de um clube. O cadastro de participantes precisa distinguir clube de seleção.

## Prazo de aposta confirmado: 15h (não 14h)
- Concurso 1272 (regular): apostas até 15h de 26/09/2026 (sábado, dia de início dos jogos).
- Loteca especial "Dia dos Pais" (concurso 1265): apostas até 15h de 08/08/2026.
Resolve a suspeita anterior de que "14h de sábado" estava desatualizado — estava, o horário certo é 15h.

## Loteca Especial — premiação com mais detalhe (release "Dia dos Pais")
1ª faixa (90%, 14 acertos) soma: valor da faixa do concurso especial + acumulado do último "final zero/cinco" anterior + acumulado reservado para o especial + acumulado da 1ª faixa do concurso anterior, se houver. Sem 14 acertos, vai para os 13 (2ª faixa, 10%); sem ganhador em nenhuma faixa, acumula para o **próximo concurso regular**. Bolão: preço mínimo R$16, cota mínima R$4, 2–50 cotistas — confirma `data/loteca-boloes-oficial.csv`.

## Copa da Loteca 2026 — datas completas confirmadas
Extra/Globo (01/06/2026): concursos em **17, 22, 25 e 29 de junho de 2026**, apostas de 30/05 a 25/06, prêmio estimado ~R$10 milhões. Fecha a pendência da 4ª data.

## Impacto no projeto
Novo requisito de modelagem: distinguir clube de seleção nacional. Prazo de aposta atualizado para 15h. Datas da Copa da Loteca 2026 completas para uso como período de teste do importador.

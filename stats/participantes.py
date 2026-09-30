"""Rótulos de participantes para listas de escolha (só apresentação, sem acesso a banco)."""
from collections import Counter


def rotulos_de_participantes(participantes) -> dict[str, int]:
    """{rótulo: id} sem colisão. Cada participante tem um id próprio, mas vários clubes
    compartilham o nome (Cruzeiro-MG e Cruzeiro-RS, por exemplo). Se o rótulo fosse só
    "NOME (tipo)", os homônimos virariam a mesma chave e o último vencia: o clube com centenas
    de jogos ficava inalcançável. Por isso:
    - nome único no tipo: "NOME (tipo)";
    - homônimos: "NOME/UF (tipo)", ou "NOME/UF não informada (tipo)" quando não há UF;
    - ainda repetido (mesma UF em duas linhas): acrescenta " #id".
    Cada linha precisa ter `id`, `nome`, `tipo` e `pais_ou_uf`."""
    por_nome = Counter((p["nome"], p["tipo"]) for p in participantes)
    provisorios = []
    for p in participantes:
        if por_nome[(p["nome"], p["tipo"])] == 1:
            rotulo = f"{p['nome']} ({p['tipo']})"
        else:
            local = p["pais_ou_uf"] or "UF não informada"
            rotulo = f"{p['nome']}/{local} ({p['tipo']})"
        provisorios.append((rotulo, p["id"]))
    repetidos = Counter(rotulo for rotulo, _ in provisorios)
    return {
        (rotulo if repetidos[rotulo] == 1 else f"{rotulo} #{participante_id}"): participante_id
        for rotulo, participante_id in provisorios
    }

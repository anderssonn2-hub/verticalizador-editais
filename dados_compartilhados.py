
import re
import unicodedata

DINHEIRO = r"R\$\s*[\d.]+,\d{2}"

def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    return texto.casefold()

def extrair_grupos(paginas):
    grupos = []
    atual = None

    for numero, pagina in enumerate(paginas[:20], 1):
        linhas = pagina.splitlines()

        for indice, linha in enumerate(linhas):
            texto = linha.strip()
            normal = normalizar(texto)

            cabecalho = re.match(
                r"^((?:analista|tecnico)\s+judiciario)"
                r"\s*[-–—]\s*ensino\b",
                normal,
                re.I
            )

            if cabecalho:
                atual = {
                    "grupo": cabecalho.group(1),
                    "salario": None,
                    "taxa": None,
                    "pagina": numero
                }
                grupos.append(atual)

            if atual is None:
                continue

            trecho = " ".join(linhas[indice:indice+4])
            trecho_normal = normalizar(trecho)

            if atual["taxa"] is None:
                m = re.search(
                    r"valor da inscricao\s*:\s*(" + DINHEIRO + ")",
                    trecho_normal,
                    re.I
                )
                if m:
                    atual["taxa"] = m.group(1)

            if atual["salario"] is None:
                m = re.search(
                    r"remuneracao inicial\b[\s\S]{0,160}?("
                    + DINHEIRO + ")",
                    trecho_normal,
                    re.I
                )
                if m:
                    atual["salario"] = m.group(1)

    return grupos

def aplicar_grupos(dados, grupos):
    for nome, info in dados.items():
        nome_normal = normalizar(nome)

        nome_normal = re.sub(
            r"^\s*\d{1,4}\s*[-–—.:)]?\s*",
            "",
            nome_normal
        ).strip()

        correspondentes = [
            g for g in grupos
            if nome_normal.startswith(g["grupo"])
        ]

        if len(correspondentes) != 1:
            continue

        grupo = correspondentes[0]

        for campo in ("salario", "taxa"):
            if not info.get(campo) and grupo[campo]:
                info[campo] = grupo[campo]
                info["paginas"].add(grupo["pagina"])

    return dados

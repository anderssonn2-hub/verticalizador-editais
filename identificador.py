import re
import unicodedata
from difflib import SequenceMatcher


def chave(s):
    return ''.join(
        c for c in unicodedata.normalize('NFD', s.casefold())
        if not unicodedata.combining(c)
    )


def normalizar(s):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', chave(s)).split())


def nome_valido(nome):
    n = normalizar(nome)
    palavras = n.split()

    if len(palavras) < 2 or len(palavras) > 9:
        return False

    if re.search(
        r'\b(?:provimento|concurso|candidato|referido|publico|inscricao)\b',
        n
    ):
        return False

    if n in {
        'policial', 'nivel superior', 'nivel medio',
        'carreira policial', 'cargo publico'
    }:
        return False

    return True


def nomes_equivalentes(a, b):
    na, nb = normalizar(a), normalizar(b)

    if na == nb:
        return True

    pa, pb = na.split(), nb.split()

    if len(pa) != len(pb) or len(pa) < 3:
        return False

    diferencas = [
        (x, y) for x, y in zip(pa, pb) if x != y
    ]

    if len(diferencas) != 1:
        return False

    x, y = diferencas[0]

    if len(x) < 5 or len(y) < 5:
        return False

    return SequenceMatcher(None, x, y).ratio() >= 0.88


def identificar(pgs):
    cargos = {}
    campos = []

    for i, p in enumerate(pgs, 1):
        t = ' '.join(p.split())

        for m in re.finditer(
            r'\b(?:para o cargo de|cargo de|cargo\s*:)\s*([^,;:.]{3,100})',
            t, re.I
        ):
            nome = re.split(
                r'\s+(?:a que|ao qual|da carreira|será|é|deverá|se |'
                r'previsto|para |com |nos termos|e será|do quadro|'
                r'que |pertencente|destinado|no presente)\b',
                m[1], maxsplit=1, flags=re.I
            )[0].strip(' -')

            if not nome_valido(nome):
                continue

            if re.search(r'\d', nome):
                continue

            equivalente = next(
                (k for k, v in cargos.items()
                 if nomes_equivalentes(nome, v['Cargo'])),
                None
            )

            if equivalente is None:
                cargos[normalizar(nome)] = {
                    'Cargo': nome,
                    'Página': i,
                    'Trecho': m.group()
                }

        if i <= 2:
            for m in re.finditer(
                r'^\s*CARGO DE (.{3,80})$', p, re.I | re.M
            ):
                nome = m[1].strip().title()

                if nome_valido(nome):
                    if not any(
                        nomes_equivalentes(nome, v['Cargo'])
                        for v in cargos.values()
                    ):
                        cargos[normalizar(nome)] = {
                            'Cargo': nome,
                            'Página': i,
                            'Trecho': m.group()
                        }

            for m in re.finditer(
                r'TRIBUNAL REGIONAL FEDERAL DA\s+(\d{1,2})'
                r'(?:[. ]?2|[ªºa])?\s+REGIÃO',
                p, re.I
            ):
                numero = m[1]
                numero = (
                    numero[0]
                    if len(numero) == 2 and numero.endswith('2')
                    else numero
                )
                campos.append({
                    'Campo': 'Órgão',
                    'Valor': f'Tribunal Regional Federal da {numero}ª Região',
                    'Página': i,
                    'Trecho': m.group()
                })

        if i <= 15:
            padroes = [
                ('Vagas', r'\b(\d[\d.]*)\s*(?:\([^)]{1,80}\)\s*)?vagas\b'),
                ('Remuneração',
                 r'(?:remuneração(?: inicial)?|vencimento(?:s)?|'
                 r'subsídio|salário)[^.;]{0,100}?(R\$\s*[\d.]+,\d{2})'),
                ('Banca',
                 r'(Fundação\s+Get[uú]lio\s+Vargas|CEBRASPE|CESPE|'
                 r'Fundação Carlos Chagas|VUNESP|Instituto AOCP|'
                 r'IBFC|Instituto ACCESS|Instituto Quadrix|'
                 r'FUNDATEC|Consulplan)'),
                ('Órgão',
                 r'(Polícia Civil (?:do Estado )?de '
                 r'[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+'
                 r'(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+)?)')
            ]

            for campo, pat in padroes:
                flags = re.I if campo != 'Órgão' else 0

                for m in re.finditer(pat, t, flags):
                    campos.append({
                        'Campo': campo,
                        'Valor': m[1],
                        'Página': i,
                        'Trecho': t[max(0, m.start()-65):m.end()+65]
                    })

    return list(cargos.values()), campos

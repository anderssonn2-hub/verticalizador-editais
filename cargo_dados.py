import re
from identificador import chave
from conteudo import canon
from dados_compartilhados import extrair_grupos, aplicar_grupos

MONEY=r'R\$\s*[\d.]+,\d{2}'
def norm(s): return ' '.join(re.sub(r'[^a-z0-9]+',' ',chave(s)).split())
def especial(s):
    n=norm(s); return n.split('especialidade ')[-1] if 'especialidade ' in n else n
def localizar_valor_rotulado(pgs, rotulos, limite=180):
    """Localiza um valor monetário próximo de um rótulo e informa a página."""
    padrao = re.compile(
        r'(?:' + '|'.join(rotulos) + r')'
        r'[\s\S]{0,' + str(limite) + r'}?'
        r'(' + MONEY + r')',
        re.I
    )

    for pagina, texto in enumerate(pgs, 1):
        for match in padrao.finditer(texto):
            trecho = texto[match.start():match.end()]
            if len(re.findall(r'\n', trecho)) > 4:
                continue
            return {
                'valor': match.group(1),
                'pagina': pagina,
                'trecho': trecho
            }

    return None
def extrair_dados(pgs, nomes):
    result={n:dict(salario=None,taxa=None,vagas=None,paginas=set(),codigo=None) for n in nomes}
    def match_name(text):
        t=norm(text); scores=[]
        for n in nomes:
            k=norm(n); e=especial(n); base=' '.join(k.split()[:2]); e=re.sub(r'\b(?:jfsp|jfms|trf3|trf4)\b','',e).strip(); e=re.sub(r'^'+re.escape(base)+r'\s+','',e); e=re.sub(r'^area (?:de )?apoio especializado ','',e)
            if base in t and e and (e in t or (len(e.split())>=3 and re.search(r'\b'+r'\b.{0,65}?\b'.join(map(re.escape,e.split()))+r'\b',t))): scores.append((len(e),n))
            elif canon(n) in canon(text): scores.append((len(canon(n)),n))
        scores.sort(reverse=True)
        return scores[0][1] if scores and (len(scores)==1 or scores[0][0]>scores[1][0]) else None
    for page,p in enumerate(pgs,1):
        # Salary and fee must be explicitly labeled within a cargo heading.
        if page<=8:
            for m in re.finditer(r'(?im)^\s*CARGO DE ([^\n]{3,100})\s*$',p):
                tail=p[m.end():]; tail=re.split(r'(?im)^\s*(?:CARGO DE |\d+\.?\s+DAS? )',tail,maxsplit=1)[0][:1800]
                sal=re.search(r'(?:remunera[cç][aã]o|vencimento|subs[ií]dio|sal[aá]rio)[^\n]{0,100}?('+MONEY+r')',tail,re.I)
                fee=re.search(r'(?:valor|taxa)\s+d[ae]\s+inscri[cç][aã]o\s*:?\s*('+MONEY+r')',tail,re.I)
                if not sal: continue
                base=norm(m[1]); extra=re.search(r'(?:ressalvada|exceto)[\s\S]{0,100}?('+MONEY+r')\s+para\s+a?\s*(?:especialidade|cargo)\s+([^\n]+(?:\n[^\n]+)?)',tail,re.I)
                for n,d in result.items():
                    if not norm(n).startswith(base): continue
                    if extra and re.sub(r'\b(?:jfsp|jfms|trf3|trf4)\b','',especial(n)).strip() in norm(extra[2]): d['salario']=extra[1]
                    elif extra and not re.search(r'\b'+re.escape(especial(n))+r'\b',norm(extra[2])): d['salario']=sal[1]
                    else: d['salario']=sal[1]
                    if fee: d['taxa']=fee[1]
                    d['paginas'].add(page)
        if not re.search(r'n[uú]mero de\s*vagas|total de\s*\|?\s*ampla',p,re.I): continue
        # Coded vacancy rows with total followed by five allocation columns.
        for m in re.finditer(r'(?im)\b(\d{2,3})\s+((?:Analista|T[eé]cnico)[^\n]{2,120}?)\s*\|?\s*\b(\d+|CR)\*?\s+((?:[\d-]+[ \t]*){3,5})',p):
            end=m.end(); following=p[end:end+850]; following=re.split(r'\n[^\n]*\b\d{3}\s+(?:Analista|T[eé]cnico)|\n\s*ANEXO',following,maxsplit=1,flags=re.I)[0]
            n=match_name(m[2]+' '+following)
            if not n: continue
            d=result[n]; v=m[3]; d['codigo']=m[1]; d['paginas'].add(page)
            if d['vagas'] is None: d['vagas']=v
            elif d['vagas']!=v: d['vagas']='Conferir por unidade'
    grupos = extrair_grupos(pgs)
    result = aplicar_grupos(result, grupos)
    return result

def prova_por_cargo(pgs, codigo):
    if not codigo:return None
    for page,p in enumerate(pgs,1):
        for m in re.finditer(r'(?im)^\s*'+re.escape(codigo)+r'\s+[^\n]+',p):
            text=p[m.start():m.start()+650]; text=re.split(r'\n\s*\d{3}\s+|\n\s*\d+\.\d+',text,maxsplit=1)[0]
            total=re.search(r'prova objetiva\s*[:.]?\s*(\d{1,3})\b',text,re.I)
            if not total:continue
            rows=[]
            for label in ['Gerais','Específicos']:
                q=re.search(r'Conhecimentos\s+'+label+r'\s+(\d{1,3})\s+(\d+(?:[,.]\d+)?)\b',text,re.I)
                if q:rows.append({'Grupo':'Conhecimentos '+label.lower(),'Questões':int(q[1]),'Peso':float(q[2].replace(',','.'))})
            if len(rows)!=2 or sum(r['Questões'] for r in rows)!=int(total[1]):rows=[]
            return dict(total=int(total[1]),rows=rows,pagina=page,texto=text)
    return None

def complementar_dados_cargo_unico(pgs, dados):
    """
    Complementa campos ausentes quando existe apenas um cargo.
    Mantem os valores previamente extraidos.
    """
    import re

    if len(dados) != 1:
        return dados

    cargo = next(iter(dados))
    info = dados[cargo]

    if "jornada" not in info:
        info["jornada"] = None

    dinheiro = r"R\$\s*[\d.]+,\d{2}"

    padroes = {
        "salario": (
            r"\b(?:vencimento(?:\s+inicial)?|remunera[cç][aã]o"
            r"(?:\s+inicial)?|subs[ií]dio|sal[aá]rio)\b"
            r"[\s\S]{0,250}?(" + dinheiro + r")"
        ),
        "taxa": (
            r"\b(?:valor\s+(?:da|de)\s+inscri[cç][aã]o"
            r"|taxa\s+de\s+inscri[cç][aã]o)\b"
            r"[^\n]{0,120}?(" + dinheiro + r")"
        ),
        "vagas": (
            r"\bVagas\s*:\s*"
            r"[^\n]{0,150}?\b(\d[\d.]*)\s*"
            r"(?:\([^)]*\)\s*)?vagas\b"
        ),
        "jornada": (
            r"\bJornada\s+de\s+trabalho\s*:\s*"
            r"(\d{1,3})\s*(?:\([^)]*\)\s*)?horas"
            r"(?:\s+semanais)?"
        )
    }

    for campo, padrao in padroes.items():
        if info.get(campo) is not None:
            continue

        for pagina, texto in enumerate(pgs[:15], 1):
            resultado = re.search(padrao, texto, re.I)

            if not resultado:
                continue

            valor = resultado.group(1).strip()

            if campo == "jornada":
                valor += " horas semanais"

            info[campo] = valor
            info["paginas"].add(pagina)
            break

    return dados

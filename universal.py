import re, unicodedata, io, csv
import fitz
from collections import Counter

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn')

def paginas(pdf):
    with fitz.open(stream=pdf,filetype='pdf') as doc:
        return [p.get_text(sort=True) for p in doc]

def localizar(pgs):
    from estrutura import limites
    lim=limites(pgs)
    if lim: return lim
    hits=[i+1 for i,p in enumerate(pgs) if re.search(r'CONTEUDOS? PROGRAMATICOS?|PROGRAMA DE PROVAS|OBJETOS DE AVALIACAO',norm(p))]
    if not hits: return 1,len(pgs)
    start=next((i for i in hits if re.search(r'CONHECIMENTOS (BASICOS|GERAIS|ESPECIFICOS)|LINGUA PORTUGUESA',norm(pgs[i-1]))),hits[-1])
    end=next((i for i in range(start+1,len(pgs)+1) if re.search(r'^\s*ANEXO\s+(?:[IVX]+|\d+)\s*\n\s*(?:EXAMES|MODELO|FORMULARIO|CRONOGRAMA)',norm(pgs[i-1]),re.M)),len(pgs)+1)-1
    return start,max(start,end)

def cargos(pgs):
    from estrutura import opcoes
    opts=opcoes(pgs)
    if opts:return opts
    out=[]
    for p in pgs:
        for line in p.splitlines():
            m=re.match(r'^\s*(?:CARGO|FUNCAO|ESPECIALIDADE)\s*(?:\d+\s*)?[:–—-]\s*(.{3,120})$',norm(line))
            if m:
                name=re.split(r'[:–—-]',line,maxsplit=1)[-1].strip()
                if name not in out: out.append(name)
    return out

def extrair(pgs,start,end,cargo=None):
    from estrutura import opcoes,itens
    if cargo in opcoes(pgs):return itens(pgs,cargo)
    raw='\n'.join(re.sub(r'^\s*\d+\s*$','',p,flags=re.M) for p in pgs[start-1:end])
    heads=list(re.finditer(r'^\s*(?:(\d+)\.[ \t]+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇÜ][A-ZÁÉÍÓÚÂÊÔÃÕÇÜ /(),-]{3,100})\s*:?\s*$',raw,re.M))
    out=[]; discipline=None
    for i,h in enumerate(heads):
        name=h[2].strip(); n=norm(name)
        if re.search(r'^(ANEXO|CONTEUDO|CONHECIMENTOS (BASICOS|GERAIS|ESPECIFICOS)|CARGO|INVESTIGADOR DE POLICIA)',n): continue
        body=' '.join(raw[h.end():heads[i+1].start() if i+1<len(heads) else len(raw)].split())
        if not body: continue
        markers=list(re.finditer(r'(?<![\w.])(\d+(?:\.\d+)+)\.?(?=\s)',body))
        if markers:
            topics=[m[1]+'- '+body[m.end():markers[j+1].start() if j+1<len(markers) else len(body)].strip().rstrip(';') for j,m in enumerate(markers)]
            if body[:markers[0].start()].strip(): topics.insert(0,body[:markers[0].start()].strip())
        else: topics=[x.strip() for x in body.split(';') if x.strip()]
        out.extend({'Disciplina':name,'Assunto':t} for t in topics if t.strip())
    return out

def montar(base,items):
    rows=list(csv.reader(io.StringIO(base.decode('utf-8-sig')),delimiter=';')); header=rows[0]
    port=[r for r in rows[1:] if norm(r[0]).startswith('LINGUA PORTUGUESA')]; prototype=port[0] if port else ['']*len(header)
    out=[header]+port; counts=Counter()
    for item in items:
        d=str(item.get('Disciplina') or '').strip(); t=str(item.get('Assunto') or '').strip()
        if not d or not t or (port and norm(d).startswith('LINGUA PORTUGUESA')): continue
        counts[d]+=1;r=prototype.copy();r[0]=d;r[1]=t;r[10]=str(counts[d]*10);r[9]='';r[15:18]=['','',''];out.append(r)
    b=io.StringIO(newline='');csv.writer(b,delimiter=';').writerows(out);return b.getvalue().encode('utf-8-sig')

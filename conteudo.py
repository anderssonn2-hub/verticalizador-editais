import re
from difflib import SequenceMatcher
from identificador import chave

G='Conhecimentos gerais'; E='Conhecimentos específicos'; U='Classificação não identificada'
CARGO=re.compile(r'^(?:\d{1,3}\s*[-–—]?\s*)?(?:cargo\s+de\s+)?(?:analista|tecnico)\s*,?\s+judiciario\b',re.I)
def canon(s):
    s=chave(s); s=re.sub(r'[^a-z0-9]+',' ',s).strip()
    s=re.sub(r'^(?:\d+ )?(?:cargo de )?','',s)
    s=re.sub(r'\b(?:trf\d+|jf[a-z]{2}|jesp)\b',' ',s)
    s=re.sub(r'\b(?:sem especialidade|de|da|do|especialidade)\b',' ',s)
    return ' '.join(s.split())
def matches(a,b):
    ca=re.match(r'^\s*(\d{1,3})\b',a); cb=re.match(r'^\s*(\d{1,3})\b',b)
    if ca and cb: return ca[1]==cb[1]
    a,b=canon(a),canon(b)
    return bool(a and b and (a==b or abs(len(a)-len(b))<=5 and SequenceMatcher(None,a,b).ratio()>=.94))
def clean(l):
    n=chave(l).strip()
    return not (not n or n.isdigit() or re.match(r'^(diario oficial da uniao|este documento pode|documento assinado|www\s*\.|pcimarkpci)',n))
def heading(l):
    n=chave(l).strip()
    return re.match(r'^(?:anexo\s+[ivxlcd\d|]+\s*[-–—:]?\s*)?(?:conteudos? programaticos?|programa de provas|objetos de avaliacao)\s*[:.]?$',n)
def parse(pgs):
    active=False; group=U; scope=[]; blocks=[]; cargo_list=[]; current=None; pending=None; blank=True; shared=False
    def flush():
        nonlocal current
        if current and current['parts']: blocks.append(current)
        current=None
    for page,p in enumerate(pgs,1):
        for raw in p.splitlines():
            l=raw.strip(); n=chave(l)
            if heading(l): active=True; blank=True; continue
            if not active: continue
            if re.match(r'^anexo\s+[ivxlcd\d|]+\b',n): flush(); return blocks,cargo_list
            if not clean(l):
                if not l: blank=True
                continue
            if re.match(r'^para os cargos? de\b',n):
                flush(); pending=l; scope=[]; blank=True; continue
            gm=re.match(r'^conhecimentos\s+(gerais|basicos|especificos)\b',n)
            if gm:
                flush(); shared=False; group=E if gm[1]=='especificos' else G
                if pending:
                    scope=[x.strip(' ,:-') for x in re.split(r'(?=\b(?:Analista|Técnico)\s+Judiciário)',pending,flags=re.I) if CARGO.match(chave(x.strip()))]; pending=None
                elif group==G: scope=[] if 'todos' in n and 'tecnic' not in n and 'exceto' not in n else [l] if len(n)>25 else []
                else: scope=[]
                blank=True; continue
            if pending is not None: pending+=' '+l; continue
            if CARGO.match(n):
                flush()
                if group==E:
                    name=l.strip(' ,;:'); name=re.sub(r'\s+e$','',name,flags=re.I)
                    if not any(matches(name,x) for x in cargo_list): cargo_list.append(name)
                    scope=scope+[name] if shared else [name]
                    shared=n.endswith(' e')
                elif scope and 'exceto' in chave(scope[0]): scope.append(l)
                blank=True; continue
            if re.match(r'^ensino\s+(superior|medio|fundamental)',n): continue
            if group==U: continue
            # Prefer paragraph beginnings, not colons embedded in wrapped topics.
            m=re.match(r'^([^:]{3,105}):\s*(.*)$',l) if blank or current is None else None
            if m and not re.search(r'[.;!?]|\b(?:lei n|artigos? \d)\b',chave(m[1])):
                flush(); current=dict(Grupo=group,scope=scope.copy(),Disciplina=m[1].strip(),parts=[]); l=m[2]
            elif (blank or current is None) and re.match(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ /-]{3,90}\s+(?=[A-ZÁÉÍÓÚ][a-z])',l):
                m=re.match(r'^([A-ZÁÉÍÓÚÂÊÔÃÕÇ /-]{3,90}?)\s+(?=[A-ZÁÉÍÓÚ][a-z])(.*)$',l)
                if m: flush(); current=dict(Grupo=group,scope=scope.copy(),Disciplina=m[1],parts=[]); l=m[2]
            if current is None: current=dict(Grupo=group,scope=scope.copy(),Disciplina='Disciplina não identificada',parts=[])
            if l: current['parts'].append((page,l))
            blank=False
    flush(); return blocks,cargo_list

def selected(blocks,cargo):
    out=[]
    for b in blocks:
        s=b['scope']; g=b['Grupo']
        if g==E and not s: continue
        if s:
            n=chave(s[0]); ok=any(matches(cargo,x) for x in s)
            if 'exceto' in n: ok=not any(matches(cargo,x) for x in s[1:]) if len(s)>1 else False
            elif 'todos' in n and 'tecnic' in n: ok='tecnico' in chave(cargo)
            if not ok: continue
        text=' '.join(t for _,t in b['parts']); pages=', '.join(map(str,sorted({p for p,_ in b['parts']})))
        # Split only clear sentence endings, preserving punctuation and nested semicolons.
        topics=re.split(r'(?<!\bnº)(?<!\bArt)(?<!\bart)(?<!\bInc)(?<=\.)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])',text)
        out.append(dict(Grupo=g,Disciplina=b['Disciplina'],Assuntos=topics,Páginas=pages))
    return out

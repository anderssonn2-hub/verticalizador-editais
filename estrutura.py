import re
from identificador import chave
from datetime import datetime

def limites(pgs):
    for i,p in enumerate(pgs):
        if re.search(r'^\s*(?:anexo\s+[ivxlcd\d]+\s*\n\s*)?conteudos? programaticos?\s*$',chave(p),re.M):
            for j in range(i+1,len(pgs)):
                if re.match(r'\s*anexo\s+[ivxlcd\d]+\s*\n',chave(pgs[j])): return i+1,j
            return i+1,len(pgs)
    return None

CARGO=re.compile(r'^\s*(\d{2})\s+((?:Analista|Técnico) Judiciário[^\n]*)$',re.I)
def blocos(pgs):
    lim=limites(pgs)
    if not lim:return {}
    out={}; ids=[]; pending=False
    for page,line in ((i+1,l) for i in range(lim[0]-1,lim[1]) for l in pgs[i].splitlines()):
        line=line.strip(); n=chave(line)
        if not line or line.isdigit():continue
        if ids==['exceto'] and re.match(r'^\d{2}\s*[–—-]',line):continue
        if n.startswith('conhecimentos gerais'):
            ids=['tecnicos' if 'tecnicos' in n else 'exceto' if 'exceto' in n else 'todos']; pending=False;continue
        if n=='conhecimentos especificos':ids=[];pending=False;continue
        m=CARGO.match(line)
        if m:
            if ids==['exceto']:continue
            code,name=m.groups(); name=re.sub(r'\s+e$','',name,flags=re.I)
            out.setdefault(code,{'nome':code+' '+name,'linhas':[]})
            ids=ids+[code] if pending else [code];pending=n.endswith(' e');continue
        pending=False
        for code in ids:out.setdefault(code,{'nome':code,'linhas':[]})['linhas'].append((page,line))
    return out

def opcoes(pgs):return [v['nome'] for k,v in blocos(pgs).items() if k.isdigit()]

def itens(pgs,cargo,detalhes=False):
    b=blocos(pgs); code=cargo[:2]; keys=['todos']+(['exceto'] if code not in ('01','02','18') else [])+(['tecnicos'] if 'técnico judiciário' in cargo.lower() else [])+[code]
    result=[]
    for k in keys:
        d='Conhecimentos específicos' if k==code else 'Conhecimentos gerais'; body=[]; pages=set(); grupo=d
        def flush():
            text=' '.join(body).strip()
            if text:
                for t in re.split(r'(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])',text):
                    if t.strip():result.append(dict(Disciplina=d,Assunto=t.strip(),**({'Grupo':grupo,'Páginas':', '.join(map(str,sorted(pages)))} if detalhes else {})))
        for page,l in b.get(k,{}).get('linhas',[]):
            m=re.match(r'^([A-ZÁÉÍÓÚÂÊÔÃÕÇÜ][A-ZÁÉÍÓÚÂÊÔÃÕÇÜ /(),–-]{3,100}?)(?::\s*|\s+(?=[A-ZÁÉÍÓÚ][a-záéíóú]))(.*)$',l)
            if m:
                flush();body=[];pages=set();d=m[1].strip();body.append(m[2]);pages.add(page)
            else:body.append(l);pages.add(page)
        flush()
    return result

def campos_extra(pgs):
    out=[]
    def add(c,v,p,t):out.append(dict(Campo=c,Valor=v,Página=p,Trecho=t))
    for l in pgs[0].splitlines()[:8]:
        if re.match(r'\s*(TRIBUNAL|PREFEITURA|MINISTÉRIO|SECRETARIA|UNIVERSIDADE)\b',l):add('Órgão',l.strip(),1,l.strip());break
    for i,p in enumerate(pgs[:8],1):
        if re.search(r'CR\s*\(2\)',p) and 'Cadastro de Reserva' in ' '.join(pgs[:4]):add('Vagas','Cadastro de reserva',i,'CR(2)');break
    return out

def tabela_datas(pgs):
    out=[]
    for i,p in enumerate(pgs,1):
        if not re.search(r'cronograma',chave(p)):continue
        for l in p.splitlines():
            n=chave(l); ds=re.findall(r'\b\d{1,2}/\d{1,2}(?:/\d{4})?\b',l)
            if not ds or len(ds[-1].split('/'))!=3:continue
            def add(event,s):
                if s.count('/')==1:s+='/'+ds[-1][-4:]
                try:s=datetime.strptime(s,'%d/%m/%Y').strftime('%d/%m/%Y')
                except ValueError:return
                out.append(dict(Evento=event,Data=s,Página=i,Trecho=l.strip()))
            if 'periodo de inscri' in n and len(ds)>=2:add('Início das inscrições',ds[0]);add('Encerramento das inscrições',ds[-1])
            elif 'aplicacao das provas objetivas' in n:add('Data prevista da prova',ds[-1])
    return out

import re
from identificador import chave
from extrator_raiox import DATA
from datetime import date

def consolidar(nomes, campos):
    cargos={}
    for r in nomes:
        k=chave(r['Cargo']).strip()
        if k in {'policial','servidor','publico','efetivo','provimento efetivo'}: continue
        cargos.setdefault(k,r)
    out={}
    for r in campos:
        v=r['Valor']; c=r['Campo']; k=chave(v)
        if c=='Órgão': k=k.replace('do estado de ','de ')
        if c=='Vagas' and not re.fullmatch(r'\d{1,3}(?:\.\d{3})*|\d+',v): continue
        out.setdefault((c,k),r)
    return list(cargos.values()),list(out.values())

def calendario(pgs):
    eventos={}
    def add(event,m,p,t):
        try:
            from extrator_raiox import MESES
            d=date(int(m[3]),int(m[2]),int(m[1])) if m[1] else date(int(m[6]),MESES.index(m[5].lower())+1,int(m[4]))
        except ValueError: return
        s=d.strftime('%d/%m/%Y'); eventos.setdefault((event,s),{'Evento':event,'Data':s,'Página':p,'Trecho':t})
    for p,raw in enumerate(pgs,1):
        t=' '.join(raw.split())
        for m in re.finditer(r'(?i)\b(?:inscriç(?:ões|ão)|período de inscrição)\b[^.;]{0,180}',t):
            frag=m.group(); ds=list(DATA.finditer(frag)); norm=chave(frag)
            prefix=chave(t[max(0,m.start()-100):m.start()])
            if any(x in norm for x in ('isencao','pagamento','taxa','recurso','lei n','decreto')): continue
            if re.search(r'(?:isencao|pagamento|taxa|recurso)[^.;]{0,80}$',prefix): continue
            if not re.search(r'periodo de inscricao|inscricoes (?:estarao|ficarao|poderao)|inscricoes abertas|inscricoes\s*:',norm): continue
            if len(ds)>=2 and re.search(r'\b(?:a|ate|e)\b',chave(frag[ds[0].end():ds[1].start()])):
                add('Início das inscrições',ds[0],p,frag); add('Encerramento das inscrições',ds[1],p,frag)
        for m in DATA.finditer(t):
            before=t[max(0,m.start()-190):m.start()]; after=t[m.end():m.end()+70]; n=chave(before)
            if re.search(r'(?:lei|decreto|portaria|resolucao)\s*(?:n[.º°o]*\s*)?\d[\d.]*\s*,?\s*(?:de\s*)?$',n): continue
            if re.search(r'\b(?:prova objetiva|provas objetivas|prova escrita|prova discursiva)\b',n) and re.search(r'\b(?:aplicad[ao]s?|realizad[ao]s?|previst[ao]s?|ocorrera|dia)\b',n[-145:]) and not re.search(r'gabarito|resultado|recurso|convocacao',n[-100:]):
                add('Data prevista da prova',m,p,before+ m.group()+after)
    order={'Início das inscrições':0,'Encerramento das inscrições':1,'Data prevista da prova':2}
    return sorted(eventos.values(),key=lambda r:order[r['Evento']])

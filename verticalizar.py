import re,csv,io,sys
from pathlib import Path
import fitz

def gerar(pdf, modelo):
    doc=fitz.open(stream=pdf,filetype='pdf')
    pages=[p.get_text(sort=True) for p in doc]
    start=next(i for i,p in enumerate(pages) if 'CONTEÚDO PROGRAMÁTICO' in p and 'CONHECIMENTOS BÁSICOS' in p)
    end=next(i for i in range(start+1,len(pages)) if re.search(r'ANEXO II\s+EXAMES BIOMÉDICOS',pages[i]))
    raw='\n'.join(re.sub(r'^\s*\d+\s*$','',p,flags=re.M) for p in pages[start:end])
    raw=re.sub(r'(?<=\w)-\s*\n\s*(?=mails\b)','-',raw)
    heads=list(re.finditer(r'^\s*(\d+)\.\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇÜ][A-ZÁÉÍÓÚÂÊÔÃÕÇÜ -]+)\s*$',raw,re.M))
    for enc in ['utf-8-sig','cp1252']:
        try: rows=list(csv.reader(io.StringIO(modelo.decode(enc)),delimiter=';'));break
        except UnicodeDecodeError: pass
    header=rows[0]; port=[r for r in rows[1:] if r and r[0].startswith('LÍNGUA PORTUGUESA')]; assert len(header)==19 and port
    out=[header]+port; stats={port[0][0]:len(port)}
    for i,h in enumerate(heads):
        name=h[2].strip()
        if 'PORTUGUESA' in name: continue
        body=raw[h.end():heads[i+1].start() if i+1<len(heads) else len(raw)]
        body=re.sub(r'CONHECIMENTOS ESPECÍFICOS','',body)
        body=' '.join(body.split())
        # Ignore software version number, not a syllabus item.
        markers=[m for m in re.finditer(r'(?<![\w.])('+h[1]+r'(?:\.\d+)+)\.?(?=\s)',body)]
        d=re.sub(r'^NOÇÕES DE ','',name)+' - PCMG'; stats[d]=len(markers)
        for j,m in enumerate(markers):
            topic=body[m.end():markers[j+1].start() if j+1<len(markers) else len(body)].strip().rstrip(';').strip()
            if not topic: raise ValueError(f'Tópico vazio: {m[1]}')
            r=port[0].copy();r[0]=d;r[1]=m[1]+'- '+topic;r[10]=str((j+1)*10);r[9]='';r[15:18]=['','',''];out.append(r)
    if len(stats)!=12: raise ValueError(f'Esperadas 12 disciplinas: {stats}')
    buf=io.StringIO(newline='');csv.writer(buf,delimiter=';',lineterminator='\r\n').writerows(out)
    return buf.getvalue().encode('cp1252'),stats

if __name__=='__main__':
    pdf,modelo,saida=sys.argv[1:4]; data,stats=gerar(Path(pdf).read_bytes(),Path(modelo).read_bytes());Path(saida).write_bytes(data);print(stats)

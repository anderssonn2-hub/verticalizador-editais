import csv, io, re
from copy import copy
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

def ler_csv(data):
    for enc in ('utf-8-sig','cp1252'):
        try: text=data.decode(enc); break
        except UnicodeDecodeError: continue
    dialect=csv.Sniffer().sniff(text[:8192], delimiters=';,\t') if ';' not in text.splitlines()[0] else csv.excel
    return list(csv.reader(io.StringIO(text),delimiter=';' if ';' in text.splitlines()[0] else dialect.delimiter))

def preparar_modelo(data,nome):
    if nome.lower().endswith('.xlsx'):
        wb=load_workbook(io.BytesIO(data)); ws=wb.active
        rows=[[c.value for c in row] for row in ws.iter_rows()]
    else:
        wb=None; rows=ler_csv(data)
    rows=[r for r in rows if any(v not in ('',None) for v in r)]
    if not rows or len(rows[0])!=19 or rows[0][:2]!=['Disciplina','Assunto']:
        raise ValueError('O modelo precisa ter os 19 cabeçalhos originais, começando por Disciplina e Assunto.')
    if any(len(r)!=19 for r in rows): raise ValueError('Há linhas com quantidade de colunas diferente do cabeçalho.')
    buf=io.StringIO(newline=''); csv.writer(buf,delimiter=';').writerows(rows)
    return buf.getvalue().encode('utf-8-sig'),wb

def excel(data,wb=None):
    rows=ler_csv(data)
    if wb is None:
        wb=Workbook(); ws=wb.active; ws.title='Página2'; original={}; prototype=None
    else:
        ws=wb.active
        original={i:[(c.value,c.data_type,copy(c._style),copy(c.hyperlink)) for c in row] for i,row in enumerate(ws.iter_rows(),1)}
        prototype=next((r for r in original.values() if str(r[0][0]).startswith('LÍNGUA PORTUGUESA')),None)
        port=[r for r in original.values() if str(r[0][0]).startswith('LÍNGUA PORTUGUESA')]
        ws.delete_rows(2,ws.max_row)
    numeric={2,3,4,5,10,11,12,13,14,18}; pi=0
    for i,row in enumerate(rows,1):
        saved=None
        if i==1 and original: saved=original[1]
        elif original and row[0].startswith('LÍNGUA PORTUGUESA'):
            saved=port[pi]; pi+=1
        for j,v in enumerate(row):
            c=ws.cell(i,j+1)
            if saved:
                value,kind,style,link=saved[j]; c.value=value;c.data_type=kind;c._style=copy(style)
                if link: c.hyperlink=copy(link)
            else:
                if i>1 and j in numeric and re.fullmatch(r'-?\d+(?:[.,]\d+)?',v):
                    n=float(v.replace(',','.'));c.value=int(n) if n.is_integer() else n
                else:
                    c.value=v or None
                    if isinstance(c.value,str): c.data_type='s'
                if i>1 and prototype: c._style=copy(prototype[j][2])
    if not original:
        from openpyxl.styles import Font,PatternFill,Alignment
        for c in ws[1]: c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='164B54');c.alignment=Alignment(wrap_text=True)
        for j in range(1,20): ws.column_dimensions[get_column_letter(j)].width=42 if j==1 else 75 if j==2 else 20
        ws.freeze_panes='C2';ws.auto_filter.ref=ws.dimensions
    elif ws.auto_filter.ref: ws.auto_filter.ref=ws.dimensions
    for table in ws.tables.values(): table.ref=ws.dimensions
    out=io.BytesIO();wb.save(out);return out.getvalue()

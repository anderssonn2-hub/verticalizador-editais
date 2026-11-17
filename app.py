import streamlit as st
import io, zipfile, re, hashlib
from universal import paginas, localizar, cargos, extrair, montar
from verticalizar import gerar
from exportar import preparar_modelo, excel, ler_csv
st.set_page_config(page_title='Verticalizador de Editais',page_icon='📄',layout='wide')
st.markdown('''<style>.block-container{max-width:1120px;padding-top:2.5rem}.hero{background:linear-gradient(120deg,#102b46,#17635e);color:white;padding:36px;border-radius:18px;margin-bottom:24px}.hero h1{color:white;margin:8px 0}.hero p{color:#e0f2ef}</style><div class="hero"><small>PLANEJAMENTO DE ESTUDOS · V2.0 BETA</small><h1>Verticalizador de Editais</h1><p>Do edital à planilha de estudos.</p></div>''',unsafe_allow_html=True)
a,b=st.columns(2)
with a: pdf=st.file_uploader('Edital do concurso',type=['pdf'])
with b: modelo=st.file_uploader('Planilha paradigma',type=['xlsx','csv'])
st.info('Língua Portuguesa do modelo é preservada automaticamente. Revise a extração antes de exportar.')
if not pdf or not modelo: st.stop()
try:
    base,_=preparar_modelo(modelo.getvalue(),modelo.name)
    pgs=paginas(pdf.getvalue()); n=len(pgs)
    if not any(p.strip() for p in pgs): st.error('PDF sem texto pesquisável. OCR ainda não disponível.');st.stop()
    start,end=localizar(pgs)
    key=hashlib.sha256(pdf.getvalue()+modelo.getvalue()).hexdigest()[:16]
    st.metric('Páginas do edital',n)
    known=bool(any('INVESTIGADOR DE POLÍCIA I' in p and 'CONTEÚDO PROGRAMÁTICO' in p for p in pgs))
    options=cargos(pgs)
    if known and 'Investigador de Polícia I' not in options: options.insert(0,'Investigador de Polícia I')
    custom=st.text_area('Adicionar cargos não identificados (um por linha)')
    options=list(dict.fromkeys(options+[x.strip() for x in custom.splitlines() if x.strip()]))
    chosen=st.multiselect('Cargos desejados',options,default=options if len(options)==1 else [],key='cargo'+key)
    if not chosen: st.warning('Selecione ou informe o cargo.');st.stop()
    files={}
    for i,cargo in enumerate(chosen):
        st.subheader(cargo)
        scope=st.slider('Páginas do conteúdo programático (inclua conhecimentos comuns)',1,n,(start,end),key=f'p{key}{cargo}') if n>1 else (1,1)
        with st.expander('Conferir texto original das páginas escolhidas'):
            st.text('\n'.join(pgs[scope[0]-1:scope[1]]))
        legacy=known and cargo=='Investigador de Polícia I' and scope==(start,end)
        if legacy:
            data,_=gerar(pdf.getvalue(),base); rows=ler_csv(data); original=ler_csv(base); preserved={tuple(r[:2]) for r in original[1:] if r[0].startswith('LÍNGUA PORTUGUESA')}; items=[dict(zip(rows[0][:2],r[:2])) for r in rows[1:] if tuple(r[:2]) not in preserved]
        else: items=extrair(pgs,*scope)
        if not items: items=[{'Disciplina':'','Assunto':''}];st.warning('Nenhum padrão identificado. Informe os assuntos manualmente ou ajuste as páginas.')
        edited=st.data_editor(items,num_rows='dynamic',hide_index=True,key=f'e{key}{cargo}{scope}')
        confirmed=st.checkbox('Conferi os assuntos e a correspondência com este cargo',key=f'c{key}{cargo}{scope}')
        if confirmed:
            result=montar(base,edited); _,wb=preparar_modelo(modelo.getvalue(),modelo.name); output=excel(result,wb)
            name=f'{i+1}_'+re.sub(r'[^\w-]+','_',cargo)+'.xlsx';files[name]=output
            st.download_button('Baixar Excel (.xlsx)',output,name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f'd{key}{cargo}')
    if len(files)>1:
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items(): z.writestr(name,data)
        st.download_button('Baixar todos os cargos (ZIP)',buf.getvalue(),'editais.zip','application/zip')
except Exception as e: st.error(f'Não foi possível processar: {e}')
st.caption('V2.0 beta · Extração genérica por padrões, com revisão obrigatória.')

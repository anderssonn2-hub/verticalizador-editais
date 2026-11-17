import streamlit as st
import io, zipfile, re, hashlib
from universal import paginas, localizar, cargos, extrair, montar
from verticalizar import gerar
from exportar import preparar_modelo, excel, ler_csv
st.set_page_config(page_title='Verticalizador de Editais',page_icon='📄',layout='wide')
st.markdown('''<style>
.block-container{max-width:1120px;padding-top:2.5rem;padding-bottom:3rem}
.hero{background:linear-gradient(115deg,#102b46,#17635e);color:white;padding:36px;border-radius:18px;margin-bottom:24px}
.hero h1{color:white;margin:8px 0;font-size:clamp(1.8rem,4vw,2.7rem)}.hero p{color:#e0f2ef;margin-bottom:0}
.steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 24px}
.step{border:1px solid #81939e55;border-radius:12px;padding:14px;font-size:.88rem;font-weight:600}
.step span{color:#168575;margin-right:7px;font-weight:800}
[data-testid="stMetric"]{border:1px solid #81939e55;border-radius:14px;padding:16px;min-height:110px;box-shadow:0 3px 12px #173b4910}
[data-testid="stMetricLabel"]{font-size:.85rem}[data-testid="stMetricValue"]{font-size:1.85rem}
[data-testid="stFileUploaderDropzone"]{border:1px dashed #81939e;border-radius:12px}
[data-testid="stDownloadButton"] button{border-radius:10px;background:#217346;color:white;border:1px solid #217346;font-weight:600}
[data-testid="stDownloadButton"] button:hover{background:#175a36;color:white;border-color:#175a36}
@media(max-width:600px){.hero{padding:23px}.steps{gap:5px}.step{padding:8px;font-size:.72rem}}
</style><div class="hero"><small>PLANEJAMENTO DE ESTUDOS · V2.0.2 BETA</small><h1>Verticalizador de Editais</h1><p>Do edital à planilha de estudos. Organize, confira e exporte em Excel.</p></div>
<div class="steps"><div class="step"><span>01</span>Enviar arquivos</div><div class="step"><span>02</span>Conferir conteúdo</div><div class="step"><span>03</span>Exportar Excel</div></div>''',unsafe_allow_html=True)
st.subheader('01 · Arquivos de entrada')
st.caption('Selecione o edital em PDF e o modelo de planilha utilizado no seu planejamento.')
a,b=st.columns(2)
with a: pdf=st.file_uploader('Edital do concurso',type=['pdf'])
with b: modelo=st.file_uploader('Planilha paradigma',type=['xlsx','csv'])
if not pdf or not modelo:
    st.caption('Aguardando os dois arquivos para iniciar a análise.')
    st.stop()
st.success('Arquivos recebidos. Confira a análise abaixo.')
st.divider()
st.subheader('02 · Análise do edital')
try:
    base,_=preparar_modelo(modelo.getvalue(),modelo.name)
    pgs=paginas(pdf.getvalue()); n=len(pgs)
    if not any(p.strip() for p in pgs): st.error('PDF sem texto pesquisável. OCR ainda não disponível.');st.stop()
    start,end=localizar(pgs)
    key=hashlib.sha256(pdf.getvalue()+modelo.getvalue()).hexdigest()[:16]
    known=bool(any('INVESTIGADOR DE POLÍCIA I' in p and 'CONTEÚDO PROGRAMÁTICO' in p for p in pgs))
    options=cargos(pgs)
    if known and 'Investigador de Polícia I' not in options: options.insert(0,'Investigador de Polícia I')
    m1,m2,m3=st.columns(3)
    m1.metric('Páginas do edital',n)
    m2.metric('Cargos detectados',len(options))
    m3.metric('Páginas sugeridas',f'{start}–{end}')
    st.caption('Intervalo sugerido automaticamente; confira as páginas para cada cargo.')
    with st.expander('Adicionar cargos manualmente'):
        custom=st.text_area('Adicionar cargos não identificados (um por linha)')
    st.subheader('03 · Selecione os cargos')
    options=list(dict.fromkeys(options+[x.strip() for x in custom.splitlines() if x.strip()]))
    chosen=st.multiselect('Cargos desejados',options,default=options if len(options)==1 else [],key='cargo'+key)
    if not chosen: st.warning('Selecione ou informe o cargo.');st.stop()
    files={}
    for i,cargo in enumerate(chosen):
        st.divider()
        st.subheader(f'{i+1:02d} · {cargo}')
        st.caption('Ajuste o intervalo, confira o texto e revise os assuntos antes de exportar.')
        scope=st.slider('Páginas do conteúdo programático (inclua conhecimentos comuns)',1,n,(start,end),key=f'p{key}{cargo}') if n>1 else (1,1)
        with st.expander('Conferir texto original das páginas escolhidas'):
            st.text('\n'.join(pgs[scope[0]-1:scope[1]]))
        legacy=known and cargo=='Investigador de Polícia I' and scope==(start,end)
        if legacy:
            data,_=gerar(pdf.getvalue(),base); rows=ler_csv(data); original=ler_csv(base); preserved={tuple(r[:2]) for r in original[1:] if r[0].startswith('LÍNGUA PORTUGUESA')}; items=[dict(zip(rows[0][:2],r[:2])) for r in rows[1:] if tuple(r[:2]) not in preserved]
        else: items=extrair(pgs,*scope)
        if not items: items=[{'Disciplina':'','Assunto':''}];st.warning('Nenhum padrão identificado. Informe os assuntos manualmente ou ajuste as páginas.')
        edited=st.data_editor(items,num_rows='dynamic',hide_index=True,key=f'e{key}{cargo}{scope}')
        valid=[r for r in edited if str(r.get('Disciplina') or '').strip() and str(r.get('Assunto') or '').strip()]
        c1,c2,c3=st.columns(3)
        c1.metric('Disciplinas na revisão',len({str(r['Disciplina']).strip() for r in valid}))
        c2.metric('Assuntos na revisão',len(valid))
        c3.metric('Páginas selecionadas',scope[1]-scope[0]+1)
        st.caption('Os números acima refletem a tabela de revisão, não necessariamente o total final do Excel.')
        if valid:
            result=montar(base,valid); _,wb=preparar_modelo(modelo.getvalue(),modelo.name); output=excel(result,wb)
            name=f'{i+1}_'+re.sub(r'[^\w-]+','_',cargo)+'.xlsx';files[name]=output
            st.markdown('#### Sua planilha está pronta')
            st.caption('O arquivo incorpora os assuntos da tabela de revisão. Confira o conteúdo antes de utilizar.')
            st.download_button('⬇ Baixar planilha Excel (.xlsx)',output,name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f'd{key}{cargo}',use_container_width=True)
        else:
            st.warning('Inclua pelo menos um assunto válido para disponibilizar o Excel.')
    if len(files)>1:
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items(): z.writestr(name,data)
        st.download_button('Baixar todos os cargos (ZIP)',buf.getvalue(),'editais.zip','application/zip')
except Exception as e: st.error(f'Não foi possível processar: {e}')
st.caption('V2.0.2 beta · Extração genérica por padrões, confira o conteúdo antes de utilizar.')

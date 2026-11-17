import streamlit as st
import csv,io
from verticalizar import gerar
st.set_page_config(page_title='Verticalizador de Editais',layout='wide')
st.title('Verticalizador de Editais — V1.0')
st.caption('Protótipo para o edital PCMG. Preserva Português e as 19 colunas do modelo.')
pdf=st.file_uploader('Edital do concurso',type=['pdf'])
modelo=st.file_uploader('Planilha paradigma',type=['csv'])
if pdf and modelo:
    try:
        data,stats=gerar(pdf.getvalue(),modelo.getvalue())
        st.metric('Assuntos',sum(stats.values()))
        st.dataframe([{'Disciplina':k,'Assuntos':v} for k,v in stats.items()])
        rows=list(csv.DictReader(io.StringIO(data.decode('cp1252')),delimiter=';'))
        st.dataframe(rows,use_container_width=True)
        st.download_button('Baixar CSV',data,'PCMG_verticalizado.csv','text/csv')
    except Exception as e:
        st.error(f'Não foi possível processar: {e}')

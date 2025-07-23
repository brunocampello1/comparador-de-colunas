import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import dateutil.parser

def detect_date_format(date_series):
    """Detecta automaticamente o formato de data em uma série"""
    sample = date_series.dropna().head(100)  # Analisa uma amostra
    formats = []
    
    for date_str in sample:
        try:
            parsed = dateutil.parser.parse(str(date_str))
            formats.append(parsed)
        except:
            continue
    
    if not formats:
        return None
    
    # Verifica o formato predominante
    first_date = formats[0]
    if first_date.strftime('%Y-%m-%d') in sample.values:
        return 'iso'
    elif first_date.strftime('%d/%m/%Y') in sample.values:
        return 'brasil'
    elif first_date.strftime('%m/%d/%Y') in sample.values:
        return 'eua'
    else:
        return 'auto'

def convert_dates(df, date_col):
    """Converte a coluna de data para datetime conforme formato detectado"""
    if date_col not in df.columns:
        return df
    
    date_format = detect_date_format(df[date_col])
    
    if date_format == 'brasil':
        df[date_col] = pd.to_datetime(df[date_col], format='%d/%m/%Y', errors='coerce')
    elif date_format == 'iso':
        df[date_col] = pd.to_datetime(df[date_col], format='%Y-%m-%d', errors='coerce')
    elif date_format == 'eua':
        df[date_col] = pd.to_datetime(df[date_col], format='%m/%d/%Y', errors='coerce')
    else:
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    
    return df

st.title("Planejado x Realizado")

# Upload dos arquivos
file1 = st.file_uploader("Envie o plano de mídia", type="csv")
file2 = st.file_uploader("Envie o realizado", type="csv")

if file1 and file2:
    # Guardar os dataframes originais antes de qualquer filtro
    df1_original = pd.read_csv(file1, delimiter=';')
    df2_original = pd.read_csv(file2, delimiter=';')
    
    # Criar cópias para trabalhar
    df1 = df1_original.copy()
    df2 = df2_original.copy()

    st.subheader('COLUNAS DE COMPARAÇÃO')
    col1 = st.selectbox("Coluna do PLANO para comparação", df1.columns)
    col2 = st.selectbox("Coluna do REALIZADO para comparação", df2.columns)

    st.subheader('FILTROS OPCIONAIS')
    
    # Filtro por valor
    filtro_col = st.selectbox("Coluna para filtrar (opcional)", ["(Sem filtro)"] + list(df1.columns))
    filtro_val = None
    if filtro_col != "(Sem filtro)":
        valores = sorted(df1[filtro_col].dropna().astype(str).unique())
        filtro_val = st.selectbox(f"Valor para filtrar '{filtro_col}'", valores)

    # Filtro por data com detecção automática
    st.subheader('FILTRO DE DATA')
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        date_col_plano = st.selectbox("Coluna de data no PLANO", ["(Sem filtro)"] + list(df1.columns))
    with col_date2:
        date_col_realizado = st.selectbox("Coluna de data no REALIZADO", ["(Sem filtro)"] + list(df2.columns))
    
    date_range = st.date_input("Intervalo de datas", [])

    if st.button("Comparar valores"):
        # Resetar os dataframes para os originais antes de aplicar novos filtros
        df1 = df1_original.copy()
        df2 = df2_original.copy()
        
        # Aplicar filtro por valor
        if filtro_col != "(Sem filtro)":
            df1 = df1[df1[filtro_col].astype(str) == str(filtro_val)]
            df2 = df2[df2[filtro_col].astype(str) == str(filtro_val)]

        # Aplicar filtro por data com detecção automática
        if len(date_range) == 2:
            try:
                data_ini, data_fim = date_range
                
                # Converter datas para datetime
                data_ini_dt = pd.to_datetime(data_ini)
                data_fim_dt = pd.to_datetime(data_fim)
                
                # Processar PLANO
                if date_col_plano != "(Sem filtro)":
                    df1 = convert_dates(df1, date_col_plano)
                    df1 = df1[
                        (df1[date_col_plano] >= data_ini_dt) & 
                        (df1[date_col_plano] <= data_fim_dt)
                    ]
                
                # Processar REALIZADO
                if date_col_realizado != "(Sem filtro)":
                    df2 = convert_dates(df2, date_col_realizado)
                    df2 = df2[
                        (df2[date_col_realizado] >= data_ini_dt) & 
                        (df2[date_col_realizado] <= data_fim_dt)
                    ]
                    
                # Mostrar formato detectado
                if date_col_plano != "(Sem filtro)":
                    formato_plano = detect_date_format(df1_original[date_col_plano])
                  #  st.info(f"Formato detectado no PLANO: {formato_plano}")
                if date_col_realizado != "(Sem filtro)":
                    formato_realizado = detect_date_format(df2_original[date_col_realizado])
                 #   st.info(f"Formato detectado no REALIZADO: {formato_realizado}")
                    
            except Exception as e:
                st.error(f"Erro ao filtrar datas: {e}")
                st.stop()

        # DEBUG: Mostrar contagem de linhas após filtros
        #st.info(f"Linhas no PLANO após filtros: {len(df1)}")
        #st.info(f"Linhas no REALIZADO após filtros: {len(df2)}")

        # Comparação
        plano_vals = df1[col1].dropna().astype(str).unique()
        realizado_vals = df2[col2].dropna().astype(str).unique()

        apenas_no_realizado = sorted(set(realizado_vals) - set(plano_vals))

        # Resultado
        st.subheader("Itens no REALIZADO que não estão no PLANO:")
        if apenas_no_realizado:
            st.error(f"Total: {len(apenas_no_realizado)} itens")
            st.write(apenas_no_realizado)
            
            # Download
            output = BytesIO()
            pd.DataFrame({"Itens faltantes": apenas_no_realizado}).to_excel(output, index=False)
            output.seek(0)
            st.download_button(
                label="📥 Baixar resultado",
                data=output,
                file_name="itens_faltantes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("Todos os itens do realizado estão presentes no plano!")

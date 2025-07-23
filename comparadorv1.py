import streamlit as st
import pandas as pd
from io import BytesIO

st.title("Planejado x Realizado")

# Upload dos arquivos
file1 = st.file_uploader("Envie o plano de mídia", type="csv")
file2 = st.file_uploader("Envie o realizado", type="csv")

if file1 and file2:
    df1 = pd.read_csv(file1, delimiter=';')
    df2 = pd.read_csv(file2, delimiter=';')

    # Guardar cópias originais para comparação completa
    df1_original = df1.copy()
    df2_original = df2.copy()

    st.markdown('')
    st.subheader('COLUNAS DE COMPARAÇÃO')
    col_a, col_b = st.columns(2)
    with col_a:
        col1 = st.selectbox("Coluna do PLANO para comparação", df1.columns)

    with col_b:
        col2 = st.selectbox("Coluna do REALIZADO para comparação", df2.columns)

    st.markdown('')

    # FILTRAR COLUNA POR VALOR
    st.subheader('FILTRAR COLUNA POR VALOR')
    col_c, col_d = st.columns(2)
    with col_c:
        filtro_col1 = st.selectbox("Coluna do PLANO para filtrar (opcional)", ["(Sem filtro)"] + list(df1.columns))
        filtro_val1 = None
        if filtro_col1 != "(Sem filtro)":
            valores1 = sorted(df1[filtro_col1].dropna().astype(str).unique())
            filtro_val1 = st.selectbox(f"Valor da coluna '{filtro_col1}' na Base 1", valores1)

    with col_d:
        filtro_col2 = st.selectbox("Coluna do REALIZADO para filtrar (opcional)", ["(Sem filtro)"] + list(df2.columns))
        filtro_val2 = None
        if filtro_col2 != "(Sem filtro)":
            valores2 = sorted(df2[filtro_col2].dropna().astype(str).unique())
            filtro_val2 = st.selectbox(f"Valor da coluna '{filtro_col2}' na Base 2", valores2)

    st.markdown('')

    # FILTRAR DATAFRAME POR DATA (APLICADO PARA AMBOS)
    st.subheader('FILTRAR DATAFRAME POR DATA (OPCIONAL)')
    date_range = st.date_input("Intervalo de datas (aplicado tanto para o PLANO quanto para o REALIZADO)", [])

    # Escolha do tipo de comparação
    modo_comparacao = st.radio("Modo de comparação:", ["Comparar usando dados filtrados", "Comparar todos os dados (sem filtro)"])

    if st.button("Comparar valores"):

        # Aplicar filtro por valor
        if filtro_col1 != "(Sem filtro)":
            df1 = df1[df1[filtro_col1].astype(str) == filtro_val1]
        if filtro_col2 != "(Sem filtro)":
            df2 = df2[df2[filtro_col2].astype(str) == filtro_val2]

        # Aplicar filtro por data (nos dois DataFrames)
        if 'plan_data' in df1.columns and len(date_range) == 2:
            data_ini, data_fim = date_range
            df1['plan_data'] = pd.to_datetime(df1['plan_data'], errors='coerce', dayfirst=True)
            df1 = df1[df1['plan_data'].dt.date >= data_ini]
            df1 = df1[df1['plan_data'].dt.date <= data_fim]

        if 'real_data' in df2.columns and len(date_range) == 2:
            df2['real_data'] = pd.to_datetime(df2['real_data'], errors='coerce', dayfirst=True)
            df2 = df2[df2['real_data'].dt.date >= data_ini]
            df2 = df2[df2['real_data'].dt.date <= data_fim]

        # Escolher fonte dos dados para comparação
        if modo_comparacao == "Comparar todos os dados (sem filtro)":
            base1_vals = df1_original[col1].dropna().astype(str).unique()
            base2_vals = df2_original[col2].dropna().astype(str).unique()
            st.info("Comparando usando todos os dados, sem aplicar filtros.")
        else:
            base1_vals = df1[col1].dropna().astype(str).unique()
            base2_vals = df2[col2].dropna().astype(str).unique()
            st.info("Comparando apenas os dados filtrados.")

        apenas_no_plano = sorted(set(base1_vals) - set(base2_vals))
        apenas_no_realizado = sorted(set(base2_vals) - set(base1_vals))

        # Exibir resultado principal
        st.subheader("Comparação do REALIZADO com o PLANO:")
        if apenas_no_realizado:
            st.error(f"Foram encontrados {len(apenas_no_realizado)} itens no realizado que não constam no plano:")
            st.write(apenas_no_realizado)
        else:
            st.success("Todos os itens do realizado estão presentes no plano!")

        # Exibir resultado secundário
        #st.subheader("ℹ️ Itens no PLANO que não aparecem no REALIZADO (não realizados):")
        #st.write(apenas_no_plano if apenas_no_plano else "Nenhum")

        # Gerar planilha para download
        output = BytesIO()
        todos_valores = sorted(set(base1_vals).union(set(base2_vals)))
        lado_realizado = [val if val in base2_vals else "" for val in todos_valores]
        lado_plano = [val if val in base1_vals else "" for val in todos_valores]

        df_resultado = pd.DataFrame({
            f"Itens no REALIZADO ({col2})": lado_realizado,
            f"Itens no PLANO ({col1})": lado_plano
        })

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_resultado.to_excel(writer, sheet_name="Comparacao", index=False)
            pd.DataFrame({"Somente no REALIZADO": apenas_no_realizado}).to_excel(writer, sheet_name="Extras", index=False, startcol=0)
            pd.DataFrame({"Somente no PLANO": apenas_no_plano}).to_excel(writer, sheet_name="Extras", index=False, startcol=2)

        output.seek(0)
        st.download_button(
            label="📥 Baixar resultado da comparação",
            data=output,
            file_name="comparacao_realizado_vs_plano.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

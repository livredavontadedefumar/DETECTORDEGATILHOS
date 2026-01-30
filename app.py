import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.title("🧪 Teste de Diagnóstico de Erro")

try:
    # Teste 1: Conexão com Google Sheets
    st.write("Tentando conectar ao Google Sheets...")
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(credentials)
    
    # ID da planilha (verifique se é este mesmo!)
    sh = client.open_by_key("16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8")
    worksheet = sh.get_worksheet(0)
    st.success("✅ Conexão com Planilha OK!")
    
    # Teste 2: Leitura de dados
    dados = worksheet.get_all_values()
    st.write(f"Linhas encontradas: {len(dados)}")
    st.success("✅ Leitura de Dados OK!")

except Exception as e:
    st.error(f"❌ O ERRO ESTÁ AQUI: {e}")

st.info("Se o erro acima for 400, o problema é o ID da planilha ou permissão no Cloud.")

import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

st.title("🧪 Teste de Conexão Direta")

try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(credentials)
    
    # Abrindo pelo ID da planilha (Foto 2e34)
    spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
    sh = client.open_by_key(spreadsheet_id)
    
    # EM VEZ DE get_worksheet(0), VAMOS PELO NOME EXATO QUE ESTÁ NA FOTO 2e34
    # Se o nome no rodapé da planilha for diferente de 'MAPEAMENTO (respostas)', 
    # mude o texto abaixo para o nome que aparece na aba lá no Google Sheets.
    worksheet = sh.worksheet("MAPEAMENTO (respostas)")
    
    dados = worksheet.get_all_values()
    st.success(f"✅ CONECTADO! Encontramos {len(dados)} linhas de dados.")
    st.dataframe(pd.DataFrame(dados[1:], columns=dados[0]))

except Exception as e:
    st.error(f"❌ Erro detectado: {e}")
    st.info("Dica: Verifique se o nome da aba no rodapé da planilha é exatamente 'MAPEAMENTO (respostas)'.")

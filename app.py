import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configuração básica
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")
os.environ["GOOGLE_API_VERSION"] = "v1"

# --- FUNÇÃO DE CONEXÃO REVISADA ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da sua planilha
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Tenta pegar a primeira aba (evita erro de nome de aba)
        worksheet = sh.get_worksheet(0)
        
        # Puxa os valores brutos
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
            
        # Cria o DataFrame
        df = pd.DataFrame(data[1:], columns=data[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Mostra o erro real para sabermos o que é
        st.error(f"Erro de Conexão: {e}")
        return pd.DataFrame()

# IA
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("E-mail cadastrado:").strip().lower()
    if st.button("Entrar"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Filtra os dados do usuário
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        
        if not user_data.empty:
            st.success(f"Olá! Encontrámos {len(user_data)} registros.")
            st.dataframe(user_data.tail(5))
            
            if st.button("🚀 GERAR ORIENTAÇÃO"):
                model = genai.GenerativeModel('gemini-1.5-flash')
                with st.spinner('Analisando...'):
                    ctx = user_data.tail(10).to_string()
                    prompt = f"És um mentor. Analise estes dados e dê um conselho curto: {ctx}"
                    res = model.generate_content(prompt)
                    st.info(res.text)
        else:
            st.warning("E-mail não encontrado na planilha.")
            if st.button("Voltar"):
                st.session_state.logged_in = False
                st.rerun()

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

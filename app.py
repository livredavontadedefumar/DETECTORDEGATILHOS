import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Força a limpeza de cache do ambiente
os.environ["GOOGLE_API_VERSION"] = "v1"
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha - Verifique se é exatamente este sem espaços
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        
        # Tentativa de abertura direta para matar o Erro 400
        sh = client.open_by_key(spreadsheet_id.strip())
        
        # Pegamos a aba por índice (0 é a primeira, 1 é a segunda)
        # Na sua foto e2a8, a aba MAPEAMENTO parece ser a segunda
        try:
            worksheet = sh.get_worksheet(1) 
        except:
            worksheet = sh.get_worksheet(0)
            
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Se falhar aqui, o erro 400 é de PERMISSÃO ou ID INCORRETO
        st.error(f"Falha na comunicação com o Google: {e}")
        return pd.DataFrame()

# Interface
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("E-mail para acesso:").strip().lower()
    if st.button("Entrar"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca flexível por e-mail em qualquer coluna
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success("Dados carregados com sucesso!")
            st.dataframe(user_data.tail(5))
            
            if st.button("🚀 GERAR ORIENTAÇÃO"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    ctx = user_data.tail(10).to_string()
                    response = model.generate_content(f"Analise e dê um conselho curto: {ctx}")
                    st.info(response.text)
                except Exception as e:
                    st.error(f"Erro no Gemini: {e}")
        else:
            st.warning("E-mail não localizado. Verifique os dados da planilha.")

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

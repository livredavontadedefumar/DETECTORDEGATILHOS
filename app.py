import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configurações de Interface
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da sua planilha (Extraído da imagem e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # BUSCA ROBUSTA: Tentamos pelo nome exato que está na aba
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            # Se não achar pelo nome, pegamos a aba que tiver 'MAPEAMENTO' no título
            list_sheets = sh.worksheets()
            worksheet = next((s for s in list_sheets if "MAPEAMENTO" in s.title.upper()), list_sheets[0])
            
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Organiza os dados
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao ler Planilha: {e}")
        return pd.DataFrame()

# Configuração Gemini
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Digite o e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = conectar_planilha()
    
    if not df.empty:
        # Busca flexível por e-mail
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Conectado com sucesso!")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando...'):
                        contexto = user_data.tail(10).to_string()
                        prompt = f"Analise estes dados e dê um diagnóstico curto de Mentor: {contexto}"
                        response = model.generate_content(prompt)
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
        else:
            st.error(f"E-mail '{st.session_state.user_email}' não encontrado.")
            if st.button("Sair"):
                st.session_state.logged_in = False
                st.rerun()

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

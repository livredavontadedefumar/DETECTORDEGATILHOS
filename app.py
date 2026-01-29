import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Forçamos o reset de qualquer configuração de versão anterior
if "GOOGLE_API_VERSION" in os.environ:
    del os.environ["GOOGLE_API_VERSION"]

st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da sua planilha (visto na imagem e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Tentamos abrir a aba MAPEAMENTO de forma bruta
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            # Se falhar, pegamos a aba 1 (Segunda aba, conforme foto e2a8)
            worksheet = sh.get_worksheet(1)
            
        # Puxamos apenas os valores, sem metadados (evita o erro 400 de argumento)
        valores = worksheet.get_values() 
        
        if not valores:
            return pd.DataFrame()
            
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Se der erro aqui, saberemos se é permissão ou cota
        st.error(f"Atenção: Erro na leitura dos dados. Detalhe: {e}")
        return pd.DataFrame()

# Título e IA
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Digite seu e-mail:").strip().lower()
    if st.button("Acessar"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca o e-mail em qualquer coluna
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        
        if not user_data.empty:
            st.success("Dados carregados!")
            st.dataframe(user_data.tail(5))
            
            if st.button("🚀 GERAR DIAGNÓSTICO"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    ctx = user_data.tail(10).to_string()
                    res = model.generate_content(f"Dê um conselho curto para este aluno: {ctx}")
                    st.info(res.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
        else:
            st.warning("E-mail não encontrado.")
            if st.button("Voltar"):
                st.session_state.logged_in = False
                st.rerun()

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

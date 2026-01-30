import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- 1. CONEXÃO COM A PLANILHA (USA O JSON) ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        sh = client.open("BANCO-MENTOR-IA")
        return pd.DataFrame(sh.worksheet("DADOS").get_all_records())
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return pd.DataFrame()

# --- 2. LOGIN ---
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🌿 Mentor IA - Acesso")
    email = st.text_input("E-mail:").strip().lower()
    if st.button("Entrar"):
        st.session_state.user_email = email
        st.session_state.logado = True
        st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca a coluna de email automaticamente
        col_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()][0]
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        
        st.success(f"Registros de {st.session_state.user_email}")
        st.dataframe(user_data.tail(10))

        # --- 3. GERAR DIAGNÓSTICO (USA APENAS API KEY) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                # Configura a IA usando APENAS a API KEY (como sugere sua pesquisa)
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                
                # Forçamos a versão estável do modelo para evitar o erro 404
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = f"Analise estes gatilhos e dê um conselho: {user_data.tail(5).to_string()}"
                
                # Chamada direta
                response = model.generate_content(prompt)
                st.info(response.text)
                
            except Exception as e:
                st.error(f"Erro na IA: {e}")
                st.warning("Verifique se sua API Key está correta nos Secrets.")

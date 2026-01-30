import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- CONEXÃO COM A PLANILHA (Usa o JSON) ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        # Abre a planilha BANCO-MENTOR-IA (Foto 7c9c)
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        dados = worksheet.get_all_values()
        headers = [str(h).strip() for h in dados[0]]
        return pd.DataFrame(dados[1:], columns=headers)
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("E-mail:").strip().lower()
    if st.button("Acessar"):
        st.session_state.user_email = email_input
        st.session_state.logado = True
        st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca a coluna de e-mail (conforme sua foto 3b31)
        col_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()][0]
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        
        st.success(f"Conectado como {st.session_state.user_email}")
        st.dataframe(user_data.tail(10))

        # --- GERAR DIAGNÓSTICO (Corrige o Erro 404) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                # Configura a IA usando estritamente a API Key do bloco [gemini]
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                
                # Chamada do modelo de forma estável (SEM v1beta)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner('Analisando seu histórico...'):
                    # Puxa os dados que já aparecem na sua foto 3b31
                    contexto = user_data.tail(5).to_string()
                    prompt = f"Você é o Mentor IA. Analise estes gatilhos e dê um conselho firme: {contexto}"
                    
                    response = model.generate_content(prompt)
                    st.markdown("---")
                    st.info(response.text)
            except Exception as e:
                st.error(f"Erro na IA: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

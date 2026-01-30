import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- CONEXÃO COM A PLANILHA (Sempre funcionando conforme foto 3b31) ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        dados = worksheet.get_all_values()
        headers = [str(h).strip() for h in dados[0]]
        return pd.DataFrame(dados[1:], columns=headers)
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("Seu e-mail:").strip().lower()
    if st.button("Acessar"):
        st.session_state.user_email = email_input
        st.session_state.logado = True
        st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        col_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()][0]
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        st.success(f"Registros de {st.session_state.user_email}")
        st.dataframe(user_data.tail(10))

        # --- BOTÃO DE DIAGNÓSTICO (Ajustado conforme diagnóstico da foto 97d1) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                api_key = st.secrets["gemini"]["api_key"]
                # URL ESTÁVEL v1
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                # Headers obrigatórios para evitar erro 400/404
                headers = {'Content-Type': 'application/json'}
                
                contexto = user_data.tail(5).to_string()
                # Payload 100% limpo conforme padrão Google AI
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"Analise como mentor: {contexto}"
                        }]
                    }]
                }
                
                with st.spinner('Analisando...'):
                    response = requests.post(url, headers=headers, json=payload)
                    
                    if response.status_code == 200:
                        resultado = response.json()
                        texto = resultado['candidates'][0]['content']['parts'][0]['text']
                        st.info(texto)
                    else:
                        # Mostra o erro real que o Google está enviando (ajuda a matar o 100% de erro)
                        st.error(f"Erro {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Falha técnica: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

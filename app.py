import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- CONEXÃO COM A PLANILHA (Google Sheets) ---
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

# --- INTERFACE PRINCIPAL ---
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("Seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca a coluna de e-mail automaticamente (visto na foto 7c9c)
        col_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()][0]
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        
        st.success(f"Registros encontrados para {st.session_state.user_email}")
        st.dataframe(user_data.tail(10))

        # --- BOTÃO DE DIAGNÓSTICO (CHAMADA DIRETA VIA WEB) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                api_key = st.secrets["gemini"]["api_key"]
                # URL da versão estável v1 (Mata o erro 404 da v1beta)
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                contexto = user_data.tail(10).to_string()
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"Você é o Mentor IA do Método Livre da Vontade. Analise estes gatilhos e dê um diagnóstico firme: {contexto}"
                        }]
                    }]
                }
                
                with st.spinner('O Mentor está analisando seu histórico...'):
                    response = requests.post(url, json=payload)
                    resultado = response.json()
                    
                    if response.status_code == 200:
                        texto_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                        st.markdown("---")
                        st.markdown("### 🌿 Diagnóstico do Mentor")
                        st.info(texto_ia)
                    else:
                        st.error(f"Erro na API ({response.status_code}): {resultado.get('error', {}).get('message', 'Erro técnico')}")
                        
            except Exception as e:
                st.error(f"Erro técnico: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

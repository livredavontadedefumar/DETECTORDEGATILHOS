import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- CONEXÃO COM A PLANILHA (Funcionando 100% - Foto 3b31) ---
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
    if st.button("Acessar Mapeamento"):
        st.session_state.user_email = email_input
        st.session_state.logado = True
        st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        col_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()][0]
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        
        st.success(f"Conectado: {st.session_state.user_email}")
        st.dataframe(user_data.tail(10))

        # --- BOTÃO DE DIAGNÓSTICO (Ajustado para Gemini-1.0-Pro) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                api_key = st.secrets["gemini"]["api_key"]
                
                # URL CORRETA SUGERIDA (v1 + gemini-1.0-pro)
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.0-pro:generateContent?key={api_key}"
                
                contexto = user_data.tail(10).to_string()
                payload = {
                    "contents": [{
                        "parts": [{"text": f"Você é o Mentor IA. Analise estes registros e dê um conselho curto e firme: {contexto}"}]
                    }]
                }
                
                headers = {'Content-Type': 'application/json'}
                
                with st.spinner('O Mentor está analisando seu Raio-X...'):
                    response = requests.post(url, headers=headers, json=payload)
                    resultado = response.json()
                    
                    if response.status_code == 200:
                        # Extrai o texto da resposta conforme o formato do Google AI
                        texto_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                        st.markdown("---")
                        st.markdown("### 🌿 Diagnóstico do Mentor")
                        st.info(texto_ia)
                    else:
                        st.error(f"Erro {response.status_code}: {resultado.get('error', {}).get('message', 'Erro técnico')}")
                        
            except Exception as e:
                st.error(f"Erro técnico: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

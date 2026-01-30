import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- CONEXÃO COM A PLANILHA (Confirmada na foto 3b31) ---
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
        
        st.success(f"Registros de {st.session_state.user_email} carregados.")
        st.dataframe(user_data.tail(10))

        # --- BOTÃO DE DIAGNÓSTICO (CHAMADA DIRETA v1) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                # Usa a sua API Key do bloco [gemini]
                api_key = st.secrets["gemini"]["api_key"]
                
                # FORÇANDO A URL ESTÁVEL v1 (Isso evita o erro 404 da v1beta)
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                contexto = user_data.tail(10).to_string()
                payload = {
                    "contents": [{
                        "parts": [{"text": f"Como Mentor, analise estes registros e dê um diagnóstico curto: {contexto}"}]
                    }]
                }
                
                with st.spinner('O Mentor está analisando seu histórico...'):
                    response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
                    
                    if response.status_code == 200:
                        resultado = response.json()
                        texto_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                        st.markdown("---")
                        st.info(texto_ia)
                    else:
                        st.error(f"Erro {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Erro técnico: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

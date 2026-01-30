import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- CONEXÃO COM A PLANILHA ---
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
        if email_input:
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

        # --- BOTÃO DE DIAGNÓSTICO (FORÇANDO ROTA ESTÁVEL) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                # Configura a chave
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                
                # FORÇANDO A VERSÃO 'v1' PARA MATAR O ERRO 404 DA 'v1beta'
                from google.generativeai.types import RequestOptions
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner('O Mentor IA está analisando...'):
                    contexto = user_data.tail(10).to_string()
                    prompt = f"Como Mentor do Método Livre da Vontade, analise estes gatilhos e dê um conselho curto: {contexto}"
                    
                    # A mágica está aqui: forçamos a API a não usar a rota beta
                    response = model.generate_content(
                        prompt,
                        request_options=RequestOptions(api_version='v1')
                    )
                    
                    st.markdown("---")
                    st.markdown("### 🌿 Diagnóstico do Mentor")
                    st.info(response.text)
            except Exception as e:
                st.error(f"Erro na IA: {e}")
                st.info("Dica: Verifique se sua API Key no AI Studio está ativa.")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

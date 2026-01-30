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

        # --- BOTÃO DE DIAGNÓSTICO (VERSÃO SIMPLIFICADA SEM ERROS) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                # 1. Configura a chave de forma direta
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                
                # 2. Define o modelo (usando a forma mais compatível possível)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner('O Mentor IA está analisando seus dados...'):
                    # Pega os dados que já aparecem na sua tela
                    contexto = user_data.tail(10).to_string()
                    
                    prompt = f"""
                    Você é o Mentor do Método Livre da Vontade.
                    Analise os seguintes registros de gatilhos:
                    {contexto}
                    
                    Dê um diagnóstico curto e uma orientação prática.
                    """
                    
                    # 3. Gera o conteúdo
                    response = model.generate_content(prompt)
                    
                    st.markdown("---")
                    st.markdown("### 🌿 Diagnóstico do Mentor")
                    st.info(response.text)
                    
            except Exception as e:
                st.error(f"Erro na IA: {e}")
                st.info("Verifique se sua API Key está ativa no Google AI Studio.")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

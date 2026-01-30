import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Configurações Iniciais
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")
st.title("🌿 Mentor IA - Método Livre da Vontade")

# 2. Conexão Simplificada
def iniciar_conexao():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    # Abra a NOVA planilha pelo nome para evitar erro de ID
    return client.open("BANCO_MENTOR_IA").worksheet("DADOS")

# 3. Lógica de Acesso
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_login = st.text_input("Digite seu e-mail:").strip().lower()
    if st.button("Entrar"):
        st.session_state.email = email_login
        st.session_state.logado = True
        st.rerun()
else:
    try:
        aba = iniciar_conexao()
        dados_brutos = aba.get_all_records()
        df = pd.DataFrame(dados_brutos)
        
        # Filtra os dados do aluno
        user_df = df[df['Email'].str.lower() == st.session_state.email]
        
        if not user_df.empty:
            st.success(f"Bem-vindo, {st.session_state.email}")
            st.table(user_df.tail(5))
            
            if st.button("🚀 Gerar Diagnóstico"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = f"Analise o histórico de gatilhos e dê um conselho curto: {user_df.to_string()}"
                res = model.generate_content(prompt)
                st.info(res.text)
        else:
            st.warning("Nenhum dado encontrado para este e-mail.")
            if st.button("Sair"):
                st.session_state.logado = False
                st.rerun()
                
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

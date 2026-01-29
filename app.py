import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configurações de Página
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

# --- FUNÇÃO DE CONEXÃO COM A PLANILHA ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha (Extraído da sua URL)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Pega a primeira aba disponível
        worksheet = sh.get_worksheet(0)
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Cria o DataFrame
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao ler Planilha: {e}")
        return pd.DataFrame()

# --- INTERFACE PRINCIPAL ---
st.title("🌿 Mentor IA - Método Livre da Vontade")

# Configuração da API Key do Gemini
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Tela de Login
    e_input = st.text_input("Digite o e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # App Logado
    df = conectar_planilha()
    
    if not df.empty:
        # Busca o aluno por e-mail em qualquer coluna
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Registros encontrados para: {st.session_state.user_email}")
            st.dataframe(user_data.tail(5))
            
            if st.button("🚀 GERAR DIAGNÓSTICO"):
                try:
                    # Removemos a linha os.environ["GOOGLE_API_VERSION"] para evitar o erro 400 de faturamento
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner('O Mentor está analisando...'):
                        contexto = user_data.tail(10).to_string()
                        prompt = f"Analise estes dados e dê um diagnóstico curto: {contexto}"
                        
                        # Chamada da IA
                        response = model.generate_content(prompt)
                        
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.info(response.text)
                        
                except Exception as e:
                    # Se o erro 400 for aqui, saberemos que é a API Key ou Faturamento
                    st.error(f"Erro na IA (Verifique a API Key nos Secrets): {e}")
        else:
            st.error("E-mail não localizado na base de dados.")
            if st.button("Voltar"):
                st.session_state.logged_in = False
                st.rerun()

# Botão Sair na barra lateral
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

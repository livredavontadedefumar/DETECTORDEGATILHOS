import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo nome exato da Foto 7c9c
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        
        dados = worksheet.get_all_values()
        if not dados:
            return pd.DataFrame()
            
        # Cria o DataFrame usando a primeira linha como cabeçalho
        df = pd.DataFrame(dados[1:], columns=dados[0])
        return df
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
else:
    df = conectar_planilha()
    
    if not df.empty:
        # Ajuste para o nome exato da coluna na Foto 7c9c: "Endereço de e-mail"
        coluna_email = "Endereço de e-mail"
        
        if coluna_email in df.columns:
            user_data = df[df[coluna_email].str.lower() == st.session_state.user_email]
            
            if not user_data.empty:
                st.success(f"Olá! Registros encontrados para {st.session_state.user_email}")
                st.dataframe(user_data.tail(10))
                
                if st.button("🚀 GERAR DIAGNÓSTICO"):
                    try:
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        with st.spinner('Analisando seu Raio-X...'):
                            contexto = user_data.tail(5).to_string()
                            prompt = f"Você é o Mentor do Método Livre da Vontade. Analise estes dados de gatilhos e dê um conselho firme e prático: {contexto}"
                            response = model.generate_content(prompt)
                            st.info(response.text)
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")
            else:
                st.warning(f"Nenhum dado encontrado para o e-mail: {st.session_state.user_email}")
        else:
            st.error(f"Coluna '{coluna_email}' não encontrada. Verifique os cabeçalhos da planilha.")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

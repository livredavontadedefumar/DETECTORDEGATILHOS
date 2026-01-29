import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Configuração básica
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        # Escopos de acesso
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Carrega credenciais dos Secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha (Extraído da foto e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Tenta abrir a aba MAPEAMENTO (Foto e2a8)
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            # Se falhar pelo nome, pega a segunda aba disponível (índice 1)
            worksheet = sh.get_worksheet(1)
            
        # Puxa os dados brutos
        dados = worksheet.get_all_values()
        if not dados:
            return pd.DataFrame()
            
        df = pd.DataFrame(dados[1:], columns=dados[0])
        # Limpa espaços nos nomes das colunas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Se o erro 400 persistir aqui, o problema é permissão no Google Cloud
        st.error(f"Erro técnico na conexão: {e}")
        return pd.DataFrame()

# Título e Configuração da IA
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca o e-mail do usuário em qualquer coluna
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Olá! Registros localizados para {st.session_state.user_email}")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('Analisando seu histórico...'):
                        contexto = user_data.tail(10).to_string()
                        prompt = f"Você é um mentor. Analise estes dados e dê um conselho prático: {contexto}"
                        response = model.generate_content(prompt)
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro ao gerar resposta da IA: {e}")
        else:
            st.warning("E-mail não localizado na aba MAPEAMENTO.")

# Botão para sair
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

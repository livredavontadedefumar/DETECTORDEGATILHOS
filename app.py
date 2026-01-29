import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Interface e Título
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")
st.title("🌿 Mentor IA - Método Livre da Vontade")

# --- CONEXÃO BLINDADA COM A PLANILHA ---
def conectar_planilha():
    try:
        # Escopos para Drive e Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Validação dos Secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID exato da sua planilha (Foto e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Tenta abrir a aba MAPEAMENTO (Foto e2a8). Se falhar, pega a segunda aba (índice 1).
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            worksheet = sh.get_worksheet(1) 
            
        # Puxa os valores brutos para evitar erro 400 (Request contains an invalid argument)
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Cria o DataFrame e limpa as colunas
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro de Conexão Google: {e}")
        return pd.DataFrame()

# Configuração Gemini (Foto 1a5c)
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Tela de Login
    e_input = st.text_input("Digite o e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # Dashboard do Aluno
    df = conectar_planilha()
    
    if not df.empty:
        # Busca o e-mail em qualquer coluna (Foto e2a8)
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Conectado: {st.session_state.user_email}")
            st.subheader("Seu Histórico de Gatilhos:")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR ORIENTAÇÃO DO MENTOR"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seu progresso...'):
                        contexto = user_data.tail(10).to_string()
                        prompt = f"Você é um mentor especialista. Analise estes dados e dê um diagnóstico curto: {contexto}"
                        response = model.generate_content(prompt)
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
        else:
            st.error(f"E-mail '{st.session_state.user_email}' não encontrado na aba MAPEAMENTO.")

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

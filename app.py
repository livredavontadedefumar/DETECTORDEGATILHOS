import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Força o faturamento Nível 1
os.environ["GOOGLE_API_VERSION"] = "v1"

st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

# --- CONFIGURAÇÃO DE ACESSO (CONTA DE SERVIÇO) ---
def conectar_planilha():
    try:
        # Puxa as credenciais JSON dos Secrets
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo ID fixo (extraído do seu link original)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet("MAPEAMENTO")
        
        # Converte para DataFrame do Pandas
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com a Conta de Serviço: {e}")
        return pd.DataFrame()

# Configuração da IA
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = conectar_planilha()
    if not df.empty:
        # Busca insensível a maiúsculas/minúsculas
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        
        if not user_data.empty:
            st.success("Registros localizados com sucesso!")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seu Raio-X...'):
                        contexto = user_data.tail(15).to_string()
                        
                        prompt_mestre = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Analise os gatilhos abaixo e forneça um diagnóstico de Nível 1.
                        DADOS DO ALUNO: {contexto}
                        ESTRUTURA:
                        1. PADRÃO IDENTIFICADO: Qual o maior erro emocional?
                        2. QUEBRA DE CICLO: Instrução prática imediata.
                        3. MENSAGEM DO MENTOR: Frase curta de encorajamento firme.
                        """
                        
                        response = model.generate_content(prompt_mestre)
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.info(response.text)
                except Exception as e:
                    st.error(f"IA indisponível: {e}")
        else:
            st.error("E-mail não encontrado na base de dados.")

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

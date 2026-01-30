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
        if len(dados) < 2:
            return pd.DataFrame()
            
        # Limpa espaços extras nos cabeçalhos para evitar o AttributeError
        headers = [str(h).strip() for h in dados[0]]
        df = pd.DataFrame(dados[1:], columns=headers)
        return df
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("Digite seu e-mail:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
else:
    df = conectar_planilha()
    
    if not df.empty:
        # BUSCA AUTOMÁTICA DA COLUNA DE E-MAIL
        # Procura qualquer coluna que tenha "e-mail" ou "email" no nome
        colunas_possiveis = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()]
        
        if colunas_possiveis:
            coluna_certa = colunas_possiveis[0]
            # Filtra os dados comparando apenas o texto limpo
            user_data = df[df[coluna_certa].str.strip().str.lower() == st.session_state.user_email]
            
            if not user_data.empty:
                st.success(f"Olá! Registros encontrados.")
                st.dataframe(user_data.tail(10))
                
                if st.button("🚀 GERAR DIAGNÓSTICO"):
                    try:
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        with st.spinner('Analisando seu Raio-X...'):
                            contexto = user_data.tail(5).to_string()
                            prompt = f"Você é o Mentor. Analise estes dados e dê um conselho curto: {contexto}"
                            response = model.generate_content(prompt)
                            st.info(response.text)
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")
            else:
                st.warning(f"Nenhum dado encontrado para: {st.session_state.user_email}")
                if st.button("Tentar outro e-mail"):
                    st.session_state.logado = False
                    st.rerun()
        else:
            st.error("Não encontramos a coluna de e-mail na planilha. Verifique o cabeçalho.")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

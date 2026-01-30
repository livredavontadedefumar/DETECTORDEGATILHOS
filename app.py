import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Configuração da página
st.set_page_config(page_title="Mentor IA", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Usa o bloco [gcp_service_account] dos seus Secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo nome exato (Foto 7c9c)
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        dados = worksheet.get_all_values()
        
        # Limpa cabeçalhos (evita erro da foto a09a)
        headers = [str(h).strip() for h in dados[0]]
        return pd.DataFrame(dados[1:], columns=headers)
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("E-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
else:
    df = conectar_planilha()
    
    if not df.empty:
        # Busca automática da coluna de e-mail (flexível)
        cols_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()]
        
        if cols_email:
            coluna_certa = cols_email[0]
            # Filtra os dados do aluno logado (visto na foto 3b31)
            user_data = df[df[coluna_certa].str.strip().str.lower() == st.session_state.user_email]
            
            if not user_data.empty:
                st.success(f"Olá! Registros encontrados.")
                st.dataframe(user_data.tail(10))
                
                # --- BOTÃO DE DIAGNÓSTICO (Corrige o Erro 404) ---
                if st.button("🚀 GERAR DIAGNÓSTICO"):
                    try:
                        # Usa APENAS a API Key do bloco [gemini] dos Secrets
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        
                        # Chama o modelo estável diretamente
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        with st.spinner('Analisando seu histórico...'):
                            contexto = user_data.tail(10).to_string()
                            prompt = f"Você é o Mentor IA. Analise estes gatilhos e dê um conselho firme: {contexto}"
                            
                            # Realiza a geração sem usar bibliotecas beta
                            response = model.generate_content(prompt)
                            st.markdown("---")
                            st.markdown("### 🌿 Diagnóstico do Mentor")
                            st.info(response.text)
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")
            else:
                st.warning(f"Nenhum dado encontrado para: {st.session_state.user_email}")
        else:
            st.error("Coluna de e-mail não encontrada na planilha.")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Configurações Iniciais
st.set_page_config(page_title="Mentor IA", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Usa o JSON do bloco [gcp_service_account] para o Sheets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha exata da sua foto 7c9c
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        dados = worksheet.get_all_values()
        
        # Limpa cabeçalhos para evitar erro de nomes (Foto a09a)
        headers = [str(h).strip() for h in dados[0]]
        df = pd.DataFrame(dados[1:], columns=headers)
        return df
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return pd.DataFrame()

# 2. Interface Principal
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email_input = st.text_input("Seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
else:
    df = conectar_planilha()
    
    if not df.empty:
        # Busca a coluna de e-mail (conforme foto 3b31)
        cols_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()]
        
        if cols_email:
            coluna_certa = cols_email[0]
            # Filtra os dados do aluno (visto na foto 3bdc)
            user_data = df[df[coluna_certa].str.strip().str.lower() == st.session_state.user_email]
            
            if not user_data.empty:
                st.success(f"Conectado: {st.session_state.user_email}")
                st.dataframe(user_data.tail(10))
                
                # --- BOTÃO DE DIAGNÓSTICO (Ajuste Final contra Erro 404) ---
                if st.button("🚀 GERAR DIAGNÓSTICO"):
                    try:
                        # Configura a IA apenas com a API Key do bloco [gemini]
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        
                        # FORÇANDO O USO DO MODELO SEM ROTA BETA (Mata o erro 404)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        with st.spinner('O Mentor IA está analisando seu Raio-X...'):
                            # Prepara os dados da planilha para a IA
                            contexto = user_data.tail(10).to_string()
                            
                            prompt = f"""
                            Você é o Mentor IA do Método Livre da Vontade.
                            Analise os seguintes registros de gatilhos:
                            {contexto}
                            
                            Dê um diagnóstico direto e uma orientação prática para o aluno.
                            """
                            
                            # Chamada de geração
                            response = model.generate_content(prompt)
                            
                            st.markdown("---")
                            st.markdown("### 🌿 Diagnóstico do Mentor")
                            st.info(response.text)
                            
                    except Exception as e:
                        st.error(f"Erro na IA: {e}")
                        st.info("Dica: Se o erro 404 persistir, dê um 'Reboot App' no painel do Streamlit.")
            else:
                st.warning(f"E-mail {st.session_state.user_email} não encontrado na planilha.")
        else:
            st.error("Coluna de e-mail não detectada.")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

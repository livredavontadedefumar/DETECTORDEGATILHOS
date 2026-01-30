import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Configurações de Página
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo nome exato (conforme sua foto 7c9c)
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        
        dados = worksheet.get_all_values()
        if len(dados) < 2:
            return pd.DataFrame()
            
        # Limpa espaços invisíveis nos cabeçalhos (evita o erro da foto a09a)
        headers = [str(h).strip() for h in dados[0]]
        df = pd.DataFrame(dados[1:], columns=headers)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return pd.DataFrame()

# 2. Interface Principal
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
        # Busca automática da coluna de e-mail (flexível para variações de nome)
        colunas_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()]
        
        if colunas_email:
            coluna_certa = colunas_email[0]
            # Filtra os registros do usuário atual
            user_data = df[df[coluna_certa].str.strip().str.lower() == st.session_state.user_email]
            
            if not user_data.empty:
                st.success(f"Olá! Registros encontrados para {st.session_state.user_email}")
                st.dataframe(user_data.tail(10))
                
                # --- BOTÃO DE DIAGNÓSTICO COM CORREÇÃO DO ERRO 404 ---
                if st.button("🚀 GERAR DIAGNÓSTICO"):
                    try:
                        # Configura a API Key do Gemini (Nível 1)
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        
                        # Chama o modelo 1.5-flash de forma estável
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        with st.spinner('O Mentor IA está analisando seu Raio-X...'):
                            # Envia os últimos 10 registros para uma análise mais rica
                            contexto = user_data.tail(10).to_string()
                            
                            prompt = f"""
                            Você é o Mentor IA do Método Livre da Vontade.
                            Com base nestes registros de gatilhos do aluno:
                            {contexto}
                            
                            Dê um diagnóstico direto, firme e encorajador.
                            Identifique padrões de comportamento e sugira uma ação prática baseada no método.
                            """
                            
                            response = model.generate_content(prompt)
                            st.markdown("---")
                            st.markdown("### 🌿 Diagnóstico do Mentor")
                            st.info(response.text)
                            
                    except Exception as e:
                        # Se der erro 404 aqui, verifique a API Key nos Secrets
                        st.error(f"Erro ao gerar diagnóstico (IA): {e}")
            else:
                st.warning(f"Nenhum registro encontrado para: {st.session_state.user_email}")
                if st.button("Tentar outro e-mail"):
                    st.session_state.logado = False
                    st.rerun()
        else:
            st.error("A coluna de e-mail não foi detectada na planilha.")
    else:
        st.info("Aguardando dados da planilha...")

# Botão para sair no menu lateral
if st.sidebar.button("Sair / Trocar de Conta"):
    st.session_state.logado = False
    st.rerun()

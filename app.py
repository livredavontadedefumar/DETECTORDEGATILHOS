import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configuração de Página
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

# --- FUNÇÃO DE CONEXÃO COM A PLANILHA ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha (visto na imagem e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # AJUSTE: Forçamos a leitura da primeira aba disponível (Form_Responses)
        worksheet = sh.get_worksheet(0)
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Cria o DataFrame e limpa os nomes das colunas
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao ler Planilha: {e}")
        return pd.DataFrame()

# --- INTERFACE PRINCIPAL ---
st.title("🌿 Mentor IA - Método Livre da Vontade")

# Configuração da API Key do Gemini (vinda dos Secrets)
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Interface de Login
    e_input = st.text_input("Digite o e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # App Logado
    df = conectar_planilha()
    
    if not df.empty:
        # Busca o aluno por e-mail em qualquer coluna (Flexível para cabeçalhos diferentes)
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Registros encontrados para: {st.session_state.user_email}")
            st.dataframe(user_data.tail(5))
            
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    # Uso do modelo Flash para evitar erros de cota gratuita
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner('O Mentor está analisando seu Raio-X...'):
                        contexto = user_data.tail(10).to_string()
                        
                        prompt_mestre = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Analise os gatilhos abaixo e forneça um diagnóstico de Nível 1.

                        DADOS DO ALUNO:
                        {contexto}

                        ESTRUTURA DO SEU DIAGNÓSTICO:
                        1. PADRÃO IDENTIFICADO: Qual o maior erro emocional deste aluno?
                        2. QUEBRA DE CICLO: Uma instrução prática imediata.
                        3. MENSAGEM DO MENTOR: Uma frase curta de encorajamento firme.
                        """
                        
                        response = model.generate_content(prompt_mestre)
                        
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.info(response.text)
                        
                except Exception as e:
                    st.error(f"Erro na análise da IA: {e}")
        else:
            st.error(f"O e-mail '{st.session_state.user_email}' não foi localizado na aba de respostas.")
            if st.button("Tentar outro e-mail"):
                st.session_state.logged_in = False
                st.rerun()

# Barra lateral para navegação
with st.sidebar:
    st.write(f"Conectado como: {st.session_state.get('user_email', '')}")
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

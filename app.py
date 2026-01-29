import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configurações de Interface
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID fixo da sua planilha (Extraído da imagem e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Tenta abrir a aba MAPEAMENTO. Se falhar, tenta a segunda aba da planilha.
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            worksheet = sh.get_worksheet(1) # Segunda aba, como visto na foto e2a8
            
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Organiza os dados em colunas limpas
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Mostra o erro exato para diagnóstico final
        st.error(f"Erro ao ler Planilha: {e}")
        return pd.DataFrame()

# Configuração da IA Gemini
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

# Sistema de Login Simples
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Digite o e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # Área Logada
    df = conectar_planilha()
    
    if not df.empty:
        # Procura o e-mail em qualquer lugar da linha (Garante que encontre o aluno)
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Bem-vindo! Localizamos seus registros.")
            
            # Mostra a tabela de gatilhos (Foto e2a8)
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seu progresso...'):
                        contexto = user_data.tail(15).to_string()
                        
                        prompt = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Analise os gatilhos abaixo e forneça um diagnóstico de Nível 1.

                        DADOS DO ALUNO: {contexto}

                        ESTRUTURA:
                        1. PADRÃO IDENTIFICADO: Qual o maior erro emocional?
                        2. QUEBRA DE CICLO: Instrução prática imediata.
                        3. MENSAGEM DO MENTOR: Frase curta de encorajamento firme.
                        """
                        response = model.generate_content(prompt)
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na análise da IA: {e}")
        else:
            st.error(f"E-mail '{st.session_state.user_email}' não encontrado na aba de mapeamento.")
            if st.button("Sair e tentar outro e-mail"):
                st.session_state.logged_in = False
                st.rerun()

# Barra lateral
with st.sidebar:
    st.write(f"Usuário: {st.session_state.get('user_email', '')}")
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configuração de Interface
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Puxa credenciais dos Secrets (Projeto gen-lang-client-0993867126)
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha (visto na imagem e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Tenta abrir especificamente a aba MAPEAMENTO (Foto e2a8)
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            # Se falhar pelo nome, pega a segunda aba (índice 1) onde estão os gatilhos
            worksheet = sh.get_worksheet(1)
            
        # Puxa os valores brutos para evitar erro de formato (Bad Request 400)
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Cria DataFrame e limpa nomes de colunas
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Exibe o erro técnico exato para diagnóstico final
        st.error(f"Erro de Conexão Google: {e}")
        return pd.DataFrame()

# Configuração Gemini (Chave Nível 1)
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Interface de Acesso
    e_input = st.text_input("Digite o e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # Área do Aluno
    df = conectar_planilha()
    
    if not df.empty:
        # Busca flexível: procura o e-mail em qualquer lugar da linha
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Conectado: {st.session_state.user_email}")
            
            # Exibe os dados de gatilhos (Foto e2a8)
            st.subheader("Seu Histórico de Gatilhos:")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR ORIENTAÇÃO DO MENTOR"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seu progresso...'):
                        # Prepara contexto para análise
                        contexto = user_data.tail(10).to_string()
                        
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
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na análise da IA: {e}")
        else:
            st.error(f"E-mail '{st.session_state.user_email}' não encontrado nos registros.")
            if st.button("Tentar outro e-mail"):
                st.session_state.logged_in = False
                st.rerun()

# Sidebar
with st.sidebar:
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

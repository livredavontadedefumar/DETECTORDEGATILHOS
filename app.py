import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

def conectar():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Usa o JSON que já está nos seus Secrets
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    # Abre a planilha pelo nome exato que você criou
    return client.open("BANCO_MENTOR_IA").sheet1 # sheet1 pega a primeira aba automaticamente

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    email = st.text_input("Digite seu e-mail:").strip().lower()
    if st.button("Acessar"):
        st.session_state.email = email
        st.session_state.logado = True
        st.rerun()
else:
    try:
        aba = conectar()
        # Pega todos os valores da planilha
        dados = aba.get_all_values()
        
        if len(dados) > 1:
            df = pd.DataFrame(dados[1:], columns=dados[0])
            # Filtra pelo e-mail do aluno
            user_df = df[df.iloc[:, 1].str.lower() == st.session_state.email] # Assume que Email é a 2ª coluna
            
            if not user_df.empty:
                st.success(f"Dados encontrados para {st.session_state.email}")
                st.dataframe(user_df.tail(5))
                
                if st.button("🚀 Gerar Diagnóstico"):
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Analise brevemente: {user_df.tail(3).to_string()}"
                    res = model.generate_content(prompt)
                    st.info(res.text)
            else:
                st.warning("E-mail não encontrado na planilha.")
        else:
            st.error("A planilha está vazia! Adicione pelo menos uma linha de dados abaixo dos cabeçalhos.")
            
    except Exception as e:
        st.error(f"Erro técnico: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

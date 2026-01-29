import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# Forçamos a versão v1 para garantir o uso do seu bônus de R$ 1.904,08
os.environ["GOOGLE_API_VERSION"] = "v1"

st.set_page_config(page_title="Raio-X 2.0", page_icon="🌿")

# O código buscará a chave nos Secrets do Streamlit, não aqui no código
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

def carregar_dados():
    try:
        url_csv = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = pd.read_csv(url_csv)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro nos dados: {e}")
        return pd.DataFrame()

st.title("🌿 Diagnóstico Raio-X 2.0")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        st.session_state.user_email = e_input
        st.session_state.logged_in = True
        st.rerun()
else:
    df = carregar_dados()
    if not df.empty:
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        if not user_data.empty:
            if st.button("Gerar Análise IA"):
                try:
                    # Usando gemini-1.5-flash com sua nova chave Nível 1
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando...'):
                        contexto = user_data.tail(15).to_string()
                        response = model.generate_content(f"Analise estes registros de gatilhos: {contexto}")
                        st.markdown("---")
                        st.write(response.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")
        else:
            st.error("E-mail não encontrado.")
    
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

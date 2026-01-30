import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

st.set_page_config(page_title="Mentor IA", page_icon="🌿")

# --- 1. CONEXÃO COM A PLANILHA (Google Sheets) ---
def conectar_planilha():
    try:
        # Define as permissões necessárias
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # BUSCA AS CREDENCIAIS NO COFRE (Secrets) DO STREAMLIT
        # O bloco JSON da sua Conta de Serviço deve estar cadastrado lá
        creds_dict = st.secrets["SUA_CONTA_GOOGLE_CLOUD_AQUI_BLOCO_JSON"]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo nome exato que está no seu Google Drive
        sh = client.open("NOME_DA_SUA_PLANILHA_AQUI")
        worksheet = sh.worksheet("NOME_DA_ABA_DADOS_AQUI")
        
        dados = worksheet.get_all_values()
        headers = [str(h).strip() for h in dados[0]]
        return pd.DataFrame(dados[1:], columns=headers)
    except Exception as e:
        st.error(f"Erro na Planilha: {e}")
        return pd.DataFrame()

# --- 2. INTERFACE DO USUÁRIO ---
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
    # Carrega os dados da planilha
    df = conectar_planilha()
    
    if not df.empty:
        # Tenta encontrar a coluna de e-mail automaticamente
        col_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()][0]
        
        # Filtra apenas os dados do usuário logado
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        
        st.success(f"Conectado: {st.session_state.user_email}")
        st.dataframe(user_data.tail(10))

        # --- 3. GERAÇÃO DO DIAGNÓSTICO (CHAMADA DA IA) ---
        if st.button("🚀 GERAR DIAGNÓSTICO"):
            try:
                # BUSCA A API KEY (NÍVEL 1) NO COFRE DO STREAMLIT
                api_key = st.secrets["gemini"]["SUA_CHAVE_API_NIVEL_1_AQUI"]
                
                # URL CONFIGURADA PARA O MODELO MAIS ESTÁVEL (Mata o erro 404)
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.0-pro:generateContent?key={api_key}"
                
                # Prepara o contexto com os últimos 10 registros
                contexto = user_data.tail(10).to_string()
                
                # Payload formatado para a versão v1 da API do Google
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"Você é o Mentor IA. Analise estes gatilhos e dê um diagnóstico firme: {contexto}"
                        }]
                    }]
                }
                
                headers = {'Content-Type': 'application/json'}
                
                with st.spinner('O Mentor está analisando seu Raio-X...'):
                    response = requests.post(url, headers=headers, json=payload)
                    resultado = response.json()
                    
                    if response.status_code == 200:
                        # Extrai o texto da resposta da IA
                        texto_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                        st.markdown("---")
                        st.markdown("### 🌿 Diagnóstico do Mentor")
                        st.info(texto_ia)
                    else:
                        st.error(f"Erro {response.status_code}: Verifique a API Key e o Billing no Google Cloud.")
            except Exception as e:
                st.error(f"Erro técnico ao chamar a IA: {e}")

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()


Esse é o meu código python, verificar se há algo a reparar??

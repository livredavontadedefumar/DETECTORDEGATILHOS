import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

# Configuração da Página
st.set_page_config(page_title="Mentor IA", page_icon="🌿", layout="centered")

# --- 1. FUNÇÃO DE CONEXÃO COM A PLANILHA ---
def conectar_planilha():
    try:
        # Escopo de permissão
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Puxa o bloco JSON da Conta de Serviço dos Secrets
        # No Streamlit Secrets deve estar como [gcp_service_account]
        creds_dict = st.secrets["gcp_service_account"]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo nome (Certifique-se que o e-mail da conta de serviço está como editor nela)
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        
        dados = worksheet.get_all_values()
        if not dados:
            return pd.DataFrame()
            
        headers = [str(h).strip() for h in dados[0]]
        return pd.DataFrame(dados[1:], columns=headers)
    except Exception as e:
        st.error(f"Erro ao conectar na Planilha: {e}")
        return pd.DataFrame()

# --- 2. INTERFACE E LOGICA DE ACESSO ---
st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.subheader("Acesso ao Raio-X")
    email_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
    
    if st.button("Acessar Mapeamento"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
        else:
            st.warning("Por favor, insira um e-mail válido.")

else:
    # Fluxo principal após login
    df = conectar_planilha()
    
    if not df.empty:
        # Busca segura pela coluna de e-mail (evita erro de coluna inexistente)
        colunas_email = [c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()]
        
        if not colunas_email:
            st.error("Erro: A coluna de E-mail não foi encontrada na sua planilha.")
            st.stop()
            
        col_email = colunas_email[0]
        
        # Filtra os dados do usuário
        user_data = df[df[col_email].str.strip().str.lower() == st.session_state.user_email]
        
        if user_data.empty:
            st.warning(f"Nenhum registro encontrado para o e-mail: {st.session_state.user_email}")
        else:
            st.success(f"Olá! Exibindo seus últimos registros.")
            st.dataframe(user_data.tail(10))

            # --- 3. CHAMADA CIRÚRGICA DA IA (Gemini 1.0 Pro) ---
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    # Puxa a API Key nível 1 do bloco [gemini][api_key]
                    api_key = st.secrets["gemini"]["api_key"]
                    
                    # Endpoint v1 estável com modelo 1.0-pro (Mata o erro 404)
                    base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                    
                    # Prepara os dados para análise
                    contexto = user_data.tail(10).to_string()
                    
                    payload = {
                        "contents": [{
                            "parts": [{
                                "text": f"Você é o Mentor IA do Método Livre da Vontade. Analise os gatilhos abaixo e forneça um diagnóstico firme, prático e motivador:\n\n{contexto}"
                            }]
                        }]
                    }
                    
                    headers = {"Content-Type": "application/json"}
                    
                    with st.spinner('O Mentor está processando seus dados...'):
                        # Chamada com timeout de 30 segundos para estabilidade
                        response = requests.post(
                            f"{base_url}?key={api_key}",
                            headers=headers,
                            json=payload,
                            timeout=30
                        )
                        
                        resultado = response.json()
                        
                        if response.status_code == 200:
                            # Sucesso: Extrai e exibe a resposta
                            texto_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                            st.markdown("---")
                            st.markdown("### 🌿 Resposta do Mentor")
                            st.info(texto_ia)
                        else:
                            # Diagnóstico detalhado em caso de erro (Billing, Cota ou Chave)
                            msg_erro = resultado.get('error', {}).get('message', 'Erro desconhecido no Google Cloud')
                            st.error(f"Erro {response.status_code} na API: {msg_erro}")
                            
                except Exception as e:
                    st.error(f"Ocorreu uma falha técnica na comunicação: {e}")

    # Botão para trocar de usuário
    if st.sidebar.button("Sair / Trocar E-mail"):
        st.session_state.logado = False
        st.rerun()

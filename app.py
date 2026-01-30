import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Configurações Iniciais do Aplicativo
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Usa as credenciais da conta de serviço salvas nos Secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Abre a planilha pelo nome exato conforme Foto 7c9c
        sh = client.open("BANCO-MENTOR-IA")
        worksheet = sh.worksheet("DADOS")
        
        dados = worksheet.get_all_values()
        if len(dados) < 2:
            return pd.DataFrame()
            
        # Limpa os cabeçalhos para evitar erros de nomes de colunas
        headers = [str(h).strip() for h in dados[0]]
        df = pd.DataFrame(dados[1:], columns=headers)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar na planilha: {e}")
        return pd.DataFrame()

# 2. Interface do Mentor IA
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
            # Filtra os dados do aluno logado
            user_data = df[df[coluna_certa].str.strip().str.lower() == st.session_state.user_email]
            
            if not user_data.empty:
                st.success(f"Olá! Registros encontrados para {st.session_state.user_email}")
                st.dataframe(user_data.tail(10))
                
                # --- BOTÃO DE DIAGNÓSTICO COM CORREÇÃO DO ERRO 404 ---
                if st.button("🚀 GERAR DIAGNÓSTICO"):
                    try:
                        # Configura a chave da IA que está nos seus Secrets
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        
                        # CHAMA O MODELO ESTÁVEL (Corrige o erro 404 da foto 0222)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                        with st.spinner('O Mentor IA está analisando seus dados...'):
                            contexto = user_data.tail(10).to_string()
                            
                            prompt = f"""
                            Você é o Mentor IA do Método Livre da Vontade.
                            Com base nestes registros de gatilhos:
                            {contexto}
                            
                            Dê um diagnóstico direto, firme e encorajador para o aluno.
                            Foque em padrões que você percebeu e sugira uma ação prática imediata.
                            """
                            
                            response = model.generate_content(prompt)
                            st.markdown("---")
                            st.markdown("### 🌿 Diagnóstico do Mentor")
                            st.info(response.text)
                    except Exception as e:
                        st.error(f"Erro ao gerar diagnóstico: {e}")
            else:
                st.warning(f"Nenhum dado encontrado para: {st.session_state.user_email}")
        else:
            st.error("Não encontramos a coluna de e-mail na planilha. Verifique os cabeçalhos.")

# Barra lateral para logout
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configurações de Ambiente
os.environ["GOOGLE_API_VERSION"] = "v1"
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da sua planilha extraído da URL na imagem e2a8
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # Acessa a primeira aba (Foto e2a8 mostra a aba 'Form_Responses')
        worksheet = sh.get_worksheet(0)
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Cria o DataFrame e limpa nomes de colunas
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro na conexão com a planilha: {e}")
        return pd.DataFrame()

# Configuração Gemini
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Digite seu e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = carregar_dados = conectar_planilha()
    if not df.empty:
        # Busca o e-mail em qualquer coluna para evitar erro de nome de cabeçalho
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Registros localizados para: {st.session_state.user_email}")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                # Captura os dados para o prompt
                contexto_bruto = user_data.tail(15).to_string()
                
                if len(contexto_bruto) > 20:
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        with st.spinner('O Mentor está analisando seu Raio-X...'):
                            prompt_mestre = f"""
                            Você é o Mentor Especialista do Método Livre da Vontade. 
                            Analise os gatilhos abaixo e forneça um diagnóstico de Nível 1.

                            DADOS DO ALUNO:
                            {contexto_bruto}

                            ESTRUTURA DO SEU DIAGNÓSTICO:
                            1. PADRÃO IDENTIFICADO: Qual o maior erro emocional deste aluno?
                            2. QUEBRA DE CICLO: Uma instrução prática para o próximo gatilho.
                            3. MENSAGEM DO MENTOR: Uma frase curta de encorajamento firme.
                            """
                            response = model.generate_content(prompt_mestre)
                            st.markdown("---")
                            st.subheader("💡 Orientação do Mentor:")
                            st.info(response.text)
                    except Exception as e:
                        st.error(f"Erro ao gerar diagnóstico (Verifique API Key): {e}")
                else:
                    st.warning("Dados insuficientes para gerar uma análise precisa.")
        else:
            st.error(f"O e-mail '{st.session_state.user_email}' não foi encontrado nos dados da planilha.")
            if st.button("Tentar outro e-mail"):
                st.session_state.logged_in = False
                st.rerun()

# Sidebar para sair
with st.sidebar:
    st.write(f"Logado como: {st.session_state.get('user_email', '')}")
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

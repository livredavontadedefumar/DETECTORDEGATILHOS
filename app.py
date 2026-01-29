import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Configurações de Interface
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        # Escopos de acesso
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Carrega credenciais dos Secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha extraído da Foto e2a8
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # ESTRATÉGIA ANTI-ERRO 400: 
        # Pegamos a primeira aba que contém dados, independente do nome
        worksheet = sh.get_worksheet(0)
        
        # Leitura bruta de valores (get_all_values é mais estável que get_all_records)
        dados_brutos = worksheet.get_all_values()
        
        if not dados_brutos:
            return pd.DataFrame()
            
        # Transforma em DataFrame usando a primeira linha como cabeçalho
        df = pd.DataFrame(dados_brutos[1:], columns=dados_brutos[0])
        
        # Limpa espaços em branco nos nomes das colunas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Exibe o erro técnico exato para diagnóstico
        st.error(f"Erro na conexão com os dados: {e}")
        return pd.DataFrame()

# Configuração da IA (Chave Nível 1)
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Tela de Acesso
    e_input = st.text_input("Digite o seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Sistema"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # Área do Aluno
    df = conectar_planilha()
    
    if not df.empty:
        # Busca o e-mail em qualquer coluna (Flexível)
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Conectado: {st.session_state.user_email}")
            
            # Mostra o histórico (Foto e2a8)
            st.subheader("Seu Mapeamento Recente:")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seu Raio-X...'):
                        contexto = user_data.tail(15).to_string()
                        
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
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na análise da IA: {e}")
        else:
            st.error(f"E-mail '{st.session_state.user_email}' não localizado na base de dados.")
            if st.button("Voltar"):
                st.session_state.logged_in = False
                st.rerun()

# Barra lateral para sair
with st.sidebar:
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

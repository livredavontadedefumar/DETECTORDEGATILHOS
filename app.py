import streamlit as st
import google.generativeai as genai
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Configuração de Página
st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

def conectar_planilha():
    try:
        # Escopos necessários
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # Puxa credenciais dos Secrets
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # ID da planilha (visto na URL da imagem e2a8)
        spreadsheet_id = "16EeafLByraXRhOh6FRhOiHTnUQCja8YEfBDlgUGH_yT8"
        sh = client.open_by_key(spreadsheet_id)
        
        # AJUSTE: Tentamos abrir especificamente a aba MAPEAMENTO (Foto e2a8)
        try:
            worksheet = sh.worksheet("MAPEAMENTO")
        except:
            # Se falhar pelo nome, pega a segunda aba (que é a MAPEAMENTO na foto e2a8)
            worksheet = sh.get_worksheet(1)
            
        valores = worksheet.get_all_values()
        
        if not valores:
            return pd.DataFrame()
            
        # Cria DataFrame e limpa colunas
        df = pd.DataFrame(valores[1:], columns=valores[0])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao ler Planilha: {e}")
        return pd.DataFrame()

# Título do App
st.title("🌿 Mentor IA - Método Livre da Vontade")

# Configura o Gemini com sua chave dos Secrets
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Tela de Acesso
    e_input = st.text_input("Digite o e-mail cadastrado na planilha:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    # App logado com sucesso
    df = conectar_planilha()
    
    if not df.empty:
        # Filtra o usuário por e-mail em qualquer coluna
        mask = df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Conectado: {st.session_state.user_email}")
            
            # Mostra os dados (Foto e2a8)
            st.subheader("Seu Histórico de Gatilhos:")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR ORIENTAÇÃO DO MENTOR"):
                try:
                    # Usamos o 1.5-flash para garantir estabilidade no plano free
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner('O Mentor está analisando seu progresso...'):
                        # Prepara o contexto para a IA
                        contexto = user_data.tail(15).to_string()
                        
                        prompt_mestre = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Analise os gatilhos abaixo e forneça um diagnóstico de Nível 1.

                        DADOS DO ALUNO:
                        {contexto}

                        ESTRUTURA DA RESPOSTA:
                        1. PADRÃO IDENTIFICADO: Qual o maior erro emocional deste aluno?
                        2. QUEBRA DE CICLO: Uma instrução prática imediata.
                        3. MENSAGEM DO MENTOR: Uma frase curta de encorajamento firme.
                        """
                        
                        response = model.generate_content(prompt_mestre)
                        st.markdown("---")
                        st.info(response.text)
                        
                except Exception as e:
                    st.error(f"Erro ao gerar resposta da IA: {e}")
        else:
            st.error(f"E-mail '{st.session_state.user_email}' não encontrado na aba MAPEAMENTO.")
            if st.button("Sair / Tentar outro"):
                st.session_state.logged_in = False
                st.rerun()

# Botão Sair na Lateral
if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

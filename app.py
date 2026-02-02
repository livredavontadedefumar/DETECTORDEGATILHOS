import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# Configuração da Página
st.set_page_config(page_title="Mentor IA - Livre da Vontade", page_icon="🌿", layout="wide")

# --- 1. FUNÇÃO DE CONEXÃO E LEITURA DE DADOS ---
def buscar_dados_aluno(email_usuario):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Conexão pelo nome exato do arquivo que você definiu
        sh = client.open("MAPEAMENTO (respostas)")
        
        # 1. Busca Perfil na aba ENTREVISTA INICIAL
        ws_perfil = sh.worksheet("ENTREVISTA INICIAL")
        df_perfil_total = pd.DataFrame(ws_perfil.get_all_records())
        
        # 2. Busca Gatilhos na aba MAPEAMENTO
        ws_gatilhos = sh.worksheet("MAPEAMENTO")
        df_gatilhos_total = pd.DataFrame(ws_gatilhos.get_all_records())

        # Filtro por e-mail (flexível para variações no nome da coluna)
        def filtrar_por_email(df, email):
            if df.empty: return pd.DataFrame()
            col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
            if col_email:
                return df[df[col_email].str.strip().str.lower() == email.lower()]
            return pd.DataFrame()

        perfil_aluno = filtrar_por_email(df_perfil_total, email_usuario)
        gatilhos_aluno = filtrar_por_email(df_gatilhos_total, email_usuario)

        return perfil_aluno, gatilhos_aluno

    except Exception as e:
        st.error(f"Erro ao acessar as planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 2. INTERFACE ---
st.title("🌿 Mentor IA - Método Clayton Chalegre")

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.subheader("Acesse seu Mapeamento Personalizado")
    email_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
    
    if st.button("Acessar Mentor"):
        if email_input:
            st.session_state.user_email = email_input
            st.session_state.logado = True
            st.rerun()
else:
    with st.spinner("Consultando seu histórico nas abas de Mapeamento..."):
        perfil, gatilhos = buscar_dados_aluno(st.session_state.user_email)
    
    if perfil.empty and gatilhos.empty:
        st.warning(f"Nenhum registro encontrado para {st.session_state.user_email}.")
        if st.button("Voltar"):
            st.session_state.logado = False
            st.rerun()
    else:
        st.success(f"Bem-vindo(a), {st.session_state.user_email}!")
        
        # Mostra o contexto para o usuário
        col1, col2 = st.columns(2)
        with col1:
            if not perfil.empty:
                st.info("✅ Perfil Inicial Identificado")
                # Exibe de forma mais limpa apenas a última resposta
                st.write(perfil.tail(1).T) 
        with col2:
            if not gatilhos.empty:
                st.info("✅ Gatilhos Recentes Mapeados")
                st.dataframe(gatilhos.tail(5))

        # --- 3. LÓGICA DA IA (BIBLIOTECA OFICIAL) ---
        if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
            try:
                # Configuração da API Oficial
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                
                # Preparação do Contexto
                contexto_perfil = perfil.tail(1).to_dict(orient='records')
                contexto_gatilhos = gatilhos.tail(5).to_dict(orient='records')
                
                prompt_mentor = f"""
                Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', criado por Clayton Chalegre.
                Sua base técnica é a Análise Funcional (Alberto Dell'Isola) e o Condicionamento Pavloviano.

                DADOS DO ALUNO:
                Perfil: {contexto_perfil}
                Gatilhos Recentes: {contexto_gatilhos}

                SUA MISSÃO:
                1. Identifique o padrão: Como o perfil emocional do aluno (ex: ver o cigarro como companhia) explica os gatilhos recentes?
                2. Use a ciência: Explique brevemente que o desejo é apenas um disparo de dopamina (previsão de prazer).
                3. Instrução Prática: Dê uma ordem direta baseada no método (ex: respiração 4-7-8 ou desvio de padrão).
                4. Estilo: Seja firme como o Clayton, acolhedor mas sem aceitar desculpas do vício.

                Responda em português de forma direta e transformadora.
                """

                with st.spinner('O Mentor está processando sua libertação...'):
                    response = model.generate_content(prompt_mentor)
                    
                    if response.text:
                        st.markdown("---")
                        st.markdown("### 🌿 Resposta Personalizada do Mentor")
                        st.info(response.text)
                    else:
                        st.error("O Gemini não retornou uma resposta válida.")

            except Exception as e:
                st.error(f"Erro na conexão com a Inteligência Artificial: {e}")

    if st.sidebar.button("Trocar Usuário"):
        st.session_state.logado = False
        st.rerun()

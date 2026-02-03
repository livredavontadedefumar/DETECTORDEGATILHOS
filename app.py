import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# Configuração da Página
st.set_page_config(page_title="Mentor IA - Livre da Vontade", page_icon="🌿", layout="wide")

# --- 1. FUNÇÕES DE CONEXÃO E LEITURA ---
def conectar_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(credentials)

def buscar_todos_os_dados():
    try:
        client = conectar_google_sheets()
        sh = client.open("MAPEAMENTO (respostas)")
        
        ws_perfil = sh.worksheet("ENTREVISTA INICIAL")
        df_perfil = pd.DataFrame(ws_perfil.get_all_records())
        
        ws_gatilhos = sh.worksheet("MAPEAMENTO")
        df_gatilhos = pd.DataFrame(ws_gatilhos.get_all_records())
        
        return df_perfil, df_gatilhos
    except Exception as e:
        st.error(f"Erro ao acessar planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame()

# --- 2. ÁREA ADMINISTRATIVA (PAINEL DO FUNDADOR) ---
def area_administrativa(df_perfil, df_gatilhos):
    st.title("📊 Painel Administrativo - Visão Global")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Alunos", len(df_perfil))
    col2.metric("Total de Gatilhos Mapeados", len(df_gatilhos))
    
    st.subheader("Análise Estratégica da IA (Todos os Alunos)")
    if st.button("🧐 GERAR INSIGHTS COLETIVOS"):
        try:
            genai.configure(api_key=st.secrets["gemini"]["api_key"])
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Resumo para a IA focar no comportamento de massa
            resumo_global = df_gatilhos.tail(150).to_string() 
            
            prompt_admin = f"""
            Você é o consultor estratégico do Clayton Chalegre. Analise estes dados coletivos de alunos:
            {resumo_global}
            
            MISSÃO:
            1. Identifique o padrão de massa: Qual o comportamento/gatilho mais comum entre todos?
            2. Analise horários e locais críticos da audiência.
            3. Sugestão de Conteúdo: Qual tema de vídeo geraria mais engajamento baseado nessas dores reais?
            """
            
            with st.spinner("Analisando dados da comunidade..."):
                response = model.generate_content(prompt_admin)
                st.info(response.text)
        except Exception as e:
            st.error(f"Erro na análise global: {e}")

# --- 3. INTERFACE PRINCIPAL ---
st.sidebar.title("🌿 Menu de Navegação")
menu = st.sidebar.radio("Ir para:", ["Área do Aluno", "Área Administrativa"])

df_perfil_total, df_gatilhos_total = buscar_todos_os_dados()

# Variável de controle de login
if "logado" not in st.session_state:
    st.session_state.logado = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if menu == "Área Administrativa":
    # Trava 1: Verifica se o e-mail logado é o administrador
    admin_email = "livredavontadedefumar@gmail.com"
    
    if st.session_state.user_email != admin_email:
        st.warning("⚠️ Esta área é restrita ao administrador. Por favor, faça login com o e-mail oficial.")
        if not st.session_state.logado:
            email_admin_input = st.text_input("E-mail do Administrador:").strip().lower()
            if st.button("Validar E-mail"):
                if email_admin_input == admin_email:
                    st.session_state.user_email = email_admin_input
                    st.rerun()
                else:
                    st.error("E-mail não autorizado para esta área.")
    else:
        # Trava 2: Verifica a senha
        senha_admin = st.sidebar.text_input("Senha de Acesso", type="password")
        if senha_admin == st.secrets.get("admin_password", "clayton123"):
            area_administrativa(df_perfil_total, df_gatilhos_total)
        elif senha_admin:
            st.sidebar.error("Senha incorreta.")

else:
    st.title("🌿 Mentor IA - Livre da Vontade de Fumar")

    if not st.session_state.logado:
        st.subheader("Bem-vindo! Acesse seu Mapeamento")
        email_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
        
        if st.button("Entrar no Mentor"):
            if email_input:
                st.session_state.user_email = email_input
                st.session_state.logado = True
                st.rerun()
    else:
        # Filtro de dados do aluno logado
        col_email_p = next((c for c in df_perfil_total.columns if "email" in c.lower()), None)
        col_email_g = next((c for c in df_gatilhos_total.columns if "email" in c.lower()), None)
        
        perfil = df_perfil_total[df_perfil_total[col_email_p].str.strip().str.lower() == st.session_state.user_email] if col_email_p else pd.DataFrame()
        gatilhos = df_gatilhos_total[df_gatilhos_total[col_email_g].str.strip().str.lower() == st.session_state.user_email] if col_email_g else pd.DataFrame()

        if perfil.empty and gatilhos.empty:
            st.warning(f"Nenhum registro encontrado para {st.session_state.user_email}.")
            if st.button("Trocar Conta"):
                st.session_state.logado = False
                st.session_state.user_email = ""
                st.rerun()
        else:
            st.success(f"Logado como: {st.session_state.user_email}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.info("✅ Resumo do Seu Perfil")
                st.write(perfil.tail(1).T)
            with c2:
                st.info("✅ Seus Últimos Registros")
                st.dataframe(gatilhos.tail(5))

            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    prompt_mentor = f"""
                    Você é o Mentor IA de Clayton Chalegre. 
                    ALUNO: {st.session_state.user_email}
                    PERFIL: {perfil.tail(1).to_dict()}
                    GATILHOS: {gatilhos.tail(10).to_dict()}

                    INSTRUÇÕES:
                    1. Faça a limpeza semântica das intenções (ex: relaxar/cansado).
                    2. Identifique os 'Sinos de Pavlov' críticos.
                    3. Explique o erro de previsão de dopamina.
                    4. Dê ordens práticas de antecipação.
                    Fale como o Clayton: Firme, sem julgamentos e direto.
                    """

                    with st.spinner('Analisando sua jornada...'):
                        response = model.generate_content(prompt_mentor)
                        st.markdown("---")
                        st.markdown("### 🌿 Sua Orientação Personalizada")
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na análise: {e}")

    if st.sidebar.button("Logoff / Sair"):
        st.session_state.logado = False
        st.session_state.user_email = ""
        st.rerun()

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
            
            # Resumo para a IA não estourar limite de tokens, focando no que importa
            resumo_global = df_gatilhos.tail(100).to_string() # Analisa os últimos 100 registros
            
            prompt_admin = f"""
            Você é o consultor estratégico do Clayton Chalegre. Analise estes dados coletivos de alunos:
            {resumo_global}
            
            MISSÃO:
            1. Identifique o perfil comum: Qual o maior gatilho da sua audiência hoje?
            2. Horários e Emoções: Existe um padrão de horário ou sentimento que domina os alunos?
            3. Sugestão de Conteúdo: Baseado nisso, qual tema Clayton deve abordar no próximo vídeo para ajudar o maior número de pessoas?
            """
            
            with st.spinner("Analisando Big Data..."):
                response = model.generate_content(prompt_admin)
                st.light_content = response.text
                st.info(st.light_content)
        except Exception as e:
            st.error(f"Erro na análise global: {e}")

# --- 3. INTERFACE PRINCIPAL ---
st.sidebar.title("Configurações")
menu = st.sidebar.radio("Navegação", ["Área do Aluno", "Área Administrativa"])

df_perfil_total, df_gatilhos_total = buscar_todos_os_dados()

if menu == "Área Administrativa":
    # Senha simples para proteção
    senha = st.sidebar.text_input("Senha Admin", type="password")
    if senha == st.secrets.get("admin_password", "clayton123"): # Defina no secrets ou use padrão
        area_administrativa(df_perfil_total, df_gatilhos_total)
    else:
        st.error("Acesso negado.")

else:
    st.title("🌿 Mentor IA - Método Clayton Chalegre")

    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        st.subheader("Acesse seu Mapeamento Personalizado")
        email_input = st.text_input("Digite seu e-mail:").strip().lower()
        
        if st.button("Acessar Mentor"):
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
            st.warning("Nenhum registro encontrado.")
            if st.button("Sair"):
                st.session_state.logado = False
                st.rerun()
        else:
            st.success(f"Conectado: {st.session_state.user_email}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.info("✅ Perfil Inicial")
                st.write(perfil.tail(1).T)
            with c2:
                st.info("✅ Seus Últimos Gatilhos")
                st.dataframe(gatilhos.tail(5))

            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    prompt_mentor = f"""
                    Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', mestre na metodologia Clayton Chalegre e Alberto Dell'Isola.
                    
                    DADOS DO ALUNO:
                    Perfil: {perfil.tail(1).to_dict()}
                    Histórico de Gatilhos: {gatilhos.tail(10).to_dict()}

                    SUA MISSÃO:
                    1. LIMPEZA SEMÂNTICA: Agrupe variações como 'pra relaxar', 'estou cansado' ou 'descansar' como a mesma intenção funcional.
                    2. DASHBOARD NARRATIVO: Resuma os horários críticos e o principal 'Sino de Pavlov' (gatilho).
                    3. ANÁLISE DE ENFRENTAMENTO: Explique a falsa necessidade do cigarro para realizar tarefas (Dopamina/Erro de Previsão).
                    4. PLANO DE ATAQUE: Dê 2 ordens práticas de antecipação para o aluno aplicar agora.
                    
                    ESTILO: Firme, transformador e direto (Voz do Clayton).
                    """

                    with st.spinner('Analisando padrões...'):
                        response = model.generate_content(prompt_mentor)
                        st.markdown("---")
                        st.markdown("### 🌿 Diagnóstico Personalizado")
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

    if st.sidebar.button("Trocar Usuário"):
        st.session_state.logado = False
        st.rerun()

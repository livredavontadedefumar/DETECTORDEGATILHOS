import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Mentor IA - Livre da Vontade", page_icon="🌿", layout="wide")

# --- 1. CONEXÃO COM GOOGLE SHEETS ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        sh = client.open("MAPEAMENTO (respostas)")
        return sh
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

def carregar_todos_os_dados():
    sh = conectar_planilha()
    if sh:
        try:
            ws_perfil = sh.worksheet("ENTREVISTA INICIAL")
            ws_gatilhos = sh.worksheet("MAPEAMENTO")
            df_p = pd.DataFrame(ws_perfil.get_all_records())
            df_g = pd.DataFrame(ws_gatilhos.get_all_records())
            return df_p, df_g
        except Exception as e:
            st.error(f"Erro ao ler abas: {e}")
    return pd.DataFrame(), pd.DataFrame()

# --- CARREGAMENTO INICIAL ---
df_perfil_total, df_gatilhos_total = carregar_todos_os_dados()

# --- 2. MENU LATERAL ---
st.sidebar.title("🌿 Menu de Navegação")
pagina = st.sidebar.radio("Ir para:", ["Área do Aluno", "Área Administrativa"])

# --- ÁREA DO ALUNO ---
if pagina == "Área do Aluno":
    st.title("🌿 Meu Mapeamento - Mentor IA")
    
    if "user_email" not in st.session_state:
        email_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
        if st.button("Acessar Meus Dados"):
            if email_input:
                st.session_state.user_email = email_input
                st.rerun()
    else:
        email = st.session_state.user_email
        
        def filtrar_aluno(df, email_aluno):
            if df.empty: return pd.DataFrame()
            col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
            if col_email:
                df[col_email] = df[col_email].astype(str).str.strip().str.lower()
                return df[df[col_email] == email_aluno]
            return pd.DataFrame()

        perfil = filtrar_aluno(df_perfil_total, email)
        gatilhos = filtrar_aluno(df_gatilhos_total, email)

        if perfil.empty and gatilhos.empty:
            st.warning(f"Nenhum registro encontrado para {email}")
            if st.button("Tentar outro E-mail"):
                del st.session_state.user_email
                st.rerun()
        else:
            st.success(f"Logado: {email}")
            
            if not gatilhos.empty:
                st.subheader("📊 Seu Histórico de Consumo")
                datas = pd.to_datetime(gatilhos.iloc[:, 0], errors='coerce').dt.date
                st.bar_chart(datas.value_counts().sort_index())

            col1, col2 = st.columns(2)
            with col1:
                st.info("📋 Perfil Identificado")
                st.write(perfil.tail(1).T)
            with col2:
                st.info("🔥 Últimos Gatilhos")
                st.dataframe(gatilhos.tail(5))

            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                contexto = f"Perfil: {perfil.tail(1).to_dict()} \nGatilhos: {gatilhos.tail(10).to_dict()}"
                
                prompt_mentor = f"""
                Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', especialista em Terapia Comportamental e Metodologia Clayton Chalegre/Alberto Dell'Isola.
                
                DADOS DO ALUNO:
                {contexto}

                SUA MISSÃO:
                1. PADRONIZAÇÃO: Ignore erros de digitação. Agrupe gatilhos por intenção (ex: relaxar).
                2. ANÁLISE: Identifique os principais 'Sinos de Pavlov' e explique o erro de previsão de dopamina.
                3. PLANO DE ANTECIPAÇÃO: Dê uma ordem prática e firme para o aluno 'desarmar o sino'.
                
                ESTILO: Direto, firme e transformador (Tom de voz de Clayton Chalegre).
                """
                
                with st.spinner("O Mentor está analisando..."):
                    response = model.generate_content(prompt_mentor)
                    st.markdown("---")
                    st.info(response.text)

# --- ÁREA ADMINISTRATIVA (COM TRAVA DE E-MAIL E SENHA) ---
elif pagina == "Área Administrativa":
    st.title("👑 Painel do Fundador")
    
    # Configurações de Acesso
    ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
    ADMIN_PASS = "Mc2284**lC"
    
    if "admin_logado" not in st.session_state:
        st.session_state.admin_logado = False

    if not st.session_state.admin_logado:
        st.subheader("🔒 Acesso Restrito ao Administrador")
        
        with st.form("login_admin"):
            email_adm = st.text_input("E-mail Administrativo:").strip().lower()
            senha_adm = st.text_input("Senha de Acesso:", type="password")
            botao_login = st.form_submit_button("Acessar Painel")
            
            if botao_login:
                if email_adm == ADMIN_EMAIL and senha_adm == ADMIN_PASS:
                    st.session_state.admin_logado = True
                    st.success("Acesso autorizado!")
                    st.rerun()
                else:
                    st.error("E-mail ou Senha incorretos.")
    else:
        st.sidebar.success("Sessão Administrativa Ativa")
        if st.sidebar.button("Encerrar Sessão ADM"):
            st.session_state.admin_logado = False
            st.rerun()

        st.success(f"Bem-vindo, Clayton! Gerenciando dados de {ADMIN_EMAIL}")

        if not df_gatilhos_total.empty:
            st.markdown("---")
            # MÉTRICAS GLOBAIS
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Gatilhos Mapeados", len(df_gatilhos_total))
            c3.metric("Status da IA", "Conectada")

            # GRÁFICOS GLOBAIS
            st.write("### Frequência de Consumo por Horário (Geral)")
            horas = pd.to_datetime(df_gatilhos_total.iloc[:, 0], errors='coerce').dt.hour.dropna()
            if not horas.empty:
                st.line_chart(horas.value_counts().sort_index())

            st.write("### Ranking de Gatilhos Mentais (Top 10)")
            col_gatilho = df_gatilhos_total.columns[3] 
            st.bar_chart(df_gatilhos_total[col_gatilho].value_counts().head(10))
            
            # INSIGHT GLOBAL DA TURMA
            if st.button("📊 GERAR INSIGHT GLOBAL DA TURMA"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                resumo_global = df_gatilhos_total[col_gatilho].value_counts().head(15).to_string()
                
                prompt_adm = f"""
                Você é um analista de dados estratégico do projeto Livre da Vontade. 
                Analise esses gatilhos mais frequentes da turma: {resumo_global}
                Sugira ao Clayton qual deve ser o próximo tema de aula ou live para atacar a dor principal do grupo.
                """
                
                with st.spinner("Analisando toda a turma..."):
                    response = model.generate_content(prompt_adm)
                    st.info(response.text)
            
            st.write("### Tabela de Dados Completa")
            st.dataframe(df_gatilhos_total)

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
import plotly.express as px

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
            
            # --- DASHBOARD VISUAL (LOOKER STYLE) ---
            if not gatilhos.empty:
                st.subheader("📊 Análise de Comportamento (Looker Style)")
                
                # Criando as colunas para os gráficos de rosca
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    # Gatilhos Principais (Coluna 3)
                    df_rosca1 = gatilhos.iloc[:, 3].value_counts().reset_index()
                    df_rosca1.columns = ['Gatilho', 'Qtd']
                    fig1 = px.pie(df_rosca1, names='Gatilho', values='Qtd', hole=0.6, title="Principais Gatilhos")
                    st.plotly_chart(fig1, use_container_width=True)
                
                with c2:
                    # Estado Emocional (Coluna 7 - Ajuste se necessário)
                    try:
                        df_rosca2 = gatilhos.iloc[:, 7].value_counts().reset_index()
                        df_rosca2.columns = ['Emoção', 'Qtd']
                        fig2 = px.pie(df_rosca2, names='Emoção', values='Qtd', hole=0.6, title="Clima Emocional")
                        st.plotly_chart(fig2, use_container_width=True)
                    except: st.write("Coluna de emoção não detectada.")

                with c3:
                    # Ambiente/Local (Ajuste o índice da coluna conforme sua planilha)
                    try:
                        df_rosca3 = gatilhos.iloc[:, 8].value_counts().reset_index()
                        df_rosca3.columns = ['Local', 'Qtd']
                        fig3 = px.pie(df_rosca3, names='Local', values='Qtd', hole=0.6, title="Ambiente Crítico")
                        st.plotly_chart(fig3, use_container_width=True)
                    except: st.write("Coluna de local não detectada.")

            col1, col2 = st.columns(2)
            with col1:
                st.info("📋 Perfil Identificado")
                st.write(perfil.tail(1).T)
            with col2:
                st.info("🔥 Últimos Gatilhos")
                st.dataframe(gatilhos.tail(5))

            # --- BOTÃO DO MENTOR (FOCO NO DIAGNÓSTICO COMPLETO) ---
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                # Enviamos o máximo de contexto possível para o diagnóstico profundo
                contexto_completo = f"""
                PERFIL DO ALUNO: {perfil.tail(1).to_dict()} 
                HISTÓRICO DE MAPEAMENTO: {gatilhos.tail(15).to_dict()}
                """
                
                prompt_mentor = f"""
                Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', especialista em Terapia Comportamental e Metodologia Clayton Chalegre/Alberto Dell'Isola.
                
                DADOS DO ALUNO:
                {contexto_completo}

                SUA MISSÃO:
                1. PADRONIZAÇÃO SEMÂNTICA: Agrupe variações como 'pra relaxar' e 'descansar' como a mesma intenção funcional.
                2. ANÁLISE PROFUNDA: Identifique os principais 'Sinos de Pavlov' (gatilhos) e explique tecnicamente o erro de previsão de dopamina.
                3. CONTEXTO EMOCIONAL: Relacione o perfil do aluno (história) com os gatilhos atuais.
                4. PLANO DE ANTECIPAÇÃO: Dê uma instrução prática, firme e clara para o aluno aplicar agora.
                
                ESTILO: Direto, firme, acolhedor e transformador (Tom de voz de Clayton Chalegre). Não economize na análise técnica.
                """
                
                with st.spinner("O Mentor está processando uma análise profunda..."):
                    response = model.generate_content(prompt_mentor)
                    st.markdown("---")
                    st.markdown("### 🌿 Resposta do Mentor")
                    st.info(response.text)

# --- ÁREA ADMINISTRATIVA ---
elif pagina == "Área Administrativa":
    st.title("👑 Painel do Fundador")
    
    ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
    ADMIN_PASS = "Mc2284**lC"
    
    if "admin_logado" not in st.session_state:
        st.session_state.admin_logado = False

    if not st.session_state.admin_logado:
        st.subheader("🔒 Acesso Restrito")
        with st.form("login_admin"):
            email_adm = st.text_input("E-mail Administrativo:").strip().lower()
            senha_adm = st.text_input("Senha de Acesso:", type="password")
            if st.form_submit_button("Acessar Painel"):
                if email_adm == ADMIN_EMAIL and senha_adm == ADMIN_PASS:
                    st.session_state.admin_logado = True
                    st.rerun()
                else:
                    st.error("Credenciais incorretas.")
    else:
        st.success(f"Bem-vindo, Clayton!")
        if st.button("Sair"):
            st.session_state.admin_logado = False
            st.rerun()

        if not df_gatilhos_total.empty:
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Mapeamentos", len(df_gatilhos_total))
            
            # Gráfico Global de Horários
            horas = pd.to_datetime(df_gatilhos_total.iloc[:, 0], errors='coerce').dt.hour.dropna()
            st.write("### Picos de Consumo (Horário Global)")
            st.line_chart(horas.value_counts().sort_index())

            # Gráfico Global de Gatilhos (Plotly)
            st.write("### Ranking Global de Gatilhos")
            df_global_gat = df_gatilhos_total.iloc[:, 3].value_counts().reset_index()
            fig_global = px.bar(df_global_gat, x=df_global_gat.columns[0], y='count', color='count')
            st.plotly_chart(fig_global, use_container_width=True)
            
            st.dataframe(df_gatilhos_total)

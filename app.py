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
            
            # --- DASHBOARD VISUAL ESTILO LOOKER STUDIO ---
            if not gatilhos.empty:
                st.subheader("📊 Sua Análise de Comportamento")
                
                # Tratamento de dados para os gráficos
                df_visual = gatilhos.copy()
                df_visual['Data/Hora'] = pd.to_datetime(df_visual.iloc[:, 0], errors='coerce')
                df_visual['Dia'] = df_visual['Data/Hora'].dt.strftime('%d/%m (%a)')
                
                # 1. Gráfico de Barras: Consumo Diário
                contagem_dia = df_visual['Dia'].value_counts().sort_index().reset_index()
                contagem_dia.columns = ['Dia', 'Quantidade']
                fig_dia = px.bar(contagem_dia, x='Dia', y='Quantidade', title="Cigarros por Dia", color_discrete_sequence=['#2E7D32'])
                st.plotly_chart(fig_dia, use_container_width=True)

                # 2. Gráficos de Rosca (Donut Charts) - Interatividade e Contexto
                col_a, col_b = st.columns(2)
                
                with col_a:
                    # Ranking de Gatilhos (Coluna 3 do Mapeamento)
                    st.write("**Principais Gatilhos Mentais**")
                    df_gat = df_visual.iloc[:, 3].value_counts().reset_index()
                    df_gat.columns = ['Gatilho', 'Total']
                    fig_gat = px.pie(df_gat, names='Gatilho', values='Total', hole=0.5, color_discrete_sequence=px.colors.sequential.Greens_r)
                    st.plotly_chart(fig_gat, use_container_width=True)

                with col_b:
                    # Sentimentos/Emoções (Ajuste o índice conforme sua coluna de emoção, ex: coluna 7)
                    st.write("**Estado Emocional no Consumo**")
                    try:
                        df_emo = df_visual.iloc[:, 7].value_counts().reset_index()
                        df_emo.columns = ['Emoção', 'Total']
                        fig_emo = px.pie(df_emo, names='Emoção', values='Total', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
                        st.plotly_chart(fig_emo, use_container_width=True)
                    except:
                        st.write("Dados de emoção ainda não mapeados.")

            col1, col2 = st.columns(2)
            with col1:
                st.info("📋 Perfil Identificado")
                st.write(perfil.tail(1).T)
            with col2:
                st.info("🔥 Dados Brutos (Últimos 5)")
                st.dataframe(gatilhos.tail(5))

            if st.button("🚀 GERAR DIAGNÓSTICO E COMENTÁRIOS DO MENTOR"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                # Resumo estatístico para a IA comentar os gráficos
                resumo_estatistico = gatilhos.iloc[:, 3].value_counts().to_string()
                contexto = f"Perfil: {perfil.tail(1).to_dict()} \nGatilhos (Resumo): {resumo_estatistico} \nÚltimos registros: {gatilhos.tail(5).to_dict()}"
                
                prompt_mentor = f"""
                Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', criado por Clayton Chalegre.
                
                DADOS PARA ANÁLISE:
                {contexto}

                SUA MISSÃO:
                1. COMENTÁRIO INTELIGENTE: Analise os números. Se o gatilho 'Café' aparece em 70% das vezes, comente isso especificamente. 
                2. PADRONIZAÇÃO SEMÂNTICA: Interprete variações como 'pra relaxar' e 'descansar' como a mesma intenção.
                3. CIÊNCIA: Explique o erro de previsão de dopamina associado ao comportamento mais frequente.
                4. ANTECIPAÇÃO: Dê um comando firme para quebrar o padrão amanhã.
                
                ESTILO: Direto, firme e transformador (Tom de voz de Clayton Chalegre).
                """
                
                with st.spinner("O Mentor está analisando os gráficos e seu perfil..."):
                    response = model.generate_content(prompt_mentor)
                    st.markdown("---")
                    st.markdown("### 🌿 Diagnóstico Personalizado")
                    st.info(response.text)

# --- ÁREA ADMINISTRATIVA ---
elif pagina == "Área Administrativa":
    st.title("👑 Painel do Fundador")
    
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
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Gatilhos Mapeados", len(df_gatilhos_total))
            c3.metric("Status da IA", "Conectada")

            # Gráfico de Horários Global
            st.write("### Frequência de Consumo por Horário (Global)")
            horas = pd.to_datetime(df_gatilhos_total.iloc[:, 0], errors='coerce').dt.hour.dropna().reset_index()
            horas.columns = ['ID', 'Hora']
            fig_horas = px.line(horas['Hora'].value_counts().sort_index(), title="Picos de Consumo na Turma")
            st.plotly_chart(fig_horas, use_container_width=True)

            # Ranking Global de Gatilhos
            st.write("### Top 10 Gatilhos da Turma")
            col_gatilho = df_gatilhos_total.columns[3] 
            df_global_gat = df_gatilhos_total[col_gatilho].value_counts().head(10).reset_index()
            fig_global_gat = px.bar(df_global_gat, x=col_gatilho, y='count', color='count', color_continuous_scale='Greens')
            st.plotly_chart(fig_global_gat, use_container_width=True)
            
            if st.button("📊 GERAR INSIGHT GLOBAL DA TURMA"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                resumo_global = df_gatilhos_total[col_gatilho].value_counts().head(15).to_string()
                prompt_adm = f"Analise esses gatilhos mais frequentes da turma e sugira ao Clayton qual deve ser o próximo tema de aula: {resumo_global}"
                with st.spinner("Analisando..."):
                    response = model.generate_content(prompt_adm)
                    st.info(response.text)
            
            st.write("### Tabela de Dados Completa")
            st.dataframe(df_gatilhos_total)

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
        ws_perfil = sh.worksheet("ENTREVISTA INICIAL")
        ws_gatilhos = sh.worksheet("MAPEAMENTO")
        df_p = pd.DataFrame(ws_perfil.get_all_records())
        df_g = pd.DataFrame(ws_gatilhos.get_all_records())
        return df_p, df_g
    return pd.DataFrame(), pd.DataFrame()

# --- 2. LOGICA DE NAVEGAÇÃO ---
st.sidebar.title("🌿 Menu de Navegação")
pagina = st.sidebar.radio("Ir para:", ["Área do Aluno", "Área Administrativa"])

df_perfil_total, df_gatilhos_total = carregar_todos_os_dados()

# --- ÁREA DO ALUNO ---
if pagina == "Área do Aluno":
    st.title("🌿 Meu Mapeamento - Mentor IA")
    
    if "user_email" not in st.session_state:
        email_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
        if st.button("Acessar Meus Dados"):
            st.session_state.user_email = email_input
            st.rerun()
    else:
        email = st.session_state.user_email
        
        # FILTRO ROBUSTO POR EMAIL
        def filtrar(df, email):
            col = next((c for c in df.columns if "email" in c.lower()), None)
            return df[df[col].astype(str).str.lower() == email] if col else pd.DataFrame()

        perfil = filtrar(df_perfil_total, email)
        gatilhos = filtrar(df_gatilhos_total, email)

        if perfil.empty and gatilhos.empty:
            st.warning(f"Nenhum registro encontrado para {email}")
            if st.button("Trocar E-mail"):
                del st.session_state.user_email
                st.rerun()
        else:
            st.success(f"Logado como: {email}")
            
            # DASHBOARD GRÁFICO DO ALUNO
            if not gatilhos.empty:
                st.subheader("📊 Seu Progresso na Semana")
                # Gráfico de cigarros por dia (Simulado pelo número de entradas por data)
                gatilhos['Data'] = pd.to_datetime(gatilhos.iloc[:, 0]).dt.date
                contagem_dia = gatilhos['Data'].value_counts().sort_index()
                st.bar_chart(contagem_dia)

            col1, col2 = st.columns(2)
            with col1:
                st.info("📋 Perfil Identificado")
                st.write(perfil.tail(1).T)
            with col2:
                st.info("🔥 Últimos Gatilhos")
                st.dataframe(gatilhos.tail(5))

            # BOTÃO DO MENTOR (IA)
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                genai.configure(api_key=st.secrets["gemini"]["api_key"])
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                contexto = f"Perfil: {perfil.tail(1).to_dict()} \n Gatilhos: {gatilhos.tail(10).to_dict()}"
                prompt = f"Analise semanticamente os gatilhos deste aluno e dê uma instrução prática de antecipação: {contexto}"
                
                with st.spinner("Analisando..."):
                    response = model.generate_content(prompt)
                    st.markdown("---")
                    st.info(response.text)

# --- ÁREA ADMINISTRATIVA ---
elif pagina == "Área Administrativa":
    st.title("👑 Painel do Fundador - Clayton Chalegre")
    
    if not df_gatilhos_total.empty:
        st.subheader("📈 Visão Geral do Projeto (Todos os Alunos)")
        
        # MÉTRICAS GLOBAIS
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique())
        c2.metric("Total de Gatilhos Mapeados", len(df_gatilhos_total))
        c3.metric("Média de Cigarros/Dia", "Em análise")

        # GRÁFICOS GLOBAIS
        st.write("### Frequência de Consumo por Horário")
        # Extrair hora do carimbo de data/hora (coluna 0)
        df_gatilhos_total['Hora'] = pd.to_datetime(df_gatilhos_total.iloc[:, 0]).dt.hour
        st.line_chart(df_gatilhos_total['Hora'].value_counts().sort_index())

        st.write("### Ranking de Gatilhos Mentais")
        # Supõe que a coluna de gatilhos tenha um nome padrão ou seja a coluna 3
        col_gatilho = df_gatilhos_total.columns[3] 
        st.bar_chart(df_gatilhos_total[col_gatilho].value_counts().head(10))

        st.dataframe(df_gatilhos_total)
    else:
        st.error("Não foi possível carregar os dados globais.")

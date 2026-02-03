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
            
            # --- SEÇÃO DE PERFIL E GATILHOS EM DESTAQUE ---
            st.markdown("---")
            col_perfil, col_gatilhos_alerta = st.columns([1, 1.2])
            
            with col_perfil:
                st.subheader("📋 Identidade do Aluno")
                if not perfil.empty:
                    dados = perfil.tail(1).to_dict('records')[0]
                    nome = next((v for k, v in dados.items() if "NOME" in k.upper()), "Usuário")
                    idade = next((v for k, v in dados.items() if "ANOS" in k.upper()), "Não informada")
                    cidade = next((v for k, v in dados.items() if "CIDADE" in k.upper()), "Não informada")
                    
                    st.info(f"""
                    **NOME:** {nome}  
                    **IDADE:** {idade} anos  
                    **LOCAL:** {cidade}  
                    *Pronto para a próxima etapa da liberdade.*
                    """)
                else:
                    st.write("Dados de perfil em processamento...")

            with col_gatilhos_alerta:
                st.subheader("⚠️ Alerta de Gatilhos Frequentes")
                if not gatilhos.empty:
                    # Ranking dos 3 maiores gatilhos (Coluna 3)
                    top_gatilhos = gatilhos.iloc[:, 3].value_counts().head(3)
                    
                    for i, (g, qtd) in enumerate(top_gatilhos.items()):
                        # Cores diferentes para criar hierarquia visual
                        cores = ["#FF4B4B", "#FF8B3D", "#FFC107"]
                        st.markdown(f"""
                        <div style="background-color:{cores[i]}; padding:15px; border-radius:10px; margin-bottom:10px; color:white; font-weight:bold;">
                            {i+1}º GATILHO: {g.upper()} <br>
                            <span style="font-size: 0.9em; font-weight:normal;">Detectado {qtd} vezes no seu mapeamento.</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.write("Aguardando os primeiros registros de mapeamento.")

            # --- BOTÃO DO MENTOR (FOCO NO DIAGNÓSTICO PROFUNDO) ---
            st.markdown("###")
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    # Otimização: Pegamos dados fundamentais para evitar erro de cota
                    historico_leve = gatilhos.iloc[:, [3, 7]].tail(10).to_dict('records')
                    contexto_completo = f"PERFIL: {perfil.tail(1).to_dict('records')} \nGATILHOS: {historico_leve}"
                    
                    prompt_blindado = f"""
                    Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', especialista em Terapia Comportamental e Metodologia Clayton Chalegre/Alberto Dell'Isola.
                    
                    DADOS DO ALUNO:
                    {contexto_completo}

                    SUA MISSÃO (PADRÃO BLINDADO):
                    1. Analise os gatilhos e o perfil histórico do aluno.
                    2. Explique tecnicamente o 'Sino de Pavlov' e o erro de previsão de dopamina.
                    3. Relacione a emoção predominante com o ato de fumar.
                    4. Entregue um plano de antecipação prático e firme.
                    
                    ESTILO: Direto, firme, técnico e transformador (Voz de Clayton Chalegre).
                    """
                    
                    with st.spinner("O Mentor está processando sua análise profunda..."):
                        response = model.generate_content(prompt_blindado)
                        st.markdown("---")
                        st.markdown("### 🌿 Resposta do Mentor")
                        st.info(response.text)
                
                except Exception as e:
                    if "ResourceExhausted" in str(e):
                        st.error("🌿 O Mentor está atendendo muitos alunos. Aguarde 60 segundos e tente novamente.")
                    else:
                        st.error(f"Erro no diagnóstico: {e}")

# --- ÁREA ADMINISTRATIVA ---
elif pagina == "Área Administrativa":
    st.title("👑 Painel do Fundador")
    ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
    ADMIN_PASS = "Mc2284**lC"
    
    if "admin_logado" not in st.session_state:
        st.session_state.admin_logado = False

    if not st.session_state.admin_logado:
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
        st.success("Bem-vindo, Clayton!")
        if st.button("Sair"):
            st.session_state.admin_logado = False
            st.rerun()

        if not df_gatilhos_total.empty:
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Mapeamentos Totais", len(df_gatilhos_total))
            
            st.write("### Tabela Geral de Mapeamento")
            st.dataframe(df_gatilhos_total)

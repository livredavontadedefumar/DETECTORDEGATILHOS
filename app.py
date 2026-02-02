import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests

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
            col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
            if col_email:
                return df[df[col_email].str.strip().str.lower() == email.lower()]
            return pd.DataFrame()

        perfil_aluno = filtrar_por_email(df_perfil_total, email_usuario)
        gatilhos_aluno = filtrar_por_email(df_gatilhos_total, email_usuario)

        return perfil_aluno, gatilhos_aluno

    except Exception as e:
        st.error(f"Erro ao acessar as abas: {e}")
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
                # Pega as últimas respostas do perfil
                st.write(perfil.tail(1).T) 
        with col2:
            if not gatilhos.empty:
                st.info("✅ Gatilhos Recentes Mapeados")
                st.dataframe(gatilhos.tail(5))

        # --- 3. LÓGICA DA IA ---
        if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
            try:
                api_key = st.secrets["gemini"]["api_key"]
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                
                # Montagem do Prompt com dados cruzados das duas abas
                contexto_perfil = perfil.to_string() if not perfil.empty else "Não informado"
                contexto_gatilhos = gatilhos.tail(5).to_string() if not gatilhos.empty else "Sem gatilhos recentes"
                
                prompt_mentor = f"""
                Você é o Mentor IA do projeto Livre da Vontade de Fumar, criado por Clayton Chalegre.
                Use a ciência do condicionamento (Pavlov) e erro de previsão de recompensa (Skinner).

                PERFIL PSICOLÓGICO DO ALUNO (ENTREVISTA INICIAL):
                {contexto_perfil}

                GATILHOS RECENTES (MAPEAMENTO DIÁRIO):
                {contexto_gatilhos}

                SUA MISSÃO:
                1. Analise como o perfil psicológico (ex: busca por companhia ou alívio de ansiedade) se reflete nos gatilhos recentes.
                2. Explique que o 'craving' (vontade) é apenas um disparo de dopamina baseado num erro de previsão.
                3. Dê uma instrução prática e firme para o aluno aplicar AGORA.
                4. Use o tom de voz do Clayton: Transformador, firme, sem julgamentos e focado em resultado.
                """

                payload = {"contents": [{"parts": [{"text": prompt_mentor}]}]}
                
                with st.spinner('O Mentor está analisando seu perfil e seus gatilhos...'):
                    response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=30)
                    if response.status_code == 200:
                        resultado = response.json()
                        texto_ia = resultado['candidates'][0]['content']['parts'][0]['text']
                        st.markdown("---")
                        st.markdown("### 🌿 Resposta Personalizada do Mentor")
                        st.info(texto_ia)
                    else:
                        st.error("Falha na API do Gemini.")

            except Exception as e:
                st.error(f"Erro ao gerar diagnóstico: {e}")

    if st.sidebar.button("Trocar Usuário"):
        st.session_state.logado = False
        st.rerun()

import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# Força o uso da API v1 para usar seu bônus de R$ 1.904,08 (Foto 1a5c)
os.environ["GOOGLE_API_VERSION"] = "v1"

st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

# Configuração da IA vinda dos Secrets
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

def carregar_dados():
    try:
        # Link do Secret (Foto a93b)
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # Usamos engine='python' para evitar o Erro 400 em servidores do Streamlit
        df = pd.read_csv(url, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = carregar_dados()
    if not df.empty:
        # Busca o aluno (Ajustado para ser mais flexível na busca)
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        
        if not user_data.empty:
            st.success(f"Registros localizados para {st.session_state.user_email}!")
            # Mostra a tabela que você sentiu falta
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seu Raio-X...'):
                        contexto = user_data.tail(15).to_string()
                        
                        # --- O PROMPT MESTRE QUE FALTAVA ---
                        prompt_mestre = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Analise os gatilhos abaixo e forneça um diagnóstico de Nível 1.

                        DADOS DO ALUNO:
                        {contexto}

                        ESTRUTURA DO SEU DIAGNÓSTICO:
                        1. PADRÃO IDENTIFICADO: Qual o maior erro emocional deste aluno?
                        2. QUEBRA DE CICLO: Uma instrução prática para o próximo gatilho.
                        3. MENSAGEM DO MENTOR: Uma frase curta de encorajamento firme.
                        """
                        
                        response = model.generate_content(prompt_mestre)
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.info(response.text)
                except Exception as e:
                    st.error(f"IA indisponível. Verifique o faturamento: {e}")
        else:
            st.error("E-mail não encontrado. Verifique sua planilha.")

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

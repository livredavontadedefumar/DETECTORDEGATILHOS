import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# Forçamos a versão v1 para garantir o bônus Nível 1 (Foto 1a5c)
os.environ["GOOGLE_API_VERSION"] = "v1"

st.set_page_config(page_title="Mentor IA - Raio-X 2.0", page_icon="🌿")

# Configuração da IA vinda dos Secrets
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

def carregar_dados():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # O engine python com on_bad_lines evita o erro 400 em muitos casos
        df = pd.read_csv(url, on_bad_lines='skip', engine='python')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")
st.write("---")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    e_input = st.text_input("Digite seu e-mail cadastrado:").strip().lower()
    if st.button("Acessar Mapeamento"):
        if e_input:
            st.session_state.user_email = e_input
            st.session_state.logged_in = True
            st.rerun()
else:
    df = carregar_dados()
    if not df.empty:
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        
        if not user_data.empty:
            st.success(f"Olá! Localizamos seus registros.")
            
            if st.button("🚀 GERAR MEU RAIO-X DA LIBERDADE"):
                try:
                    # Usando o modelo 1.5 Flash do seu plano pago (Foto 1a5c)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    with st.spinner('O Mentor está analisando seus padrões...'):
                        contexto = user_data.tail(15).to_string()
                        
                        # PROMPT MESTRE CONFIGURADO
                        prompt = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Sua missão é analisar os gatilhos de fumo deste aluno e fornecer um diagnóstico transformador.

                        DADOS RECENTES DO ALUNO:
                        {contexto}

                        ESTRUTURA DA RESPOSTA:
                        1. RESUMO DOS GATILHOS: Identifique os 3 momentos de maior risco.
                        2. PADRÃO EMOCIONAL: O que está por trás do desejo (ansiedade, tédio, hábito)?
                        3. PLANO DE AÇÃO: Dê uma instrução prática do Método Livre da Vontade para o próximo gatilho.
                        
                        Mantenha um tom profissional, acolhedor e focado na liberdade.
                        """
                        
                        response = model.generate_content(prompt)
                        st.markdown("### 💡 Diagnóstico do Mentor:")
                        st.info(response.text)
                except Exception as e:
                    st.error(f"Falha na análise da IA: {e}")
        else:
            st.error("E-mail não encontrado na planilha de mapeamento.")
            if st.button("Voltar"):
                st.session_state.logged_in = False
                st.rerun()

if st.sidebar.button("Sair"):
    st.session_state.logged_in = False
    st.rerun()

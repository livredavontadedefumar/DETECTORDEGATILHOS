import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# Forçamos a versão v1 para garantir o uso do faturamento Nível 1 (Foto 1a5c)
os.environ["GOOGLE_API_VERSION"] = "v1"

st.set_page_config(page_title="Raio-X 2.0", page_icon="🌿")

# Configuração da API Key vinda dos Secrets
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

def carregar_dados():
    try:
        # Puxa o link do formato export?format=csv (Foto 566f)
        url_csv = st.secrets["connections"]["gsheets"]["spreadsheet"]
        
        # Ajuste de segurança: definimos o engine e ignoramos linhas com erro de formato
        df = pd.read_csv(url_csv, on_bad_lines='skip', engine='python')
        
        # Limpamos espaços vazios nos nomes das colunas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro na conexão com os dados: {e}")
        return pd.DataFrame()

st.title("🌿 Diagnóstico Raio-X 2.0")

# Sistema de Login simples
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
            st.warning("Por favor, digite seu e-mail.")
else:
    df = carregar_dados()
    if not df.empty:
        # Busca o aluno na planilha (Busca parcial para evitar erros de digitação)
        user_data = df[df.apply(lambda row: st.session_state.user_email in str(row.values).lower(), axis=1)]
        
        if not user_data.empty:
            st.success(f"Dados localizados para: {st.session_state.user_email}")
            
            # Mostra os últimos registros para o aluno confirmar
            st.write("Seus últimos registros encontrados:")
            st.dataframe(user_data.tail(5))
            
            if st.button("Gerar Análise com IA"):
                try:
                    # Modelo Gemini 1.5 Flash (Rápido e eficiente)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner('O Mentor está analisando seus gatilhos...'):
                        # Enviamos os últimos 15 registros como contexto
                        contexto = user_data.tail(15).to_string()
                        prompt = f"Como mentor do Método Livre da Vontade, analise estes gatilhos e dê uma orientação prática: \n\n{contexto}"
                        
                        response = model.generate_content(prompt)
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.write(response.text)
                except Exception as e:
                    st.error(f"Erro ao processar análise. Verifique se o saldo está ativo. Detalhes: {e}")
        else:
            st.error("E-mail não encontrado na base de dados.")
            if st.button("Tentar outro e-mail"):
                st.session_state.logged_in = False
                st.rerun()
    
    # Botão de Sair na barra lateral
    if st.sidebar.button("Sair / Trocar Conta"):
        st.session_state.logged_in = False
        st.rerun()

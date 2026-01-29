import streamlit as st
import google.generativeai as genai
import pandas as pd
import os

# Ativa o uso da API v1 para garantir o uso do bônus de faturamento Nível 1
os.environ["GOOGLE_API_VERSION"] = "v1"

st.set_page_config(page_title="Mentor IA - Método Livre da Vontade", page_icon="🌿")

# Configuração da IA vinda dos Secrets
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])

def carregar_dados():
    try:
        # Puxa a URL configurada nos Secrets
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        
        # AJUSTE ANT-ERRO 400: Adicionamos engine e storage_options para conexões seguras
        df = pd.read_csv(url, on_bad_lines='skip', engine='python', encoding='utf-8')
        
        # Limpa nomes de colunas e dados para evitar erros de busca
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        # Mostra o erro técnico apenas se necessário para diagnóstico
        st.error(f"Erro de conexão com a base de dados: {e}")
        return pd.DataFrame()

st.title("🌿 Mentor IA - Método Livre da Vontade")

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
        # BUSCA MELHORADA: Procura o e-mail em todas as células, limpando espaços
        email_busca = st.session_state.user_email
        mask = df.apply(lambda row: row.astype(str).str.contains(email_busca, case=False, na=False).any(), axis=1)
        user_data = df[mask]
        
        if not user_data.empty:
            st.success(f"Olá! Registros localizados com sucesso.")
            
            # Exibe os últimos 10 registros para o usuário conferir
            st.subheader("Seu Histórico Recente:")
            st.dataframe(user_data.tail(10))
            
            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    # Inicializa o modelo configurado no seu plano Pro
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    with st.spinner('O Mentor está analisando seus padrões agora...'):
                        # Prepara o contexto com os dados reais da planilha
                        contexto_texto = user_data.tail(15).to_string()
                        
                        # --- PROMPT MESTRE DEFINITIVO ---
                        prompt_mestre = f"""
                        Você é o Mentor Especialista do Método Livre da Vontade. 
                        Sua missão é dar um Raio-X preciso para um aluno que deseja a liberdade do fumo.

                        DADOS DO ALUNO EXTRAÍDOS DA PLANILHA:
                        {contexto_texto}

                        ESTRUTURA OBRIGATÓRIA DA RESPOSTA:
                        1. PADRÃO IDENTIFICADO: Analise as emoções relatadas e identifique o gatilho mestre (ex: fuga, ansiedade, tédio).
                        2. QUEBRA DE CICLO: Dê uma instrução prática e imediata baseada no Método Livre da Vontade.
                        3. PALAVRA DO MENTOR: Uma frase curta de impacto para fortalecer a decisão do aluno.
                        
                        Mantenha o tom de autoridade, porém acolhedor.
                        """
                        
                        response = model.generate_content(prompt_mestre)
                        st.markdown("---")
                        st.subheader("💡 Orientação do Mentor:")
                        st.info(response.text)
                        
                except Exception as e:
                    st.error(f"Ocorreu um erro ao gerar a análise. Verifique sua cota de IA: {e}")
        else:
            st.error(f"O e-mail '{st.session_state.user_email}' não foi encontrado na base de dados.")
            if st.button("Tentar outro e-mail"):
                st.session_state.logged_in = False
                st.rerun()

# Menu lateral para navegação
with st.sidebar:
    st.write(f"Usuário: {st.session_state.get('user_email', 'Não logado')}")
    if st.button("Sair"):
        st.session_state.logged_in = False
        st.rerun()

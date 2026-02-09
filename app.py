import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from fpdf import FPDF
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

df_perfil_total, df_gatilhos_total = carregar_todos_os_dados()

# --- FUNÇÃO DE PDF ---
def gerar_pdf_formatado(dados_perfil, top_gatilhos, texto_diagnostico):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 15, txt="Livre da Vontade de Fumar", ln=True, align="C")
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="IDENTIDADE DO ALUNO", ln=True, fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, txt=f"NOME: {dados_perfil.get('nome', 'N/A')}", ln=True)
    pdf.cell(0, 7, txt=f"IDADE: {dados_perfil.get('idade', 'N/A')} anos", ln=True)
    pdf.cell(0, 7, txt=f"LOCAL: {dados_perfil.get('local', 'N/A')}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt="ALERTA DE GATILHOS FREQUENTES", ln=True, fill=True)
    pdf.set_font("Arial", "B", 10)
    for i, (g, qtd) in enumerate(top_gatilhos.items()):
        pdf.cell(0, 7, txt=f"{i+1}o: {g.upper()} ({qtd}x)", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 10, txt="RESPOSTA DO MENTOR", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(0, 0, 0)
    texto_limpo = texto_diagnostico.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=texto_limpo)
    
    pdf.ln(15)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, txt="Metodologia Clayton Chalegre", ln=True, align="C")
    return pdf.output(dest="S").encode("latin-1")

def filtrar_aluno(df, email_aluno):
    if df.empty: return pd.DataFrame()
    col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
    if col_email:
        df[col_email] = df[col_email].astype(str).str.strip().str.lower()
        return df[df[col_email] == email_aluno]
    return pd.DataFrame()

# --- FUNÇÃO DE DASHBOARD VISUAL (SEM IA) ---
def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel de Autoconsciência")
    
    # Tenta gerar gráficos baseados nas colunas padrão (3=Gatilho, 7=Emoção)
    try:
        c1, c2 = st.columns(2)
        with c1:
            if df_aluno.shape[1] > 3:
                # Gráfico de Pizza: Gatilhos
                dados_gatilho = df_aluno.iloc[:, 3].value_counts().reset_index()
                dados_gatilho.columns = ['Gatilho', 'Qtd']
                fig1 = px.pie(dados_gatilho, names='Gatilho', values='Qtd', hole=0.5, 
                             title="Seus Maiores Gatilhos", color_discrete_sequence=px.colors.sequential.Greens_r)
                st.plotly_chart(fig1, use_container_width=True)
            
        with c2:
            if df_aluno.shape[1] > 7:
                # Gráfico de Barras: Emoções
                dados_emocao = df_aluno.iloc[:, 7].value_counts().reset_index()
                dados_emocao.columns = ['Emoção', 'Qtd']
                fig2 = px.bar(dados_emocao, x='Qtd', y='Emoção', orientation='h', 
                             title="Clima Emocional", color='Qtd', color_continuous_scale='Reds')
                st.plotly_chart(fig2, use_container_width=True)
            
    except Exception as e:
        st.info("Aguardando mais dados para gerar os gráficos visuais.")

# --- MENU LATERAL ---
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
        perfil = filtrar_aluno(df_perfil_total, email)
        gatilhos = filtrar_aluno(df_gatilhos_total, email)

        if perfil.empty and gatilhos.empty:
            st.warning(f"Nenhum registro encontrado para {email}")
            if st.button("Tentar outro E-mail"):
                del st.session_state.user_email
                st.rerun()
        else:
            st.success(f"Logado: {email}")
            
            # --- BLOCO DE PERFIL ---
            st.markdown("---")
            col_perfil, col_info = st.columns([1, 2])
            dados_aluno_pdf = {}
            top_gatilhos_pdf = pd.Series(dtype=int)

            with col_perfil:
                st.subheader("📋 Identidade")
                if not perfil.empty:
                    d = perfil.tail(1).to_dict('records')[0]
                    # Busca flexível por colunas de nome/idade
                    dados_aluno_pdf['nome'] = next((v for k, v in d.items() if "NOME" in k.upper()), "Usuário")
                    dados_aluno_pdf['idade'] = next((v for k, v in d.items() if "ANOS" in k.upper()), "N/A")
                    dados_aluno_pdf['local'] = next((v for k, v in d.items() if "CIDADE" in k.upper()), "N/A")
                    st.info(f"**NOME:** {dados_aluno_pdf['nome']}\n\n**IDADE:** {dados_aluno_pdf['idade']}\n\n**LOCAL:** {dados_aluno_pdf['local']}")

            with col_info:
                # Exibe Dashboard Visual (SEM GASTAR IA)
                if not gatilhos.empty:
                    exibir_dashboard_visual(gatilhos)
                    if gatilhos.shape[1] > 3:
                        top_gatilhos_pdf = gatilhos.iloc[:, 3].value_counts().head(3)
                else:
                    st.write("Comece seu mapeamento para ver os gráficos.")

            # --- BLOCO DO MENTOR IA (INTELIGÊNCIA) ---
            st.markdown("---")
            st.subheader("🧠 Inteligência Comportamental")
            st.write("Acione o Mentor IA para receber uma análise profunda baseada em Pavlov e Dopamina.")

            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    # Seleciona colunas principais para a IA (Gatilho e Emoção) para economizar tokens
                    col_indices = [3, 7] if gatilhos.shape[1] > 7 else [0]
                    historico_leve = gatilhos.iloc[:, col_indices].tail(15).to_dict('records')
                    
                    # --- PROMPT DE FERRO 2.0 ---
                    prompt_ferro = f"""
                    Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', porta-voz estrito da Metodologia Clayton Chalegre. 
                    Sua base é a Terapia Comportamental e o Descondicionamento de Pavlov.

                    DADOS DO ALUNO: PERFIL: {perfil.tail(1).to_dict('records')} GATILHOS: {historico_leve}

                    REGRAS DE OURO (PROIBIÇÕES ABSOLUTAS):
                    1. JAMAIS sugira Vape, cigarros eletrônicos ou substitutos.
                    2. JAMAIS elogie redução gradual. O objetivo é liberdade total.
                    3. Trate cada cigarro fumado como uma falha técnica de antecipação, nunca como uma vitória parcial.
                    4. JAMAIS sugira substituir o cigarro por comida ou doces.

                    DIRETRIZES TÉCNICAS:
                    1. Explique o Erro de Previsão de Dopamina.
                    2. Desmonte o "Sino de Pavlov" identificando o gatilho.
                    3. Dê uma ordem de antecipação prática.

                    ESTILO: Firme, técnico, transformador. Voz de Clayton Chalegre.
                    """
                    
                    with st.spinner("Analisando seus padrões comportamentais..."):
                        response = model.generate_content(prompt_ferro)
                        res_texto = response.text
                        
                        # Filtro de Segurança
                        proibidos = ["vape", "eletrônico", "moderado", "reduzir aos poucos", "comer doce"]
                        if any(t in res_texto.lower() for t in proibidos):
                            st.error("Inconsistência detectada. Tente novamente.")
                        else:
                            st.session_state.ultimo_diagnostico = res_texto
                            st.info(st.session_state.ultimo_diagnostico)
                except Exception as e: st.error(f"Erro: {e}")

            if "ultimo_diagnostico" in st.session_state:
                pdf_bytes = gerar_pdf_formatado(dados_aluno_pdf, top_gatilhos_pdf, st.session_state.ultimo_diagnostico)
                st.download_button(label="📥 Baixar Diagnóstico em PDF", data=pdf_bytes, file_name=f"Relatorio_{dados_aluno_pdf.get('nome','Aluno')}.pdf", mime="application/pdf")

# --- ÁREA ADMINISTRATIVA ---
elif pagina == "Área Administrativa":
    st.title("👑 Painel do Fundador")
    ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
    ADMIN_PASS = "Mc2284**lC"
    
    if "admin_logado" not in st.session_state: st.session_state.admin_logado = False
    if not st.session_state.admin_logado:
        with st.form("login_admin"):
            email_adm = st.text_input("E-mail Administrativo:").strip().lower()
            senha_adm = st.text_input("Senha de Acesso:", type="password")
            if st.form_submit_button("Acessar Painel"):
                if email_adm == ADMIN_EMAIL and senha_adm == ADMIN_PASS:
                    st.session_state.admin_logado = True
                    st.rerun()
                else: st.error("Acesso Negado.")
    else:
        st.success("Administrador Ativo")
        if st.button("Sair"):
            st.session_state.admin_logado = False
            st.rerun()

        # Dashboard Administrativo Visual
        st.markdown("---")
        st.subheader("📊 Visão Geral da Turma")
        if not df_gatilhos_total.empty:
            c1, c2 = st.columns(2)
            c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Mapeamentos Registrados", len(df_gatilhos_total))
            
            # Gráfico Geral da Turma
            if df_gatilhos_total.shape[1] > 3:
                dados_gerais = df_gatilhos_total.iloc[:, 3].value_counts().reset_index().head(10)
                dados_gerais.columns = ['Gatilho', 'Qtd']
                fig_geral = px.bar(dados_gerais, x='Gatilho', y='Qtd', title="Top 10 Gatilhos da Turma", color='Qtd')
                st.plotly_chart(fig_geral, use_container_width=True)

        st.subheader("🔍 Auditoria Individual")
        emails_lista = df_perfil_total.iloc[:, 1].unique().tolist() if not df_perfil_total.empty else []
        aluno_selecionado = st.selectbox("Selecione o aluno:", [""] + emails_lista)

        if aluno_selecionado:
            p_adm = filtrar_aluno(df_perfil_total, aluno_selecionado)
            g_adm = filtrar_aluno(df_gatilhos_total, aluno_selecionado)
            
            # Exibe o dashboard visual do aluno selecionado
            if not g_adm.empty:
                exibir_dashboard_visual(g_adm)
            
            if st.button("🚀 GERAR DIAGNÓSTICO ADM"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    indices = [3, 7] if g_adm.shape[1] > 7 else [0]
                    h_adm = g_adm.iloc[:, indices].tail(15).to_dict('records')
                    
                    prompt_adm = f"Analise como Mentor IA Clayton Chalegre: PERFIL {p_adm.tail(1).to_dict('records')} GATILHOS {h_adm}. Proibido sugerir vape/redução."
                    with st.spinner("Gerando auditoria..."):
                        resp = model.generate_content(prompt_adm)
                        st.session_state.diag_adm = resp.text
                        st.info(st.session_state.diag_adm)
                except Exception as e: st.error(f"Erro: {e}")
            
            if "diag_adm" in st.session_state:
                d_adm = p_adm.tail(1).to_dict('records')[0] if not p_adm.empty else {}
                dados_adm_pdf = {
                    'nome': next((v for k, v in d_adm.items() if "NOME" in k.upper()), "N/A"),
                    'idade': next((v for k, v in d_adm.items() if "ANOS" in k.upper()), "N/A"),
                    'local': next((v for k, v in d_adm.items() if "CIDADE" in k.upper()), "N/A")
                }
                top_g_adm = g_adm.iloc[:, 3].value_counts().head(3) if not g_adm.empty and g_adm.shape[1] > 3 else pd.Series()
                
                pdf_adm = gerar_pdf_formatado(dados_adm_pdf, top_g_adm, st.session_state.diag_adm)
                st.download_button("📥 Baixar PDF Administrativo", data=pdf_adm, file_name=f"Relatorio_ADM.pdf")

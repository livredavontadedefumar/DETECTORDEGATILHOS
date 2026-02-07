import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from fpdf import FPDF

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

# --- FUNÇÃO PARA GERAR PDF DINÂMICO ---
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
        pdf.cell(0, 7, txt=f"{i+1}º: {g.upper()} ({qtd}x)", ln=True)
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
    pdf.cell(0, 10, txt="Metodologia Clayton Chalegre - 'O estresse não vai parar, mas sua reação a ele pode mudar.'", ln=True, align="C")
    return pdf.output(dest="S").encode("latin-1")

def filtrar_aluno(df, email_aluno):
    if df.empty: return pd.DataFrame()
    col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
    if col_email:
        df[col_email] = df[col_email].astype(str).str.strip().str.lower()
        return df[df[col_email] == email_aluno]
    return pd.DataFrame()

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
            st.markdown("---")
            col_perfil, col_gatilhos_alerta = st.columns([1, 1.2])
            dados_aluno_pdf = {}
            top_gatilhos_pdf = pd.Series(dtype=int)

            with col_perfil:
                st.subheader("📋 Identidade do Aluno")
                if not perfil.empty:
                    dados = perfil.tail(1).to_dict('records')[0]
                    dados_aluno_pdf['nome'] = next((v for k, v in dados.items() if "NOME" in k.upper()), "Usuário")
                    dados_aluno_pdf['idade'] = next((v for k, v in dados.items() if "ANOS" in k.upper()), "Não informada")
                    dados_aluno_pdf['local'] = next((v for k, v in dados.items() if "CIDADE" in k.upper()), "Não informada")
                    st.info(f"**NOME:** {dados_aluno_pdf['nome']}\n\n**IDADE:** {dados_aluno_pdf['idade']} anos\n\n**LOCAL:** {dados_aluno_pdf['local']}")

            with col_gatilhos_alerta:
                st.subheader("⚠️ Alerta de Gatilhos Frequentes")
                if not gatilhos.empty:
                    top_gatilhos_pdf = gatilhos.iloc[:, 3].value_counts().head(3)
                    cores = ["#FF4B4B", "#FF8B3D", "#FFC107"]
                    for i, (g, qtd) in enumerate(top_gatilhos_pdf.items()):
                        st.markdown(f'<div style="background-color:{cores[i]}; padding:12px; border-radius:10px; margin-bottom:8px; color:white; font-weight:bold;">{i+1}º: {g.upper()} ({qtd}x)</div>', unsafe_allow_html=True)

            st.markdown("---")
            total_mapeamentos = len(gatilhos)
            
            # Trava visual temporária (será refinada depois)
            if total_mapeamentos < 7:
                st.warning(f"🚨 **Diagnóstico Bloqueado:** Você possui {total_mapeamentos} mapeamentos. São necessários pelo menos **7 registros**.")
                st.progress(min(total_mapeamentos / 7, 1.0))
            else:
                if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                    try:
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        
                        historico_leve = gatilhos.iloc[:, [3, 7]].tail(10).to_dict('records')
                        contexto = f"PERFIL: {perfil.tail(1).to_dict('records')} GATILHOS: {historico_leve}"

                        # --- PROMPT DE FERRO BLINDADO ---
                        prompt_ferro = f"""
                        Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', porta-voz da Metodologia Clayton Chalegre. 
                        Sua base é a Terapia Comportamental e o Descondicionamento de Pavlov.

                        DADOS DO ALUNO: {contexto}

                        REGRAS DE OURO (PROIBIÇÕES ABSOLUTAS):
                        1. JAMAIS sugira Vape, cigarros eletrônicos ou dispositivos de aquecimento.
                        2. JAMAIS sugira redução gradual ou "fumar moderadamente".
                        3. JAMAIS sugira substituir o cigarro por comida, doces ou outros vícios.
                        4. JAMAIS recomende medicamentos.
                        5. JAMAIS use linguagem de pena ou vitimização.

                        DIRETRIZES TÉCNICAS:
                        1. Explique o Erro de Previsão de Dopamina: O cérebro espera um prazer que o cigarro não entrega.
                        2. Identifique o "Sino de Pavlov": Aponte o gatilho automático.
                        3. Ordem de Antecipação: Dê instrução prática de ação ANTES do gatilho.

                        ESTILO: Direto, firme, técnico e transformador. Use a voz de Clayton Chalegre.
                        """

                        with st.spinner("O Mentor está processando sua análise profunda..."):
                            response = model.generate_content(prompt_ferro)
                            res_texto = response.text

                            # --- FILTRO DE SEGURANÇA (GUARDRAIL) ---
                            proibidos = ["vape", "eletrônico", "moderado", "reduzir aos poucos", "comer doce", "chiclete de nicotina"]
                            if any(termo in res_texto.lower() for termo in proibidos):
                                st.error("🌿 O Mentor detectou uma recomendação fora da metodologia e bloqueou a resposta. Por favor, tente gerar novamente.")
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
                else: st.error("Credenciais incorretas.")
    else:
        st.success("Bem-vindo, Clayton!")
        if st.button("Sair"):
            st.session_state.admin_logado = False
            st.rerun()

        st.markdown("---")
        st.subheader("🔍 Auditar Aluno Específico")
        emails_lista = df_perfil_total.iloc[:, 1].unique().tolist() if not df_perfil_total.empty else []
        aluno_selecionado = st.selectbox("Selecione o e-mail do aluno para analisar:", [""] + emails_lista)

        if aluno_selecionado:
            p_adm = filtrar_aluno(df_perfil_total, aluno_selecionado)
            g_adm = filtrar_aluno(df_gatilhos_total, aluno_selecionado)
            
            col_p_adm, col_g_adm = st.columns([1, 1.2])
            dados_adm_pdf = {}
            top_g_adm_pdf = pd.Series(dtype=int)

            with col_p_adm:
                if not p_adm.empty:
                    d = p_adm.tail(1).to_dict('records')[0]
                    dados_adm_pdf['nome'] = next((v for k, v in d.items() if "NOME" in k.upper()), "N/A")
                    dados_adm_pdf['idade'] = next((v for k, v in d.items() if "ANOS" in k.upper()), "N/A")
                    dados_adm_pdf['local'] = next((v for k, v in d.items() if "CIDADE" in k.upper()), "N/A")
                    st.info(f"**ALUNO:** {dados_adm_pdf['nome']}\n\n**IDADE:** {dados_adm_pdf['idade']}\n\n**LOCAL:** {dados_adm_pdf['local']}")

            with col_g_adm:
                if not g_adm.empty:
                    top_g_adm_pdf = g_adm.iloc[:, 3].value_counts().head(3)
                    for i, (g, q) in enumerate(top_g_adm_pdf.items()):
                        st.warning(f"{i+1}º Gatilho: {g.upper()} ({q}x)")

            if st.button("🚀 GERAR DIAGNÓSTICO ADMINISTRATIVO"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    h_adm = g_adm.iloc[:, [3, 7]].tail(10).to_dict('records')
                    # ADM também usa o Prompt de Ferro para manter o padrão
                    prompt_adm = f"""Analise como Mentor IA #SEJALIVRE: PERFIL {p_adm.tail(1).to_dict('records')} GATILHOS {h_adm}. 
                    REGRAS: Proibido sugerir Vape, moderação ou redução. Foco em Pavlov e Antecipação."""
                    with st.spinner("Gerando diagnóstico administrativo..."):
                        resp = model.generate_content(prompt_adm)
                        st.session_state.diag_adm = resp.text
                        st.info(st.session_state.diag_adm)
                except Exception as e: st.error(f"Erro: {e}")

            if "diag_adm" in st.session_state:
                pdf_adm = gerar_pdf_formatado(dados_adm_pdf, top_g_adm_pdf, st.session_state.diag_adm)
                st.download_button("📥 Baixar PDF Administrativo", data=pdf_adm, file_name=f"Relatorio_ADM_{dados_adm_pdf.get('nome')}.pdf")
        

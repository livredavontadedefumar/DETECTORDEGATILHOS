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
    pdf.cell(0, 10, txt="Metodologia Clayton Chalegre - 'O estresse nao vai parar, mas sua reacao a ele pode mudar.'", ln=True, align="C")
    return pdf.output(dest="S").encode("latin-1")

def filtrar_aluno(df, email_aluno):
    if df.empty: return pd.DataFrame()
    col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
    if col_email:
        df[col_email] = df[col_email].astype(str).str.strip().str.lower()
        return df[df[col_email] == email_aluno]
    return pd.DataFrame()

# --- CÉREBRO DE CATEGORIZAÇÃO (LÓGICA HIERÁRQUICA) ---
def categorizar_inteligente(texto):
    """
    Função hierárquica para agrupar gatilhos e contextos.
    A ordem dos 'if' define a prioridade da classificação.
    """
    t = str(texto).upper().strip()
    
    # 1. ROTINA DE CASA E MOVIMENTO (Prioridade Máxima)
    # Ex: "Cheguei do trabalho" -> Classifica como CASA/ROTINA, não TRABALHO.
    termos_retorno = ['CHEGUEI', 'CHEGANDO', 'SAI DO', 'VINDO', 'VOLTANDO', 'CASA', 'DESCANSO', 'SOFÁ', 'BANHO', 'DORMIR', 'ACORDAR', 'CAMA']
    if any(term in t for term in termos_retorno):
        return "ROTINA / CASA"

    # 2. GATILHOS FISIOLÓGICOS E SOCIAIS FORTES
    # Álcool e Festas
    termos_social = ['CERVEJA', 'BEBER', 'BAR', 'FESTA', 'AMIGOS', 'CHURRASCO', 'VINHO', 'HAPPY', 'BALADA']
    if any(term in t for term in termos_social):
        return "SOCIAL / ÁLCOOL"

    # Café (O clássico)
    termos_cafe = ['CAFE', 'CAFÉ', 'CAPUCCINO', 'PADARIA', 'DESJEJUM', 'MANHÃ', 'EXPRESSO']
    if any(term in t for term in termos_cafe):
        return "MOMENTO DO CAFÉ"

    # Refeições
    termos_comida = ['ALMOÇO', 'JANTAR', 'COMER', 'FOME', 'BARRIGA', 'REFEIÇÃO', 'LANCHE', 'RESTAURANTE', 'PIZZA']
    if any(term in t for term in termos_comida):
        return "PÓS-REFEIÇÃO"

    # 3. CONTEXTOS DE ESTRESSE EXTERNO
    # Trânsito
    termos_transito = ['CARRO', 'TRANSITO', 'TRÂNSITO', 'DIRIGINDO', 'UBER', 'ÔNIBUS', 'METRÔ', 'ENGARRAFAMENTO', 'SEMAFORO', 'MOTO']
    if any(term in t for term in termos_transito):
        return "TRÂNSITO"

    # Trabalho (Só cai aqui se não foi 'Cheguei do trabalho')
    termos_trabalho = ['CHEFE', 'REUNIÃO', 'PRAZO', 'CLIENTE', 'EMAIL', 'ESCRITÓRIO', 'TRABALHO', 'JOB', 'PROJETO', 'COMPUTADOR', 'LIGAÇÃO']
    if any(term in t for term in termos_trabalho):
        return "TRABALHO"

    # 4. ESTADOS EMOCIONAIS (Se não tiver contexto físico)
    termos_ansiedade = ['ANSIEDADE', 'NERVOSO', 'BRIGA', 'DISCUSSÃO', 'ESTRESSE', 'CHATEADO', 'TRISTE', 'RAIVA', 'CHORAR', 'PREOCUPADO']
    if any(term in t for term in termos_ansiedade):
        return "PICO DE ANSIEDADE"

    termos_tedio = ['TÉDIO', 'NADA', 'ESPERANDO', 'FILA', 'TV', 'NETFLIX', 'ASSISTINDO']
    if any(term in t for term in termos_tedio):
        return "TÉDIO / OCIOSIDADE"

    return "OUTROS"

# --- FUNÇÃO DE DASHBOARD VISUAL (COM INTELIGÊNCIA LÓGICA) ---
def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel de Autoconsciência")
    
    try:
        # Colunas (ajuste índices se necessário): 3=Gatilho, 7=Emoção, 8=Local
        if df_aluno.shape[1] > 3:
            # Aplica a inteligência na coluna de Gatilhos
            df_aluno['Categoria_Gatilho'] = df_aluno.iloc[:, 3].apply(categorizar_inteligente)
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                # Gráfico de GATILHOS AGRUPADOS
                dados_gatilho = df_aluno['Categoria_Gatilho'].value_counts().reset_index()
                dados_gatilho.columns = ['Gatilho', 'Qtd']
                
                fig1 = px.pie(dados_gatilho, names='Gatilho', values='Qtd', hole=0.6, 
                             title="Gatilhos (Agrupados)", 
                             color_discrete_sequence=px.colors.qualitative.Prism)
                fig1.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig1, use_container_width=True)
            
            with c2:
                # Gráfico de EMOÇÕES (Top 5)
                if df_aluno.shape[1] > 7:
                    # Normaliza texto das emoções
                    raw_emo = df_aluno.iloc[:, 7].astype(str).str.upper().str.strip()
                    top_emo = raw_emo.value_counts().head(5).reset_index()
                    top_emo.columns = ['Emoção', 'Qtd']
                    
                    fig2 = px.bar(top_emo, x='Qtd', y='Emoção', orientation='h', 
                                 title="Top 5 Emoções", 
                                 color='Qtd', color_continuous_scale='Reds')
                    fig2.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig2, use_container_width=True)

            with c3:
                # Gráfico de AMBIENTE CRÍTICO (Usando a Coluna 8 se existir)
                if df_aluno.shape[1] > 8: 
                    # Aplica limpeza básica no ambiente
                    raw_loc = df_aluno.iloc[:, 8].astype(str).str.upper().str.strip()
                    top_loc = raw_loc.value_counts().head(5).reset_index()
                    top_loc.columns = ['Local', 'Qtd']
                    
                    fig3 = px.pie(top_loc, names='Local', values='Qtd', hole=0.6,
                                 title="Onde Você Fuma Mais?",
                                 color_discrete_sequence=px.colors.sequential.Blues)
                    fig3.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
                    fig3.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("Local não mapeado.")
            
    except Exception as e:
        st.error(f"Erro ao gerar gráficos: {e}")

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
            col_perfil, col_info = st.columns([1, 2])
            dados_aluno_pdf = {}
            top_gatilhos_pdf = pd.Series(dtype=int)

            with col_perfil:
                st.subheader("📋 Identidade")
                if not perfil.empty:
                    d = perfil.tail(1).to_dict('records')[0]
                    dados_aluno_pdf['nome'] = next((v for k, v in d.items() if "NOME" in k.upper()), "Usuário")
                    dados_aluno_pdf['idade'] = next((v for k, v in d.items() if "ANOS" in k.upper()), "N/A")
                    dados_aluno_pdf['local'] = next((v for k, v in d.items() if "CIDADE" in k.upper()), "N/A")
                    st.info(f"**NOME:** {dados_aluno_pdf['nome']}\n\n**IDADE:** {dados_aluno_pdf['idade']}\n\n**LOCAL:** {dados_aluno_pdf['local']}")

            with col_info:
                if not gatilhos.empty:
                    # EXIBE O DASHBOARD INTELIGENTE
                    exibir_dashboard_visual(gatilhos)
                    if gatilhos.shape[1] > 3:
                        # Para o PDF, usamos os dados agrupados se possível, ou brutos
                        top_gatilhos_pdf = gatilhos.iloc[:, 3].value_counts().head(3)
                else:
                    st.write("Comece seu mapeamento para ver os gráficos.")

            st.markdown("---")
            st.subheader("🧠 Inteligência Comportamental")
            st.write("Acione o Mentor IA para receber uma análise profunda baseada em Pavlov e Dopamina.")

            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    
                    # Seleciona colunas para enviar para IA
                    col_indices = [3, 7] if gatilhos.shape[1] > 7 else [0]
                    historico_leve = gatilhos.iloc[:, col_indices].tail(15).to_dict('records')
                    
                    # PROMPT DE FERRO 2.0 (Mantido conforme solicitado)
                    prompt_ferro = f"""
                    Você é o Mentor IA do projeto 'Livre da Vontade de Fumar', porta-voz estrito da Metodologia Clayton Chalegre. 
                    Sua base é a Terapia Comportamental e o Descondicionamento de Pavlov.

                    DADOS DO ALUNO: PERFIL: {perfil.tail(1).to_dict('records')} GATILHOS: {historico_leve}

                    REGRAS DE OURO:
                    1. JAMAIS sugira Vape/eletrônicos.
                    2. JAMAIS elogie redução gradual. Foco em liberdade total.
                    3. Trate cada cigarro como falha técnica de antecipação.
                    4. JAMAIS sugira comida como substituto.

                    DIRETRIZES:
                    1. Explique o Erro de Previsão de Dopamina.
                    2. Desmonte o "Sino de Pavlov".
                    3. Dê ordem de antecipação.

                    ESTILO: Firme, técnico, transformador. Voz de Clayton Chalegre.
                    """
                    
                    with st.spinner("Analisando padrões..."):
                        response = model.generate_content(prompt_ferro)
                        res_texto = response.text
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

        st.markdown("---")
        st.subheader("📊 Visão Geral da Turma")
        if not df_gatilhos_total.empty:
            c1, c2 = st.columns(2)
            c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Mapeamentos Registrados", len(df_gatilhos_total))
            
            # Dashboard Geral Inteligente
            exibir_dashboard_visual(df_gatilhos_total)

        st.subheader("🔍 Auditoria Individual")
        emails_lista = df_perfil_total.iloc[:, 1].unique().tolist() if not df_perfil_total.empty else []
        aluno_selecionado = st.selectbox("Selecione o aluno:", [""] + emails_lista)

        if aluno_selecionado:
            p_adm = filtrar_aluno(df_perfil_total, aluno_selecionado)
            g_adm = filtrar_aluno(df_gatilhos_total, aluno_selecionado)
            
            if not g_adm.empty:
                exibir_dashboard_visual(g_adm)
            
            if st.button("🚀 GERAR DIAGNÓSTICO ADM"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    h_adm = g_adm.iloc[:, [3, 7]].tail(15).to_dict('records')
                    prompt_adm = f"Analise como Mentor IA Clayton Chalegre: PERFIL {p_adm.tail(1).to_dict('records')} GATILHOS {h_adm}. Proibido sugerir vape/redução."
                    with st.spinner("Gerando auditoria..."):
                        resp = model.generate_content(prompt_adm)
                        st.session_state.diag_adm = resp.text
                        st.info(st.session_state.diag_adm)
                except Exception as e: st.error(f"Erro: {e}")
            
            if "diag_adm" in st.session_state:
                d_adm = p_adm.tail(1).to_dict('records')[0] if not p_adm.empty else {}
                dados_adm_pdf = {'nome': 'Auditoria', 'idade': '-', 'local': '-'}
                top_g_adm = g_adm.iloc[:, 3].value_counts().head(3) if not g_adm.empty else pd.Series()
                pdf_adm = gerar_pdf_formatado(dados_adm_pdf, top_g_adm, st.session_state.diag_adm)
                st.download_button("📥 Baixar PDF Administrativo", data=pdf_adm, file_name=f"Relatorio_ADM.pdf")

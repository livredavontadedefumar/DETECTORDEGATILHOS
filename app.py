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

# --- INTELIGÊNCIA DE DADOS (HÍBRIDA / "LÓGICA DA VERDADE") ---

def categorizar_geral_hibrida(texto):
    """ 
    Usada para GATILHOS (Col D) e LOCAIS (Col C).
    Tenta categorizar. Se não conseguir, devolve o texto original.
    """
    t = str(texto).upper().strip()
    
    # 1. BIOLÓGICOS / GATILHOS FORTES
    if any(k in t for k in ['ACORDEI', 'ACORDANDO', 'LEVANTANDO', 'CAMA', 'JEJUM', 'MANHÃ']): return "PRIMEIRO DO DIA (ACORDAR)"
    if any(k in t for k in ['CAFE', 'CAFÉ', 'CAPUCCINO', 'PADARIA', 'DESJEJUM']): return "GATILHO DO CAFÉ"
    if any(k in t for k in ['ALMOÇO', 'JANTAR', 'COMER', 'FOME', 'REFEIÇÃO', 'LANCHE', 'PIZZA']): return "PÓS-REFEIÇÃO"
    if any(k in t for k in ['CERVEJA', 'BEBER', 'BAR', 'FESTA', 'VINHO', 'HAPPY']): return "BEBIDA/SOCIAL"

    # 2. LOCAIS ESPECÍFICOS
    if any(k in t for k in ['COZINHA', 'BALCÃO', 'BALCAO', 'GELADEIRA', 'PIA', 'FOGÃO']): return "COZINHA / BALCÃO"
    if any(k in t for k in ['VARANDA', 'SACADA', 'QUINTAL', 'JARDIM', 'GARAGEM', 'RUA']): return "ÁREA EXTERNA / VARANDA"
    if any(k in t for k in ['BANHEIRO', 'BANHO', 'PRIVADA']): return "BANHEIRO"
    if any(k in t for k in ['QUARTO', 'CABECEIRA', 'DORMITÓRIO']): return "QUARTO"
    if any(k in t for k in ['SALA', 'SOFÁ', 'TV']): return "SALA DE ESTAR"

    # 3. CONTEXTO
    if any(k in t for k in ['CARRO', 'TRANSITO', 'TRÂNSITO', 'DIRIGINDO', 'UBER', 'VOLANTE']): return "TRÂNSITO"
    if any(k in t for k in ['CHEFE', 'REUNIÃO', 'PRAZO', 'TRABALHO', 'ESCRITÓRIO', 'COMPUTADOR']): return "TRABALHO"
    if any(k in t for k in ['CELULAR', 'INSTAGRAM', 'TIKTOK', 'WHATSAPP', 'ZAP']): return "CELULAR/TELAS"
    if any(k in t for k in ['ANSIEDADE', 'NERVOSO', 'ESTRESSE', 'BRIGA', 'RAIVA']): return "PICO DE ANSIEDADE"
    if any(k in t for k in ['TÉDIO', 'NADA', 'ESPERANDO']): return "TÉDIO/OCIOSIDADE"
    
    if any(k in t for k in ['CHEGUEI', 'CHEGANDO', 'SAI DO', 'VINDO', 'CASA']): return "ROTINA DE CASA"

    # HÍBRIDO: Se não caiu em nada acima, retorna o texto original do usuário
    if len(t) > 1:
        return t
    return "NÃO INFORMADO"

def categorizar_motivos_hibrida(texto):
    """ 
    Para coluna E: Motivos de Enfrentamento
    Lógica Híbrida: Categoriza os comuns, mantém os inéditos.
    """
    t = str(texto).upper().strip()
    
    # Categorias Macro
    if any(k in t for k in ['VONTADE', 'DESEJO', 'FORTE', 'FISSURA', 'QUERIA']): return "VONTADE INCONTROLÁVEL"
    if any(k in t for k in ['HABITO', 'HÁBITO', 'AUTOMATICO', 'AUTOMÁTICO', 'NEM VI']): return "HÁBITO AUTOMÁTICO"
    if any(k in t for k in ['ANSIEDADE', 'NERVOSO', 'ESTRESSE', 'TENSO', 'BRIGA']): return "ALÍVIO DE ESTRESSE"
    if any(k in t for k in ['PRAZER', 'RELAXAR', 'GOSTO', 'BOM', 'PREMIO']): return "BUSCA POR PRAZER"
    if any(k in t for k in ['SOCIAL', 'AMIGOS', 'ACOMPANHAR', 'TURMA']): return "PRESSÃO SOCIAL"
    if any(k in t for k in ['TÉDIO', 'TEDIO', 'NADA', 'FAZER']): return "TÉDIO"
    
    # Retorna original se não achar
    if len(t) > 1:
        return t
    return "NÃO INFORMADO"

def categorizar_habitos_hibrida(texto):
    """ Para coluna H: Hábitos Associados (Já estava Híbrida) """
    t = str(texto).upper().strip()
    if any(k in t for k in ['CAFE', 'CAFÉ', 'CAPUCCINO']): return "TOMAR CAFÉ"
    if any(k in t for k in ['ALCOOL', 'ÁLCOOL', 'CERVEJA', 'BEBIDA', 'DRINK', 'VINHO']): return "BEBER ÁLCOOL"
    if any(k in t for k in ['CELULAR', 'REDES', 'INSTA', 'TIKTOK', 'ZAP']): return "MEXER NO CELULAR"
    if any(k in t for k in ['DIRIGIR', 'CARRO', 'VOLANTE', 'MOTO']): return "DIRIGIR"
    if any(k in t for k in ['TRABALHAR', 'PC', 'NOTEBOOK', 'EMAIL', 'COMPUTADOR']): return "TRABALHAR"
    if any(k in t for k in ['COMER', 'DOCE', 'SOBREMESA', 'ALMOÇO', 'JANTAR']): return "COMER/SOBREMESA"
    if any(k in t for k in ['CONVERSAR', 'PAPO', 'FALAR']): return "CONVERSAR"
    
    if len(t) > 1: return t
    return "NÃO INFORMADO"

# --- FUNÇÃO DE DASHBOARD VISUAL (VERTICAL) ---
def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel da Autoconsciência")
    st.markdown("---")
    
    try:
        # 1. CIGARROS POR DIA DA SEMANA (Mantido Intacto)
        if df_aluno.shape[1] > 0:
            st.markdown("##### 1. Cronologia do Vício (Dias da Semana)")
            df_temp = df_aluno.copy()
            df_temp['Data'] = pd.to_datetime(df_temp.iloc[:, 0], dayfirst=True, errors='coerce')
            df_temp['Dia_Semana'] = df_temp['Data'].dt.day_name()
            
            mapa_dias = {'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta', 'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
            df_temp['Dia_PT'] = df_temp['Dia_Semana'].map(mapa_dias)
            
            total_cigarros = len(df_temp)
            contagem_dias = df_temp['Dia_PT'].value_counts().reset_index()
            contagem_dias.columns = ['Dia', 'Qtd']
            
            ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            
            col_kpi, col_chart = st.columns([1, 3])
            col_kpi.metric("TOTAL DE CIGARROS", total_cigarros, delta="Mapeado até agora")
            
            fig1 = px.bar(contagem_dias, x='Dia', y='Qtd', category_orders={'Dia': ordem_dias},
                         color='Qtd', color_continuous_scale='Greens')
            col_chart.plotly_chart(fig1, use_container_width=True)
            st.markdown("---")

        # 2. PRINCIPAIS GATILHOS (Coluna D) - Agora Híbrido
        if df_aluno.shape[1] > 3:
            st.markdown("##### 2. Principais Gatilhos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 3].apply(categorizar_geral_hibrida)
            
            # Pega Top 10 para não poluir se tiver muita "verdade" diferente
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Gatilho', 'Qtd']
            
            fig2 = px.pie(dados, names='Gatilho', values='Qtd', hole=0.5, 
                         color_discrete_sequence=px.colors.sequential.Teal)
            fig2.update_layout(showlegend=True) 
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")

        # 3. HÁBITOS ASSOCIADOS (Coluna H) - Mantido Híbrido
        if df_aluno.shape[1] > 7:
            st.markdown("##### 3. Hábitos Associados")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 7].apply(categorizar_habitos_hibrida)
            
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Hábito', 'Qtd']
            
            fig3 = px.bar(dados, x='Qtd', y='Hábito', orientation='h',
                         color_discrete_sequence=['#2E8B57']) 
            fig3.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown("---")

        # 4. MOTIVOS DE ENFRENTAMENTO (Coluna E) - Agora Híbrido
        if df_aluno.shape[1] > 4:
            st.markdown("##### 4. Motivos de Enfrentamento")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 4].apply(categorizar_motivos_hibrida)
            
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Motivo', 'Qtd']
            
            fig4 = px.pie(dados, names='Motivo', values='Qtd', hole=0.5, 
                         color_discrete_sequence=px.colors.sequential.OrRd)
            fig4.update_layout(showlegend=True)
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown("---")

        # 5. CANTINHOS FAVORITOS (Coluna C) - Agora Híbrido
        if df_aluno.shape[1] > 2:
            st.markdown("##### 5. Cantinhos Favoritos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 2].apply(categorizar_geral_hibrida)
            
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Local', 'Qtd']
            
            fig5 = px.pie(dados, names='Local', values='Qtd', hole=0.5,
                         color_discrete_sequence=px.colors.sequential.Blues)
            fig5.update_layout(showlegend=True)
            fig5.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig5, use_container_width=True)
            st.markdown("---")
        
        # 6. EMOÇÕES PROPRÍCIAS (Coluna G) - Mantido TEXTO PURO (SEM AGRUPAMENTO INTELIGENTE)
        if df_aluno.shape[1] > 6:
            st.markdown("##### 6. Emoções Propícias ao Consumo")
            df_temp = df_aluno.copy()
            # Apenas Maiúsculo + Strip para padronizar visualmente
            df_temp['Cat'] = df_temp.iloc[:, 6].apply(lambda x: str(x).upper().strip())
            
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Emoção', 'Qtd']
            
            fig6 = px.bar(dados, x='Qtd', y='Emoção', orientation='h',
                         color='Qtd', color_continuous_scale='Reds')
            fig6.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig6, use_container_width=True)

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
            
            # --- INICIALIZAÇÃO DE VARIÁVEIS ---
            dados_aluno_pdf = {}
            top_gatilhos_pdf = pd.Series(dtype=int)

            # --- SEÇÃO IDENTIDADE COMPACTA ---
            if not perfil.empty:
                d = perfil.tail(1).to_dict('records')[0]
                dados_aluno_pdf['nome'] = next((v for k, v in d.items() if "NOME" in k.upper()), "Usuário")
                dados_aluno_pdf['idade'] = next((v for k, v in d.items() if "ANOS" in k.upper()), "N/A")
                dados_aluno_pdf['local'] = next((v for k, v in d.items() if "CIDADE" in k.upper()), "N/A")
                
                with st.container():
                    st.markdown(f"""
                    <div style="background-color: #f0fdf4; padding: 10px; border-radius: 5px; border: 1px solid #bbf7d0; margin-bottom: 20px;">
                        <span style="color: #166534; font-weight: bold;">👤 ALUNO:</span> {dados_aluno_pdf['nome']} | 
                        <span style="color: #166534; font-weight: bold;">🎂 IDADE:</span> {dados_aluno_pdf['idade']} | 
                        <span style="color: #166534; font-weight: bold;">📍 LOCAL:</span> {dados_aluno_pdf['local']}
                    </div>
                    """, unsafe_allow_html=True)
            
            # --- PAINEL DE CONSCIÊNCIA ---
            if not gatilhos.empty:
                exibir_dashboard_visual(gatilhos)
                if gatilhos.shape[1] > 3:
                    df_temp = gatilhos.copy()
                    df_temp['Cat'] = df_temp.iloc[:, 3].apply(categorizar_geral_hibrida)
                    top_gatilhos_pdf = df_temp['Cat'].value_counts().head(3)
            else:
                st.info("Comece seu mapeamento para liberar o Painel de Consciência.")

            # --- SEÇÃO 3: MENTOR IA ---
            st.markdown("---")
            st.subheader("🧠 Inteligência Comportamental")
            st.write("Acione o Mentor IA para receber uma análise profunda baseada em Pavlov e Dopamina.")

            if st.button("🚀 GERAR DIAGNÓSTICO DO MENTOR"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    col_indices = [3, 6] if gatilhos.shape[1] > 6 else [0]
                    historico_leve = gatilhos.iloc[:, col_indices].tail(15).to_dict('records')
                    
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
                    h_adm = g_adm.iloc[:, [3, 6]].tail(15).to_dict('records')
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
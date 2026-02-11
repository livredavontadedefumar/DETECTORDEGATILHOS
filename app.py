import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from fpdf import FPDF
import plotly.express as px
from datetime import datetime
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Madrinha-IA - MAPA COMPORTAMENTAL",
    page_icon="logo.png",
    layout="wide",
)

# --- CSS PARA REMOVER MENUS (VISUAL APP NATIVO) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CONSTANTES DE ACESSO ---
ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
ADMIN_PASS = "Mc2284**lC"

# LISTA DE MADRINHAS E SENHA PADRÃO
# A senha deve ser digitada exatamente assim (M maiúsculo)
MADRINHAS_EMAILS = [
    "luannyfaustino53@gmail.com",
    "costaebastos@yahoo.com"
]
MADRINHA_PASS = "Madrinha2026*"

# --- FUNÇÃO AUXILIAR PARA IMAGEM HTML ---
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except Exception:
        return None

# --- CONEXÃO GOOGLE SHEETS ---
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
            try:
                ws_log = sh.worksheet("LOG_DIAGNOSTICOS")
                df_l = pd.DataFrame(ws_log.get_all_records())
            except:
                df_l = pd.DataFrame(columns=["DATA", "QUEM_SOLICITOU", "ALUNO_ANALISADO"])
            
            df_p = pd.DataFrame(ws_perfil.get_all_records())
            df_g = pd.DataFrame(ws_gatilhos.get_all_records())
            return df_p, df_g, df_l
        except Exception as e:
            st.error(f"Erro ao ler abas: {e}")
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_perfil_total, df_gatilhos_total, df_log_total = carregar_todos_os_dados()

# --- FUNÇÕES ÚTEIS (LOG E PDF) ---
def registrar_uso_diagnostico(quem_solicitou, aluno_analisado):
    sh = conectar_planilha()
    if sh:
        try:
            ws_log = sh.worksheet("LOG_DIAGNOSTICOS")
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws_log.append_row([data_hora, quem_solicitou, aluno_analisado])
            return True
        except: return False
    return False

def verificar_limite_madrinha(email_madrinha, email_aluno, df_log):
    if df_log.empty: return True
    mask_madrinha = df_log.iloc[:, 1].astype(str).str.strip().str.lower() == email_madrinha
    mask_aluno = df_log.iloc[:, 2].astype(str).str.strip().str.lower() == email_aluno
    usos = df_log[mask_madrinha & mask_aluno].copy()
    if usos.empty: return True
    usos['Data_Obj'] = pd.to_datetime(usos.iloc[:, 0], errors='coerce')
    limite_data = datetime.now() - timedelta(days=7)
    usos_recentes = usos[usos['Data_Obj'] >= limite_data]
    if len(usos_recentes) >= 2:
        return False
    return True

def gerar_pdf_formatado(dados_perfil, top_gatilhos, texto_diagnostico):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", x=10, y=8, w=30)
        pdf.set_y(40)
    except: pass
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 15, txt="Livre da Vontade de Fumar", ln=True, align="C")
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="RELATÓRIO DE ANÁLISE", ln=True, fill=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, txt=f"NOME/TURMA: {dados_perfil.get('nome', 'Análise Geral')}", ln=True)
    if 'idade' in dados_perfil: pdf.cell(0, 7, txt=f"IDADE: {dados_perfil.get('idade', 'N/A')}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt="RESUMO DOS DADOS", ln=True, fill=True)
    pdf.set_font("Arial", "B", 10)
    for i, (g, qtd) in enumerate(top_gatilhos.items()):
        pdf.cell(0, 7, txt=f"{i+1}o: {g.upper()} ({qtd}x)", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 10, txt="DIAGNÓSTICO ESTRATÉGICO", ln=True)
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

# --- INTELIGÊNCIA DE DADOS ---
def categorizar_geral_hibrida(texto):
    t = str(texto).upper().strip()
    if any(k in t for k in ['ACORDEI', 'ACORDANDO', 'LEVANTANDO', 'CAMA', 'JEJUM', 'MANHÃ']): return "PRIMEIRO DO DIA (ACORDAR)"
    if any(k in t for k in ['CAFE', 'CAFÉ', 'CAPUCCINO', 'PADARIA', 'DESJEJUM']): return "GATILHO DO CAFÉ"
    if any(k in t for k in ['ALMOÇO', 'JANTAR', 'COMER', 'FOME', 'REFEIÇÃO', 'LANCHE', 'PIZZA']): return "PÓS-REFEIÇÃO"
    if any(k in t for k in ['CERVEJA', 'BEBER', 'BAR', 'FESTA', 'VINHO', 'HAPPY']): return "BEBIDA/SOCIAL"
    if any(k in t for k in ['COZINHA', 'BALCÃO', 'BALCAO', 'GELADEIRA', 'PIA', 'FOGÃO']): return "COZINHA / BALCÃO"
    if any(k in t for k in ['VARANDA', 'SACADA', 'QUINTAL', 'JARDIM', 'GARAGEM', 'RUA']): return "ÁREA EXTERNA / VARANDA"
    if any(k in t for k in ['BANHEIRO', 'BANHO', 'PRIVADA']): return "BANHEIRO"
    if any(k in t for k in ['QUARTO', 'CABECEIRA', 'DORMITÓRIO']): return "QUARTO"
    if any(k in t for k in ['SALA', 'SOFÁ', 'TV']): return "SALA DE ESTAR"
    if any(k in t for k in ['CARRO', 'TRANSITO', 'TRÂNSITO', 'DIRIGINDO', 'UBER', 'VOLANTE']): return "TRÂNSITO"
    if any(k in t for k in ['CHEFE', 'REUNIÃO', 'PRAZO', 'TRABALHO', 'ESCRITÓRIO', 'COMPUTADOR']): return "TRABALHO"
    if any(k in t for k in ['CELULAR', 'INSTAGRAM', 'TIKTOK', 'WHATSAPP', 'ZAP']): return "CELULAR/TELAS"
    if any(k in t for k in ['ANSIEDADE', 'NERVOSO', 'ESTRESSE', 'BRIGA', 'RAIVA']): return "PICO DE ANSIEDADE"
    if any(k in t for k in ['TÉDIO', 'NADA', 'ESPERANDO']): return "TÉDIO/OCIOSIDADE"
    if any(k in t for k in ['CHEGUEI', 'CHEGANDO', 'SAI DO', 'VINDO', 'CASA']): return "ROTINA DE CASA"
    if len(t) > 1: return t
    return "NÃO INFORMADO"

def categorizar_enfrentamento_hibrida(texto):
    t = str(texto).upper().strip()
    if any(k in t for k in ['VONTADE', 'DESEJO', 'FORTE', 'FISSURA', 'QUERIA']): return "VONTADE INCONTROLÁVEL"
    if any(k in t for k in ['HABITO', 'HÁBITO', 'AUTOMATICO', 'AUTOMÁTICO', 'NEM VI']): return "HÁBITO AUTOMÁTICO"
    if any(k in t for k in ['ANSIEDADE', 'NERVOSO', 'ESTRESSE', 'TENSO', 'BRIGA']): return "ALÍVIO DE ESTRESSE"
    if any(k in t for k in ['PRAZER', 'RELAXAR', 'GOSTO', 'BOM', 'PREMIO']): return "BUSCA POR PRAZER"
    if any(k in t for k in ['SOCIAL', 'AMIGOS', 'ACOMPANHAR', 'TURMA']): return "PRESSÃO SOCIAL"
    if any(k in t for k in ['TÉDIO', 'TEDIO', 'NADA', 'FAZER']): return "TÉDIO"
    if len(t) > 1: return t
    return "NÃO INFORMADO"

def categorizar_motivos_principais_hibrida(texto):
    t = str(texto).upper().strip()
    if any(k in t for k in ['VICIO', 'VÍCIO', 'NICOTINA', 'QUIMICO', 'QUÍMICO', 'CORPO']): return "DEPENDÊNCIA QUÍMICA"
    if any(k in t for k in ['TREMEDEIRA', 'ABSTINENCIA', 'FALTA']): return "SINTOMAS DE ABSTINÊNCIA"
    if any(k in t for k in ['CALMA', 'PAZ', 'TRANQUILO', 'SOSSEGO', 'RELAX']): return "BUSCA POR PAZ/RELAXAMENTO"
    if any(k in t for k in ['FUGA', 'ESQUECER', 'SUMIR', 'PROBLEMA']): return "FUGA DA REALIDADE"
    if any(k in t for k in ['CORAGEM', 'FORÇA', 'ENFRENTAR']): return "BUSCA POR CORAGEM"
    if any(k in t for k in ['FOCO', 'CONCENTRAR', 'ESTUDAR', 'CRIAR']): return "AUMENTO DE FOCO"
    if any(k in t for k in ['ACEITACAO', 'GRUPO', 'JEITO', 'BONITO']): return "ACEITAÇÃO SOCIAL"
    if len(t) > 1: return t
    return "NÃO INFORMADO"

def categorizar_habitos_raio_x(texto):
    t = str(texto).upper().strip()
    if ('CAFE' in t or 'CAFÉ' in t) and ('CIGARRO' in t or 'FUMAR' in t): return "RITUAL CAFÉ + CIGARRO"
    if ('CERVEJA' in t or 'BEBIDA' in t) and ('AMIGOS' in t or 'CONVERSA' in t): return "CERVEJA E PAPO"
    if any(k in t for k in ['CAFE', 'CAFÉ', 'CAPUCCINO']): return "ACOMPANHANDO CAFÉ"
    if any(k in t for k in ['ALCOOL', 'ÁLCOOL', 'CERVEJA', 'BEBIDA', 'DRINK', 'VINHO']): return "BEBIDA ALCOÓLICA"
    if any(k in t for k in ['CELULAR', 'REDES', 'INSTA', 'TIKTOK', 'ZAP']): return "SCROLLANDO NO CELULAR"
    if any(k in t for k in ['DIRIGIR', 'CARRO', 'VOLANTE', 'MOTO']): return "DIRIGINDO"
    if any(k in t for k in ['PAUSA', 'INTERVALO', 'RESPIRO']): return "PAUSA NO TRABALHO"
    if any(k in t for k in ['TRABALHAR', 'PC', 'NOTEBOOK', 'EMAIL', 'COMPUTADOR']): return "TRABALHANDO (FOCO)"
    if any(k in t for k in ['COMER', 'DOCE', 'SOBREMESA', 'ALMOÇO', 'JANTAR']): return "APÓS REFEIÇÃO/DOCE"
    if any(k in t for k in ['CONVERSAR', 'PAPO', 'FALAR']): return "CONVERSA SOCIAL"
    if len(t) > 2: return t
    return "NENHUM HÁBITO ESPECÍFICO"

def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel da Autoconsciência")
    st.markdown("---")
    pie_layout = dict(margin=dict(l=0, r=0, t=50, b=0), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
    bar_layout = dict(margin=dict(l=0, r=0, t=50, b=0), yaxis=dict(autorange="reversed"))
    
    try:
        if df_aluno.shape[1] > 0:
            st.markdown("##### 1. Cronologia do Vício (Dias da Semana)")
            df_temp = df_aluno.copy()
            df_temp['Data'] = pd.to_datetime(df_temp.iloc[:, 0], dayfirst=True, errors='coerce')
            df_temp['Dia_Semana'] = df_temp['Data'].dt.day_name()
            mapa_dias = {'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta', 'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
            df_temp['Dia_PT'] = df_temp['Dia_Semana'].map(mapa_dias)
            contagem_dias = df_temp['Dia_PT'].value_counts().reset_index()
            contagem_dias.columns = ['Dia', 'Qtd']
            ordem_dias = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
            col_kpi, col_chart = st.columns([1, 3])
            col_kpi.metric("TOTAL DE CIGARROS", len(df_temp))
            fig1 = px.bar(contagem_dias, x='Dia', y='Qtd', category_orders={'Dia': ordem_dias}, color='Qtd', color_continuous_scale=['#90EE90', '#006400'])
            fig1.update_layout(margin=dict(l=0, r=0, t=50, b=0))
            col_chart.plotly_chart(fig1, use_container_width=True)
            st.markdown("---")

        if df_aluno.shape[1] > 3:
            st.markdown("##### 2. Principais Gatilhos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 3].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Gatilho', 'Qtd']
            fig2 = px.pie(dados, names='Gatilho', values='Qtd', hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
            fig2.update_layout(**pie_layout)
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")

        if df_aluno.shape[1] > 7:
            st.markdown("##### 3. Hábitos Associados")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 7].apply(categorizar_habitos_raio_x)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Hábito', 'Qtd']
            fig3 = px.bar(dados, x='Qtd', y='Hábito', orientation='h', text_auto=True, color_discrete_sequence=['#D2691E'])
            fig3.update_layout(**bar_layout)
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown("---")

        if df_aluno.shape[1] > 4:
            st.markdown("##### 4. Enfrentamento de Tarefas")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 4].apply(categorizar_enfrentamento_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Motivo', 'Qtd']
            fig4 = px.bar(dados, x='Qtd', y='Motivo', orientation='h', text_auto=True, color='Qtd', color_continuous_scale=['#87CEEB', '#00008B'])
            fig4.update_layout(**bar_layout)
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown("---")

        if df_aluno.shape[1] > 2:
            st.markdown("##### 5. Cantinhos Favoritos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 2].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Local', 'Qtd']
            fig5 = px.pie(dados, names='Local', values='Qtd', hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
            fig5.update_layout(**pie_layout)
            fig5.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig5, use_container_width=True)
            st.markdown("---")

        if df_aluno.shape[1] > 6:
            st.markdown("##### 6. Emoções Propícias ao Consumo")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 6].apply(lambda x: str(x).upper().strip())
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Emoção', 'Qtd']
            fig6 = px.bar(dados, x='Qtd', y='Emoção', orientation='h', text_auto=True, color='Qtd', color_continuous_scale=['#FA8072', '#8B0000'])
            fig6.update_layout(**bar_layout)
            st.plotly_chart(fig6, use_container_width=True)
            st.markdown("---")

        if df_aluno.shape[1] > 5:
            st.markdown("##### 7. Os Principais Motivos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 5].apply(categorizar_motivos_principais_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Motivo Principal', 'Qtd']
            fig7 = px.bar(dados, x='Qtd', y='Motivo Principal', orientation='h', text_auto=True, color='Qtd', color_continuous_scale=['#9370DB', '#4B0082'])
            fig7.update_layout(**bar_layout)
            st.plotly_chart(fig7, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao gerar gráficos: {e}")

# --- LÓGICA DE NAVEGAÇÃO ---
if "admin_logado" not in st.session_state: st.session_state.admin_logado = False
if "tipo_usuario" not in st.session_state: st.session_state.tipo_usuario = None 
if "email_logado" not in st.session_state: st.session_state.email_logado = ""

# SE ESTIVER LOGADO NO PAINEL (ADM OU MADRINHA)
if st.session_state.admin_logado:
    
    # Cabeçalho Personalizado
    if st.session_state.tipo_usuario == 'adm':
        st.title("👑 Painel do Fundador")
    else:
        st.title("🧚‍♀️ Painel da Madrinha")
        st.info(f"Logada como: {st.session_state.email_logado}")

    if st.button("🚪 Sair do Painel"):
        st.session_state.admin_logado = False
        st.session_state.tipo_usuario = None
        st.rerun()
    
    st.markdown("---")
    st.subheader("📊 Visão Geral da Turma")
    
    # VISÃO GERAL (TODOS VEEM)
    if not df_gatilhos_total.empty:
        c1, c2 = st.columns(2)
        c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
        c2.metric("Mapeamentos", len(df_gatilhos_total))
        exibir_dashboard_visual(df_gatilhos_total)
        
        # DOSSIÊ ESTRATÉGICO (SÓ ADM VÊ)
        if st.session_state.tipo_usuario == 'adm':
            st.markdown("---")
            st.subheader("🧠 Inteligência de Avatar (Diagnóstico de Turma)")
            if st.button("🌍 GERAR DOSSIÊ ESTRATÉGICO"):
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    top_g = df_gatilhos_total.iloc[:, 3].apply(categorizar_geral_hibrida).value_counts().head(10).to_dict()
                    top_e = df_gatilhos_total.iloc[:, 6].apply(lambda x: str(x).upper()).value_counts().head(10).to_dict()
                    top_h = df_gatilhos_total.iloc[:, 7].apply(categorizar_habitos_raio_x).value_counts().head(10).to_dict()
                    prompt_turma = f"""
                    Você é o Estrategista Chefe do 'Livre da Vontade'. Analise:
                    TOP GATILHOS: {top_g} | TOP EMOÇÕES: {top_e} | TOP HÁBITOS: {top_h}
                    TAREFA: Crie um Dossiê do Avatar Coletivo. Identifique o "Vilão nº 1", descreva o "Ciclo de Dor" e sugira 3 aulas.
                    """
                    with st.spinner("Gerando..."):
                        resp = model.generate_content(prompt_turma)
                        st.session_state.diag_turma = resp.text
                        st.success("Sucesso!")
                        st.markdown(st.session_state.diag_turma)
                except Exception as e: st.error(f"Erro: {e}")
            
            if "diag_turma" in st.session_state:
                pdf_turma = gerar_pdf_formatado({'nome': 'DOSSIÊ TURMA'}, pd.Series(), st.session_state.diag_turma)
                st.download_button("📥 Baixar Dossiê (PDF)", data=pdf_turma, file_name="Dossie_Turma.pdf")

    st.markdown("---")
    st.subheader("🔍 Auditoria Individual")
    emails_lista = df_perfil_total.iloc[:, 1].unique().tolist() if not df_perfil_total.empty else []
    aluno_selecionado = st.selectbox("Selecione o aluno:", [""] + emails_lista)
    
    if aluno_selecionado:
        p_adm = filtrar_aluno(df_perfil_total, aluno_selecionado)
        g_adm = filtrar_aluno(df_gatilhos_total, aluno_selecionado)
        
        if not g_adm.empty:
            exibir_dashboard_visual(g_adm)
        
        # BOTÃO DE DIAGNÓSTICO COM TRAVAS PARA MADRINHA
        pode_gerar_diag = True
        msg_bloqueio = ""
        
        if st.session_state.tipo_usuario == 'madrinha':
            if not verificar_limite_madrinha(st.session_state.email_logado, aluno_selecionado, df_log_total):
                pode_gerar_diag = False
                msg_bloqueio = "⚠️ Limite atingido: Você já gerou 2 diagnósticos para este aluno nos últimos 7 dias. Baixe o PDF anterior."

        if pode_gerar_diag:
            if st.button("🚀 GERAR DIAGNÓSTICO INDIVIDUAL"):
                # Registra o uso (para ADM e Madrinha)
                registrar_uso_diagnostico(st.session_state.email_logado, aluno_selecionado)
                try:
                    genai.configure(api_key=st.secrets["gemini"]["api_key"])
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    h_adm = g_adm.iloc[:, [3, 6]].tail(15).to_dict('records')
                    prompt_adm = f"Analise como Mentor IA: PERFIL {p_adm.tail(1).to_dict('records')} GATILHOS {h_adm}. Proibido sugerir vape/redução."
                    with st.spinner("Gerando auditoria..."):
                        resp = model.generate_content(prompt_adm)
                        st.session_state.diag_adm = resp.text
                        st.info(st.session_state.diag_adm)
                        st.rerun() # Atualiza para contar o uso na hora
                except Exception as e: st.error(f"Erro: {e}")
        else:
            st.error(msg_bloqueio)

        if "diag_adm" in st.session_state:
            d_adm = p_adm.tail(1).to_dict('records')[0] if not p_adm.empty else {}
            # Top gatilhos para o PDF
            top_g_pdf = g_adm.iloc[:,3].value_counts().head(3) if not g_adm.empty else pd.Series()
            pdf_adm = gerar_pdf_formatado(d_adm, top_g_pdf, st.session_state.diag_adm)
            st.download_button("📥 Baixar PDF", data=pdf_adm, file_name=f"Auditoria_{aluno_selecionado}.pdf")

# ÁREA DO ALUNO (DEFAULT)
else:
    logo_b64 = get_image_base64("logo.png")
    if logo_b64:
        header_html = f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <img src="{logo_b64}" style="width: 70px; margin-right: 10px;"> 
            <h1 style="margin: 0; padding: 0; white-space: nowrap;">Madrinha-IA</h1>
        </div>
        <h3 style="margin: 0; padding: 0;">MAPA COMPORTAMENTAL</h3>
        """
        st.markdown(header_html, unsafe_allow_html=True)
    else:
        st.markdown("# 🧚‍♀️ Madrinha-IA")
        st.markdown("### MAPA COMPORTAMENTAL")
    st.markdown("---")

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
            
            with st.expander("📲 Como instalar o App no celular"):
                st.markdown("""
                **Para iPhone (iOS):**
                1. No Safari, clique no botão de **Compartilhar** (quadrado com seta).
                2. Role para baixo e toque em **"Adicionar à Tela de Início"**.
                
                **Para Android:**
                1. No Chrome, clique nos **3 pontinhos** no canto superior.
                2. Toque em **"Adicionar à Tela Inicial"** ou **"Instalar Aplicativo"**.
                """)

            dados_aluno_pdf = {}
            top_gatilhos_pdf = pd.Series(dtype=int)
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

            dias_unicos = 0
            diagnosticos_usados = 0
            if not gatilhos.empty:
                df_datas = gatilhos.copy()
                df_datas['Data_Limpa'] = pd.to_datetime(df_datas.iloc[:, 0], dayfirst=True, errors='coerce').dt.date
                dias_unicos = df_datas['Data_Limpa'].nunique()
                if not df_log_total.empty:
                    # Filtra apenas os pedidos feitos PELO PRÓPRIO ALUNO (email dele na col QUEM_SOLICITOU)
                    # Coluna B (index 1) é QUEM_SOLICITOU
                    usos = df_log_total[df_log_total.iloc[:, 1].astype(str).str.strip().str.lower() == email]
                    diagnosticos_usados = len(usos)
            
            ciclos_completos = dias_unicos // 7
            total_diagnosticos_permitidos = ciclos_completos * 2
            saldo_diagnosticos = total_diagnosticos_permitidos - diagnosticos_usados

            if not gatilhos.empty:
                exibir_dashboard_visual(gatilhos)
                if gatilhos.shape[1] > 3:
                    df_temp = gatilhos.copy()
                    df_temp['Cat'] = df_temp.iloc[:, 3].apply(categorizar_geral_hibrida)
                    top_gatilhos_pdf = df_temp['Cat'].value_counts().head(3)
            else: st.info("Comece seu mapeamento para liberar o Painel.")

            st.markdown("---")
            st.subheader("🧠 Inteligência Comportamental")
            
            pode_gerar = False
            msg_botao = "🚀 GERAR DIAGNÓSTICO DO MENTOR"
            
            if dias_unicos < 7:
                st.warning(f"🔒 Faltam {7 - dias_unicos} dias de registro.")
                st.progress(dias_unicos / 7)
            elif saldo_diagnosticos <= 0:
                dias_prox = 7 - (dias_unicos % 7)
                if dias_prox == 0: dias_prox = 7
                st.warning(f"🔒 Ciclo encerrado. Registre mais {dias_prox} dias.")
                st.progress((dias_unicos % 7) / 7)
            else:
                pode_gerar = True
                if saldo_diagnosticos == 1: st.warning("⚠️ Atenção: Último diagnóstico do ciclo!")
                else: st.success(f"✅ {saldo_diagnosticos} diagnósticos disponíveis.")

            if pode_gerar:
                if st.button(msg_botao):
                    # Registra uso: QUEM (Aluno) | PARA QUEM (Aluno)
                    if registrar_uso_diagnostico(email, email):
                        try:
                            genai.configure(api_key=st.secrets["gemini"]["api_key"])
                            model = genai.GenerativeModel('gemini-2.0-flash')
                            col_indices = [3, 6] if gatilhos.shape[1] > 6 else [0]
                            hist = gatilhos.iloc[:, col_indices].tail(15).to_dict('records')
                            prompt = f"Analise como Mentor IA: DADOS {hist}. Explique Dopamina/Pavlov. Proibido Vape."
                            with st.spinner("Analisando..."):
                                resp = model.generate_content(prompt)
                                st.session_state.ultimo_diagnostico = resp.text
                                st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                    else: st.error("Erro ao registrar uso.")

            if "ultimo_diagnostico" in st.session_state:
                st.info(st.session_state.ultimo_diagnostico)
                pdf_b = gerar_pdf_formatado(dados_aluno_pdf, top_gatilhos_pdf, st.session_state.ultimo_diagnostico)
                st.download_button("📥 Baixar PDF", data=pdf_b, file_name="Diagnostico.pdf", mime="application/pdf")

    # --- ACESSO ADMINISTRATIVO NO RODAPÉ ---
    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    with st.expander("🔐 Acesso Restrito (Equipe)"):
        with st.form("login_admin_footer"):
            email_adm = st.text_input("E-mail:", placeholder="admin@email.com").strip().lower()
            pass_adm = st.text_input("Senha:", type="password", placeholder="******").strip() # .strip() para segurança
            if st.form_submit_button("Entrar no Painel"):
                # LOGIN FUNDADOR
                if email_adm == ADMIN_EMAIL and pass_adm == ADMIN_PASS:
                    st.session_state.admin_logado = True
                    st.session_state.tipo_usuario = 'adm'
                    st.session_state.email_logado = email_adm
                    st.rerun()
                # LOGIN MADRINHA
                elif email_adm in MADRINHAS_EMAILS and pass_adm == MADRINHA_PASS:
                    st.session_state.admin_logado = True
                    st.session_state.tipo_usuario = 'madrinha'
                    st.session_state.email_logado = email_adm
                    st.rerun()
                else:
                    st.error("Dados incorretos. Verifique se digitou a senha com Letra Maiúscula.")

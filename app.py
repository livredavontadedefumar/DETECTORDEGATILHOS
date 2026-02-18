import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from fpdf import FPDF
import plotly.express as px
from datetime import datetime, timedelta
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Madrinha-IA - MAPA COMPORTAMENTAL",
    page_icon="logo.png",  # Certifique-se de ter este arquivo ou remova se der erro
    layout="wide",
)

# --- CSS (FORÇAR RODAPÉ VISÍVEL E ESTILO) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {
                visibility: visible !important;
                display: block !important;
                opacity: 1 !important;
                position: relative !important;
            }
            .stButton>button {
                width: 100%;
                border-radius: 5px;
                height: 3em;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CONSTANTES DE ACESSO ---
# Nota: Em produção, idealmente mova senhas para st.secrets, mas mantive aqui conforme seu código.
ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
ADMIN_PASS = "Mc2284**lC"

MADRINHAS_EMAILS = [
    "luannyfaustino53@gmail.com",
    "costaebastos@hotmail.com"
]
MADRINHA_PASS = "Madrinha2026*"

# --- FUNÇÕES DE CONEXÃO ---
def conectar_planilha():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Certifique-se que seus segredos estão configurados no Streamlit Cloud
        creds_dict = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        sh = client.open("MAPEAMENTO (respostas)")
        return sh
    except Exception as e:
        st.error(f"Erro de conexão com Google Sheets: {e}")
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
                # Se não existir a aba LOG, cria um DF vazio
                df_l = pd.DataFrame(columns=["DATA", "QUEM_SOLICITOU", "ALUNO_ANALISADO"])
            
            df_p = pd.DataFrame(ws_perfil.get_all_records())
            df_g = pd.DataFrame(ws_gatilhos.get_all_records())
            return df_p, df_g, df_l
        except Exception as e:
            st.error(f"Erro ao ler abas da planilha: {e}")
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Carrega dados iniciais
df_perfil_total, df_gatilhos_total, df_log_total = carregar_todos_os_dados()

# --- FUNÇÕES ÚTEIS E LOG ---
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
    """Verifica se a Madrinha já gerou mais de 2 relatórios para o mesmo aluno nos últimos 7 dias."""
    if df_log.empty: return True
    
    # Normalizar strings
    email_madrinha = str(email_madrinha).strip().lower()
    email_aluno = str(email_aluno).strip().lower()
    
    # Filtrar log
    # Ajuste: garantindo que as colunas sejam strings
    df_log.iloc[:, 1] = df_log.iloc[:, 1].astype(str).str.strip().str.lower()
    df_log.iloc[:, 2] = df_log.iloc[:, 2].astype(str).str.strip().str.lower()
    
    mask_madrinha = df_log.iloc[:, 1] == email_madrinha
    mask_aluno = df_log.iloc[:, 2] == email_aluno
    
    usos = df_log[mask_madrinha & mask_aluno].copy()
    
    if usos.empty: return True
    
    # Converter data
    usos['Data_Obj'] = pd.to_datetime(usos.iloc[:, 0], errors='coerce')
    limite_data = datetime.now() - timedelta(days=7)
    
    usos_recentes = usos[usos['Data_Obj'] >= limite_data]
    
    if len(usos_recentes) >= 2:
        return False
    return True

def gerar_pdf_formatado(dados_perfil, top_gatilhos, texto_diagnostico):
    pdf = FPDF()
    pdf.add_page()
    
    # Tenta adicionar logo se existir
    try:
        pdf.image("logo.png", x=10, y=8, w=30)
        pdf.set_y(40)
    except: 
        pdf.set_y(20)

    # Cabeçalho
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(46, 125, 50) # Verde Escuro
    pdf.cell(0, 15, txt="Livre da Vontade de Fumar", ln=True, align="C")
    
    # Título do Relatório
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, txt="RAIO-X COMPORTAMENTAL & PLANO DE AÇÃO", ln=True, fill=True)
    
    # Dados do Aluno
    pdf.set_font("Arial", "", 10)
    nome = dados_perfil.get('nome', 'Análise Geral')
    pdf.cell(0, 7, txt=f"ALUNO(A): {nome}", ln=True)
    pdf.ln(5)
    
    # Resumo Rápido (Top Gatilhos)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, txt="RESUMO DOS PADRÕES", ln=True, fill=True)
    pdf.set_font("Arial", "B", 10)
    if isinstance(top_gatilhos, dict):
        for i, (g, qtd) in enumerate(top_gatilhos.items()):
            pdf.cell(0, 7, txt=f"{i+1}º Maior Gatilho: {str(g).upper()} ({qtd} registros)", ln=True)
    pdf.ln(10)
    
    # Diagnóstico da IA
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(46, 125, 50)
    pdf.cell(0, 10, txt="ANÁLISE DO ESPECIALISTA", ln=True)
    
    pdf.set_font("Arial", "", 11)
    pdf.set_text_color(0, 0, 0)
    
    # Tratamento de caracteres para evitar erro no FPDF (Latin-1)
    texto_limpo = texto_diagnostico.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 7, txt=texto_limpo)
    
    pdf.ln(15)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, txt="Metodologia Baseada em Neurociência e Ciência Comportamental", ln=True, align="C")
    
    return pdf.output(dest="S").encode("latin-1")

def filtrar_aluno(df, email_aluno):
    if df.empty: return pd.DataFrame()
    # Tenta achar coluna de email
    col_email = next((c for c in df.columns if "email" in c.lower() or "e-mail" in c.lower()), None)
    if col_email:
        df[col_email] = df[col_email].astype(str).str.strip().str.lower()
        return df[df[col_email] == email_aluno]
    return pd.DataFrame()

# --- INTELIGÊNCIA DE CATEGORIZAÇÃO (HÍBRIDA) ---
# Mantendo suas funções de categorização originais pois funcionam bem para os gráficos

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
    return "OUTROS"

def categorizar_enfrentamento_hibrida(texto):
    t = str(texto).upper().strip()
    if any(k in t for k in ['VONTADE', 'DESEJO', 'FORTE', 'FISSURA', 'QUERIA']): return "VONTADE INCONTROLÁVEL"
    if any(k in t for k in ['HABITO', 'HÁBITO', 'AUTOMATICO', 'AUTOMÁTICO', 'NEM VI']): return "HÁBITO AUTOMÁTICO"
    if any(k in t for k in ['ANSIEDADE', 'NERVOSO', 'ESTRESSE', 'TENSO', 'BRIGA']): return "ALÍVIO DE ESTRESSE"
    if any(k in t for k in ['PRAZER', 'RELAXAR', 'GOSTO', 'BOM', 'PREMIO']): return "BUSCA POR PRAZER"
    if any(k in t for k in ['SOCIAL', 'AMIGOS', 'ACOMPANHAR', 'TURMA']): return "PRESSÃO SOCIAL"
    if any(k in t for k in ['TÉDIO', 'TEDIO', 'NADA', 'FAZER']): return "TÉDIO"
    if len(t) > 1: return t
    return "OUTROS"

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
    return "OUTROS"

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

# --- INTELIGÊNCIA ANALÍTICA (O NOVO CÉREBRO) ---
def gerar_analise_comportamental_avancada(dados_brutos, dados_perfil):
    """
    Gera o Raio-X Comportamental usando o Mega Prompt do Especialista.
    """
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model_analista = genai.GenerativeModel('gemini-2.0-flash')
    
    # Prepara os dados brutos para string para economizar tokens e facilitar leitura
    try:
        dados_str = dados_brutos.to_string()
    except:
        dados_str = str(dados_brutos)

    prompt_especialista = f"""
    # ATUE COMO:
    Você é um Especialista Sênior em Ciências Comportamentais e Cessação de Tabagismo, com foco em Neurociência, Condicionamento Clássico (Pavlov), Psicologia Ambiental (Bruce Alexander/Rat Park) e Padrões de Hipnose Ericksoniana (Meta Padrão).

    # O CONTEXTO:
    Eu tenho um produto chamado "Detector de Gatilhos". O meu mentorado rastreou cada cigarro fumado durante 7 dias.
    PERFIL DO MENTORADO: {dados_perfil}
    
    # A SUA MISSÃO:
    Analise os dados brutos abaixo e gere um "Raio-X Comportamental" profundo. Não quero obviedades. Quero que encontre os padrões ocultos, as âncoras emocionais e as falhas no ambiente do mentorado.

    # ESTRUTURA DA ANÁLISE (Use estas 4 Lentes):

    1. 🔬 A Lente de Pavlov (Gatilhos Mecânicos):
       * Identifique os "Gatilhos Geográficos" (Onde ele fuma sempre? O local virou uma âncora?).
       * Identifique os "Gatilhos de Sequência" (O que acontece *imediatamente* antes? Café? Briga? Tédio?).

    2. 🐀 A Lente de Bruce Alexander (O "Rat Park"/Ambiente):
       * Analise as Emoções. O cigarro está a substituir que necessidade humana? (Conexão, Alívio de Stress, Fuga de uma "gaiola" emocional?).
       * Qual é a "Gaiola" atual desse mentorado? (Solidão, Trabalho excessivo, Tédio?).

    3. 🌀 A Lente do Meta Padrão (A Estrutura do Problema):
       * Qual é a "Intenção Positiva" do cigarro para ele? (Ex: Pausa, Proteção, Recompensa).
       * Qual é o "Estado Problema" (ex: Ansiedade) e qual o "Estado Desejado" (ex: Paz) que ele busca através do fumo?

    4. 🛠️ PLANO DE AÇÃO TÁTICO (Sugira 3 Micro-Ferramentas):
       * Sugira 1 ferramenta para quebrar o gatilho geográfico.
       * Sugira 1 ferramenta de respiração ou fisiológica para o momento da fissura.
       * Sugira 1 Metáfora Isomorfa (uma história curta ou imagem) que eu possa usar para ressignificar o vício dele.

    # DIRETRIZES DE OURO (O QUE NÃO FAZER):
    1. 🚫 NÃO chame o vício ou a fissura de "Inimigo", "Monstro" ou algo negativo. Use termos como "Sinal de Alerta", "Pedido de Pausa" ou "Mecanismo de Defesa Antigo". (Princípio da Intenção Positiva).
    2. 🚫 NÃO sugira cortes radicais de Café ou Álcool (como "pare por 12 meses") a menos que seja estritamente necessário. O mentorado já está sob stress. Sugira "Substituições Inteligentes" ou reduções graduais.
    3. 🚫 NÃO aponte apenas o gatilho (ex: "O quintal é o gatilho"). Dê uma SOLUÇÃO para o gatilho (ex: "Mude a cadeira de lugar", "Crie uma zona livre no quintal").

    # TOM DE VOZ:
    Profissional, empático, analítico e motivador. Fale diretamente comigo, o treinador.

    # DADOS DO MENTORADO PARA ANÁLISE:
    {dados_str}
    """
    
    try:
        response = model_analista.generate_content(prompt_especialista)
        return response.text
    except Exception as e:
        return f"Erro na análise profunda: {str(e)}"

# --- DASHBOARD VISUAL ---
def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel da Autoconsciência")
    st.markdown("---")
    
    # Layouts de gráfico
    pie_layout = dict(margin=dict(l=0, r=0, t=50, b=0), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
    bar_layout = dict(margin=dict(l=0, r=0, t=50, b=0), yaxis=dict(autorange="reversed"))
    
    try:
        # 1. Cronologia
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
            col_chart.plotly_chart(fig1, use_container_width=True)
            st.markdown("---")

        # 2. Gatilhos
        if df_aluno.shape[1] > 3:
            st.markdown("##### 2. Principais Gatilhos (Contexto)")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 3].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Gatilho', 'Qtd']
            fig2 = px.pie(dados, names='Gatilho', values='Qtd', hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
            fig2.update_layout(**pie_layout)
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)

        # 3. Hábitos
        if df_aluno.shape[1] > 7:
            st.markdown("##### 3. Hábitos Simultâneos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 7].apply(categorizar_habitos_raio_x)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Hábito', 'Qtd']
            fig3 = px.bar(dados, x='Qtd', y='Hábito', orientation='h', text_auto=True, color_discrete_sequence=['#D2691E'])
            fig3.update_layout(**bar_layout)
            st.plotly_chart(fig3, use_container_width=True)

        # 4. Emoções
        if df_aluno.shape[1] > 6:
            st.markdown("##### 4. Emoções Predominantes")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp.iloc[:, 6].apply(lambda x: str(x).upper().strip())
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Emoção', 'Qtd']
            fig6 = px.bar(dados, x='Qtd', y='Emoção', orientation='h', text_auto=True, color='Qtd', color_continuous_scale=['#FA8072', '#8B0000'])
            fig6.update_layout(**bar_layout)
            st.plotly_chart(fig6, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao gerar gráficos visuais: {e}")

# --- TELA DE LOGIN ---
def tela_login():
    st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Área exclusiva para Equipe Livre da Vontade de Fumar</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            submit = st.form_submit_button("ENTRAR")
            
            if submit:
                # Login Admin
                if email.lower().strip() == ADMIN_EMAIL.lower() and senha == ADMIN_PASS:
                    st.session_state.admin_logado = True
                    st.session_state.tipo_usuario = 'adm'
                    st.session_state.email_logado = email
                    st.success("Login Admin realizado!")
                    st.rerun()
                
                # Login Madrinhas
                elif email.lower().strip() in [m.lower() for m in MADRINHAS_EMAILS] and senha == MADRINHA_PASS:
                    st.session_state.admin_logado = True
                    st.session_state.tipo_usuario = 'madrinha'
                    st.session_state.email_logado = email
                    st.success("Login Madrinha realizado!")
                    st.rerun()
                
                else:
                    st.error("Acesso negado. Verifique suas credenciais.")

# --- LÓGICA PRINCIPAL ---

if "admin_logado" not in st.session_state: st.session_state.admin_logado = False
if "tipo_usuario" not in st.session_state: st.session_state.tipo_usuario = None 
if "email_logado" not in st.session_state: st.session_state.email_logado = ""

if not st.session_state.admin_logado:
    tela_login()

else:
    # --- ÁREA LOGADA ---
    # Sidebar
    with st.sidebar:
        st.image("logo.png", width=150) if get_image_base64("logo.png") else None
        st.write(f"👤 **{st.session_state.email_logado}**")
        st.write(f"Nível: {st.session_state.tipo_usuario.upper()}")
        
        if st.button("🚪 Sair"):
            st.session_state.admin_logado = False
            st.session_state.tipo_usuario = None
            st.rerun()

    # Cabeçalho Principal
    if st.session_state.tipo_usuario == 'adm':
        st.title("👑 Painel do Fundador")
    else:
        st.title("🧚‍♀️ Painel da Madrinha")
        st.info("Lembre-se: Você tem um limite de 2 diagnósticos por aluno a cada 7 dias.")
    
    st.markdown("---")
    
    # Seleção de Aluno
    emails_lista = []
    if not df_perfil_total.empty:
        # Pega emails da coluna de perfil (assumindo que é a coluna 1, ajustável)
        emails_lista = df_perfil_total.iloc[:, 1].unique().tolist()
        emails_lista.sort()
    
    st.subheader("🔍 Selecione o Aluno para Análise")
    aluno_selecionado = st.selectbox("Buscar por E-mail:", [""] + emails_lista)
    
    if aluno_selecionado:
        # Filtra Dados
        p_aluno = filtrar_aluno(df_perfil_total, aluno_selecionado)
        g_aluno = filtrar_aluno(df_gatilhos_total, aluno_selecionado)
        
        if g_aluno.empty:
            st.warning("Este aluno ainda não preencheu o formulário de gatilhos (Detector).")
        else:
            # Exibe Dashboard
            exibir_dashboard_visual(g_aluno)
            
            st.markdown("---")
            st.subheader("🧠 Inteligência Artificial Comportamental")
            
            # Verificações de permissão
            pode_gerar = True
            msg_bloqueio = ""
            
            if st.session_state.tipo_usuario == 'madrinha':
                if not verificar_limite_madrinha(st.session_state.email_logado, aluno_selecionado, df_log_total):
                    pode_gerar = False
                    msg_bloqueio = "⚠️ Limite semanal atingido para este aluno (2 diagnósticos/7 dias)."
            
            if not pode_gerar:
                st.error(msg_bloqueio)
            else:
                col_btn, col_info = st.columns([1, 2])
                
                # Chave única para o botão baseada no aluno para não resetar estado errado
                if col_btn.button("GERAR RAIO-X COMPORTAMENTAL (IA)", key=f"btn_gen_{aluno_selecionado}"):
                    with st.spinner("O Especialista está analisando os dados com as lentes de Pavlov, Alexander e Overdurf..."):
                        
                        # Prepara dados do perfil para o prompt
                        perfil_dict = p_aluno.iloc[0].to_dict() if not p_aluno.empty else {"Email": aluno_selecionado}
                        
                        # CHAMA A NOVA IA AVANÇADA
                        diagnostico = gerar_analise_comportamental_avancada(g_aluno, perfil_dict)
                        
                        # Salva no Session State para não perder no rerun
                        st.session_state['ultimo_diagnostico'] = diagnostico
                        st.session_state['aluno_diagnostico'] = aluno_selecionado
                        
                        # Registra o uso
                        registrar_uso_diagnostico(st.session_state.email_logado, aluno_selecionado)
                        st.success("Análise Concluída com Sucesso!")
                        st.rerun() # Recarrega para mostrar o resultado abaixo
    
    # Exibição do Resultado (fora do if do botão para persistir)
    if 'ultimo_diagnostico' in st.session_state and st.session_state.get('aluno_diagnostico') == aluno_selecionado:
        st.markdown("### 📝 Resultado da Análise:")
        st.info("Revise o texto abaixo antes de enviar ou gerar PDF.")
        
        texto_final = st.text_area("Edite se necessário:", value=st.session_state['ultimo_diagnostico'], height=400)
        
        # Preparar dados para PDF
        top_gatilhos = {}
        if not g_aluno.empty:
            top_gatilhos = g_aluno.iloc[:, 3].apply(categorizar_geral_hibrida).value_counts().head(5).to_dict()
        
        dados_perfil_pdf = {'nome': aluno_selecionado} # Melhorar se tiver nome no perfil
        
        # Botão Download PDF
        pdf_bytes = gerar_pdf_formatado(dados_perfil_pdf, top_gatilhos, texto_final)
        
        st.download_button(
            label="📥 Baixar Relatório em PDF",
            data=pdf_bytes,
            file_name=f"RaioX_Comportamental_{aluno_selecionado}.pdf",
            mime="application/pdf"
        )

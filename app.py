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
    page_icon="logo.png",
    layout="wide",
)

# --- CSS (FORÇAR RODAPÉ VISÍVEL) ---
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
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CONSTANTES DE ACESSO ---
ADMIN_EMAIL = "livredavontadedefumar@gmail.com"
ADMIN_PASS = "Mc2284**lC"

MADRINHAS_EMAILS = [
    "luannyfaustino53@gmail.com",
    "costaebastos@hotmail.com"
]
MADRINHA_PASS = "Madrinha2026*"

# --- FUNÇÕES DE ARQUIVO E CONEXÃO ---
def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except Exception:
        return None

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
            
            try:
                ws_sos = sh.worksheet("LOG_SOS")
                df_sos = pd.DataFrame(ws_sos.get_all_records())
            except:
                df_sos = pd.DataFrame(columns=["DATA", "EMAIL", "MENSAGEM"])
            
            df_p = pd.DataFrame(ws_perfil.get_all_records())
            df_g = pd.DataFrame(ws_gatilhos.get_all_records())
            return df_p, df_g, df_l, df_sos
        except Exception as e:
            st.error(f"Erro ao ler abas: {e}")
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(columns=["DATA", "EMAIL", "MENSAGEM"])

df_perfil_total, df_gatilhos_total, df_log_total, df_sos_total = carregar_todos_os_dados()

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

# --- FUNÇÕES DO BOTÃO SOS ---
def verificar_limites_sos(email_aluno, df_sos):
    if df_sos.empty:
        return True, "", 0, 0
    
    usos = df_sos[df_sos['EMAIL'].astype(str).str.strip().str.lower() == email_aluno.strip().lower()].copy()
    if usos.empty:
        return True, "", 0, 0
        
    usos['Data_Obj'] = pd.to_datetime(usos['DATA'], errors='coerce')
    agora = datetime.now()
    
    usos_hoje = usos[usos['Data_Obj'].dt.date == agora.date()]
    qtd_hoje = len(usos_hoje)
    
    usos_mes = usos[(usos['Data_Obj'].dt.year == agora.year) & (usos['Data_Obj'].dt.month == agora.month)]
    qtd_mes = len(usos_mes)
    
    if qtd_hoje >= 3:
        return False, "⚠️ Limite diário atingido: Você já usou o SOS 3 vezes hoje. Continue aplicando as rotinas de defesa.", qtd_hoje, qtd_mes
    if qtd_mes >= 15:
        return False, "⚠️ Limite mensal atingido: Você já usou o SOS 15 vezes neste mês. O limite renova no dia 1º.", qtd_hoje, qtd_mes
        
    return True, "", qtd_hoje, qtd_mes

def registrar_uso_sos(email_aluno, mensagem):
    sh = conectar_planilha()
    if sh:
        try:
            try:
                ws_sos = sh.worksheet("LOG_SOS")
            except:
                ws_sos = sh.add_worksheet(title="LOG_SOS", rows="1000", cols="3")
                ws_sos.append_row(["DATA", "EMAIL", "MENSAGEM"])
            
            data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws_sos.append_row([data_hora, email_aluno, str(mensagem)])
            return True
        except:
            return False
    return False

def gerar_resposta_sos(mensagem_usuario, perfil_resumo, gatilhos_resumo):
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model_sos = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt_sos = f"""
    Atue como a "Madrinha", a mentora IA sábia e acolhedora do método Livre da Vontade.
    A usuária acabou de acionar o BOTAO DE SOS porque está com uma fissura (vontade forte de fumar) ou ansiedade alta.
    
    MENSAGEM DELA AGORA: "{mensagem_usuario}"
    
    CONTEXTO DO MAPA COMPORTAMENTAL DA USUÁRIA:
    Perfil: {perfil_resumo}
    Gatilhos Comuns: {gatilhos_resumo}
    
    SUA MISSÃO IMEDIATA:
    1. Acolha o sentimento dela imediatamente, demonstrando muita empatia.
    2. Valide que isso é apenas o reflexo automático da química/ambiente e que essa onda vai passar.
    3. Entregue UMA ferramenta prática e simples (ex: Respiração 4 tempos, mudar de cômodo, beber um copo d'água gelada) adequada ao momento que ela relatou.
    4. Seja curta e direta! No máximo 2 parágrafos curtos. Ela está ansiosa, não tem paciência para ler textos longos agora.
    """
    try:
        response = model_sos.generate_content(prompt_sos)
        return response.text
    except Exception as e:
        return f"Erro ao gerar socorro: {str(e)}"

# --- GERAÇÃO DE PDF E FILTROS ---
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
        pdf.cell(0, 7, txt=f"{i+1}o: {str(g).upper()} ({qtd}x)", ln=True)
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

def buscar_coluna_por_palavra_chave(df, palavras_chave):
    for col in df.columns:
        col_upper = str(col).upper()
        if any(kw.upper() in col_upper for kw in palavras_chave):
            return col
    return None

def categorizar_geral_hibrida(texto):
    t = str(texto).upper().strip()
    if t == 'NAN' or t == 'NONE' or t == '': return "NÃO INFORMADO"
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

def analisar_intencoes_ocultas(dados_brutos, dados_perfil):
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model_analista = genai.GenerativeModel('gemini-2.0-flash')
    
    try:
        dados_str = str(dados_brutos)
    except:
        dados_str = "Dados não formatáveis."

    prompt_detetive = f"""
    Atue como um Analista de Dados Comportamentais Sênior (Frio, clínico e direto).
    
    PERFIL DO USUÁRIO: {dados_perfil}
    DADOS DE CONSUMO: {dados_str}
    
    SUA MISSÃO: Faça um mapeamento técnico usando 4 Lentes da ciência comportamental:
    1. PAVLOV (Gatilhos): Qual é o principal gatilho geográfico (local) e de sequência (o que acontece antes)? Há padrão de intensidade?
    2. ALEXANDER (Gaiola): O ambiente dele gera que tipo de necessidade? (Solidão, stress, pausa?)
    3. OVERDURF (Intenção): Qual é a intenção positiva primária (Estado Desejado) por trás do cigarro? (Ex: fuga, alívio, recompensa).
    4. ELMAN (Transe): O que as mãos e a mente estão fazendo? (Há algum transe hipnótico associado, como mexer no celular ou olhar pro nada?)
    
    Forneça apenas o relatório técnico cru em tópicos curtos, focado na raiz do problema.
    """
    try:
        response = model_analista.generate_content(prompt_detetive)
        return response.text
    except Exception as e:
        return f"Erro na análise do detetive: {str(e)}"

def gerar_diagnostico_final(analise_detetive):
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model_mentor = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt_mentor = f"""
    Atue como o MENTOR SÊNIOR do Método "Livre da Vontade". O seu tom é acolhedor, direto, claro e encorajador.
    
    >>> RELATÓRIO DO DETETIVE (INPUT TÉCNICO):
    {analise_detetive}
    <<<
    
    SUA MISSÃO: Escrever o "Raio-X Comportamental e Diagnóstico" final para o aluno ler. Traduza o relatório acima em ações práticas, de forma amigável.
    
    REGRAS DE OURO:
    1. 🚫 PROIBIDO usar nomes de cientistas (Pavlov, Alexander, Skinner, Elman) ou jargões ("Meta Padrão", "Condicionamento", "Extinção"). Fale a língua do aluno. Use "Gatilho Automático", "Ambiente", "Ritual".
    2. 🚫 NÃO mande parar de fumar hoje. Esta fase é apenas de preparação e estratégia.
    3. 🚫 NÃO chame o vício de "Inimigo", "Monstro" ou "Maldito". Use "Sinal de Alerta", "Busca por Alívio" ou "Mecanismo de Fuga".
    4. OBRIGATÓRIO: Diga para ele continuar a preencher o Detector (App) todos os dias até parar definitivamente.
    5. Se envolver café ou álcool, sugira substituições de forma gentil, sem radicalismos que causem stress extra.
    6. Crie 1 Ferramenta Prática baseada no problema principal. Exemplo: "Elemento Neutro" (beber água, mudar trajeto) para quebrar o hábito automático, ou "Dissipação/Desconforto" (respiração, segurar gelo) para ansiedade/fissura.
    """
    try:
        response = model_mentor.generate_content(prompt_mentor)
        return response.text
    except Exception as e:
        return f"Erro na geração do diagnóstico: {str(e)}"

def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel da Autoconsciência")
    st.markdown("---")
    pie_layout = dict(margin=dict(l=0, r=0, t=50, b=0), legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5))
    bar_layout = dict(margin=dict(l=0, r=0, t=50, b=0), yaxis=dict(autorange="reversed"))
    
    try:
        if df_aluno.shape[1] > 0:
            st.markdown("##### 1. Cronologia do Vício (Dias da Semana)")
            col_data = df_aluno.columns[0]
            df_temp = df_aluno.copy()
            df_temp['Data_Formatada'] = pd.to_datetime(df_temp[col_data], dayfirst=True, errors='coerce')
            df_temp['Dia_Semana'] = df_temp['Data_Formatada'].dt.day_name()
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

        col_antes = buscar_coluna_por_palavra_chave(df_aluno, ["ANTES", "ACONTECEU ANTES"])
        if col_antes:
            st.markdown("##### 2. Gatilhos de Ação (O que aconteceu antes)")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp[col_antes].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Gatilho', 'Qtd']
            fig2 = px.pie(dados, names='Gatilho', values='Qtd', hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
            fig2.update_layout(**pie_layout)
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")

        col_maos = buscar_coluna_por_palavra_chave(df_aluno, ["MÃOS", "MAIS VOCÊ VAI FAZER", "MENTE", "ENQUANTO FUMO"])
        if col_maos:
            st.markdown("##### 3. Hábitos Associados")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp[col_maos].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Hábito', 'Qtd']
            fig3 = px.bar(dados, x='Qtd', y='Hábito', orientation='h', text_auto=True, color_discrete_sequence=['#D2691E'])
            fig3.update_layout(**bar_layout)
            st.plotly_chart(fig3, use_container_width=True)
            st.markdown("---")

        col_motivo = buscar_coluna_por_palavra_chave(df_aluno, ["RESOLVER", "PROPORCIONAR", "POR QUE EXATAMENTE"])
        if col_motivo:
            st.markdown("##### 4. O Verdadeiro Motivo (Intenção)")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp[col_motivo].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Motivo', 'Qtd']
            fig4 = px.bar(dados, x='Qtd', y='Motivo', orientation='h', text_auto=True, color='Qtd', color_continuous_scale=['#87CEEB', '#00008B'])
            fig4.update_layout(**bar_layout)
            st.plotly_chart(fig4, use_container_width=True)
            st.markdown("---")

        col_local = buscar_coluna_por_palavra_chave(df_aluno, ["AONDE EXATAMENTE", "AONDE ESTOU", "ONDE E COM QUEM"])
        if col_local:
            st.markdown("##### 5. Cantinhos Favoritos")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp[col_local].apply(categorizar_geral_hibrida)
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Local', 'Qtd']
            fig5 = px.pie(dados, names='Local', values='Qtd', hole=0.5, color_discrete_sequence=px.colors.qualitative.Bold)
            fig5.update_layout(**pie_layout)
            fig5.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig5, use_container_width=True)
            st.markdown("---")

        col_emocao = buscar_coluna_por_palavra_chave(df_aluno, ["EMOÇÃO", "EMOCAO"])
        if col_emocao:
            st.markdown("##### 6. Emoções Propícias ao Consumo")
            df_temp = df_aluno.copy()
            df_temp['Cat'] = df_temp[col_emocao].apply(lambda x: str(x).upper().strip() if pd.notnull(x) else "NÃO INFORMADO")
            dados = df_temp['Cat'].value_counts().head(10).reset_index()
            dados.columns = ['Emoção', 'Qtd']
            fig6 = px.bar(dados, x='Qtd', y='Emoção', orientation='h', text_auto=True, color='Qtd', color_continuous_scale=['#FA8072', '#8B0000'])
            fig6.update_layout(**bar_layout)
            st.plotly_chart(fig6, use_container_width=True)
            st.markdown("---")

        col_intensidade = buscar_coluna_por_palavra_chave(df_aluno, ["URGÊNCIA", "VONTADE", "ESCALA", "1 A 10"])
        if col_intensidade and not df_aluno[col_intensidade].isnull().all():
            st.markdown("##### 7. Nível de Urgência (Fissura)")
            df_temp = df_aluno.copy()
            df_temp['Intensidade'] = pd.to_numeric(df_temp[col_intensidade], errors='coerce').fillna(0)
            df_temp = df_temp[df_temp['Intensidade'] > 0] 
            if not df_temp.empty:
                dados = df_temp['Intensidade'].value_counts().reset_index()
                dados.columns = ['Nível', 'Qtd']
                fig7 = px.bar(dados, x='Nível', y='Qtd', text_auto=True, color='Nível', color_continuous_scale=['#FFD700', '#FF0000'])
                fig7.update_xaxes(type='category')
                fig7.update_layout(margin=dict(l=0, r=0, t=50, b=0))
                st.plotly_chart(fig7, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao gerar gráficos: {e}")

# --- LÓGICA DE NAVEGAÇÃO ---
if "admin_logado" not in st.session_state: st.session_state.admin_logado = False
if "tipo_usuario" not in st.session_state: st.session_state.tipo_usuario = None 
if "email_logado" not in st.session_state: st.session_state.email_logado = ""

if st.session_state.admin_logado:
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
    
    # --- ABA 1: VISÃO GERAL DA TURMA (ADMIN E MADRINHAS) ---
    with st.expander("📊 Visão Geral da Turma"):
        if not df_gatilhos_total.empty:
            c1, c2 = st.columns(2)
            c1.metric("Total de Alunos", df_perfil_total.iloc[:,1].nunique() if not df_perfil_total.empty else 0)
            c2.metric("Mapeamentos", len(df_gatilhos_total))
            exibir_dashboard_visual(df_gatilhos_total)
            
            if st.session_state.tipo_usuario == 'adm':
                st.markdown("---")
                st.markdown("#### 🧠 Inteligência de Avatar (Diagnóstico de Turma)")
                if st.button("🌍 GERAR DOSSIÊ ESTRATÉGICO"):
                    try:
                        genai.configure(api_key=st.secrets["gemini"]["api_key"])
                        model = genai.GenerativeModel('gemini-2.0-flash')
                        col_antes = buscar_coluna_por_palavra_chave(df_gatilhos_total, ["ANTES"]) or df_gatilhos_total.columns[3]
                        col_emo = buscar_coluna_por_palavra_chave(df_gatilhos_total, ["EMOÇÃO"]) or df_gatilhos_total.columns[6]
                        
                        top_g = df_gatilhos_total[col_antes].apply(categorizar_geral_hibrida).value_counts().head(10).to_dict()
                        top_e = df_gatilhos_total[col_emo].apply(lambda x: str(x).upper()).value_counts().head(10).to_dict()
                        
                        prompt_turma = f"""
                        Você é o Estrategista Chefe. Analise:
                        TOP GATILHOS: {top_g} | TOP EMOÇÕES: {top_e}
                        TAREFA: Dossiê do Avatar Coletivo. Vilão nº 1 e Soluções (Sem termos técnicos complexos).
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

    # --- ABA 2: AUDITORIA INDIVIDUAL (ADMIN E MADRINHAS) ---
    with st.expander("🔍 Auditoria Individual"):
        emails_lista = df_perfil_total.iloc[:, 1].unique().tolist() if not df_perfil_total.empty else []
        aluno_selecionado = st.selectbox("Selecione o aluno:", [""] + emails_lista)
        
        if aluno_selecionado:
            p_adm = filtrar_aluno(df_perfil_total, aluno_selecionado)
            g_adm = filtrar_aluno(df_gatilhos_total, aluno_selecionado)
            
            if not g_adm.empty:
                exibir_dashboard_visual(g_adm)
            
            pode_gerar_diag = True
            msg_bloqueio = ""
            
            if st.session_state.tipo_usuario == 'madrinha':
                if not verificar_limite_madrinha(st.session_state.email_logado, aluno_selecionado, df_log_total):
                    pode_gerar_diag = False
                    msg_bloqueio = "⚠️ Limite atingido: Você já gerou 2 diagnósticos para este aluno nos últimos 7 dias. Baixe o PDF anterior."

            if pode_gerar_diag:
                if st.button("🚀 GERAR DIAGNÓSTICO ESTRATÉGICO"):
                    registrar_uso_diagnostico(st.session_state.email_logado, aluno_selecionado)
                    try:
                        perfil_dict = p_adm.tail(1).to_dict('records')[0] if not p_adm.empty else {}
                        col_email = buscar_coluna_por_palavra_chave(g_adm, ["EMAIL", "E-MAIL"])
                        cols_to_keep = [c for c in g_adm.columns if c != col_email]
                        h_adm = g_adm[cols_to_keep].tail(20).to_dict('records') 
                        
                        with st.spinner("Passo 1/2: O Detetive está a mapear os padrões ocultos..."):
                            analise_oculta = analisar_intencoes_ocultas(h_adm, perfil_dict)
                            
                        with st.spinner("Passo 2/2: O Mentor está a traduzir a estratégia para o aluno..."):
                            analise_final = gerar_diagnostico_final(analise_oculta)
                            st.session_state.diag_adm = analise_final
                            st.success("Diagnóstico Gerado com Sucesso!")
                            st.markdown(st.session_state.diag_adm)
                            
                    except Exception as e: st.error(f"Erro: {e}")
            else:
                st.error(msg_bloqueio)

            if "diag_adm" in st.session_state:
                d_adm = p_adm.tail(1).to_dict('records')[0] if not p_adm.empty else {}
                col_resumo = buscar_coluna_por_palavra_chave(g_adm, ["ANTES"])
                if col_resumo:
                    top_g_pdf = g_adm[col_resumo].value_counts().head(3)
                else:
                    top_g_pdf = pd.Series()
                pdf_adm = gerar_pdf_formatado(d_adm, top_g_pdf, st.session_state.diag_adm)
                st.download_button("📥 Baixar PDF", data=pdf_adm, file_name=f"Auditoria_{aluno_selecionado}.pdf")

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
            
            # --- CAIXA DE DADOS DO ALUNO NO TOPO PARA FICAR VISÍVEL ---
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
            
            # --- ABA 1: COMO INSTALAR ---
            with st.expander("📲 Como instalar o App no celular"):
                st.markdown("""
                **Para iPhone (iOS):**
                1. No Safari, clique no botão de **Compartilhar**.
                2. Role para baixo e toque em **"Adicionar à Tela de Início"**.
                
                **Para Android:**
                1. No Chrome, clique nos **3 pontinhos**.
                2. Toque em **"Instalar Aplicativo"**.
                """)

            # --- ABA 2: SOS MADRINHA-IA ---
            pode_usar_sos, msg_erro_sos, usos_hoje, usos_mes = verificar_limites_sos(email, df_sos_total)
            
            with st.expander("🚨 SOS Madrinha-IA"):
                with st.form(key=f"form_sos_emergencia"):
                    st.markdown("### SOS Madrinha-IA")
                    st.markdown("#### (Ajuda Imediata)")
                    st.markdown("A vontade apertou? A ansiedade bateu forte agora? Escreva abaixo o que está sentindo e eu te ajudo neste exato momento.")
                    
                    mensagem_sos = st.text_area("O que você está sentindo/pensando agora?", placeholder="Ex: Acabei de brigar e deu uma vontade louca de acender um cigarro...")
                    
                    col_sos1, col_sos2 = st.columns([1, 2])
                    with col_sos1:
                        submit_sos = st.form_submit_button("🆘 Enviar Pedido", disabled=not pode_usar_sos, use_container_width=True)
                    with col_sos2:
                        st.caption(f"**Seus Limites do SOS:** Você usou **{usos_hoje}/3** hoje e **{usos_mes}/15** neste mês.")

                    if submit_sos:
                        if not pode_usar_sos:
                            st.error(msg_erro_sos)
                        elif not mensagem_sos.strip():
                            st.warning("Por favor, digite o que está sentindo antes de enviar o SOS.")
                        else:
                            with st.spinner("A Madrinha está preparando a sua resposta..."):
                                if registrar_uso_sos(email, mensagem_sos):
                                    perfil_resumo = perfil.tail(1).to_dict('records')[0] if not perfil.empty else "Dados do perfil não disponíveis"
                                    
                                    col_resumo_aluno_sos = buscar_coluna_por_palavra_chave(gatilhos, ["ANTES"])
                                    if col_resumo_aluno_sos and not gatilhos.empty:
                                        gatilhos_resumo = gatilhos[col_resumo_aluno_sos].apply(categorizar_geral_hibrida).value_counts().head(3).to_dict()
                                    else:
                                        gatilhos_resumo = "O aluno ainda está começando a mapear os gatilhos..."
                                        
                                    resposta_sos = gerar_resposta_sos(mensagem_sos, perfil_resumo, gatilhos_resumo)
                                    st.session_state[f'sos_resposta_{email}'] = resposta_sos
                                    st.rerun() 
                                else:
                                    st.error("Erro de conexão com o banco de dados do SOS. Tente novamente.")

                if f'sos_resposta_{email}' in st.session_state:
                    st.success(f"💌 **A Madrinha Diz:**\n\n{st.session_state[f'sos_resposta_{email}']}")

            # Lógica de contagem de dias (necessária para Painel e Inteligência)
            dias_unicos = 0
            diagnosticos_usados = 0
            if not gatilhos.empty:
                df_datas = gatilhos.copy()
                col_data_aluno = df_datas.columns[0]
                df_datas['Data_Limpa'] = pd.to_datetime(df_datas[col_data_aluno], dayfirst=True, errors='coerce').dt.date
                dias_unicos = df_datas['Data_Limpa'].nunique()
                if not df_log_total.empty:
                    usos = df_log_total[df_log_total.iloc[:, 1].astype(str).str.strip().str.lower() == email]
                    diagnosticos_usados = len(usos)
            
            ciclos_completos = dias_unicos // 7
            total_diagnosticos_permitidos = ciclos_completos * 2
            saldo_diagnosticos = total_diagnosticos_permitidos - diagnosticos_usados

            # --- ABA 3: PAINEL DE CONSCIÊNCIA ---
            with st.expander("📊 Painel de Consciência"):
                if not gatilhos.empty:
                    exibir_dashboard_visual(gatilhos)
                    col_resumo_aluno = buscar_coluna_por_palavra_chave(gatilhos, ["ANTES"])
                    if col_resumo_aluno:
                        df_temp = gatilhos.copy()
                        df_temp['Cat'] = df_temp[col_resumo_aluno].apply(categorizar_geral_hibrida)
                        top_gatilhos_pdf = df_temp['Cat'].value_counts().head(3)
                else: 
                    st.info("Comece seu mapeamento para liberar o Painel.")

            # --- ABA 4: INTELIGÊNCIA COMPORTAMENTAL ---
            with st.expander("🧠 Inteligência Comportamental"):
                pode_gerar = False
                msg_botao = "🚀 GERAR MEU DIAGNÓSTICO ESTRATÉGICO"
                
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
                        if registrar_uso_diagnostico(email, email):
                            try:
                                col_email = buscar_coluna_por_palavra_chave(gatilhos, ["EMAIL", "E-MAIL"])
                                cols_to_keep = [c for c in gatilhos.columns if c != col_email]
                                hist_raw = gatilhos[cols_to_keep].tail(20).to_dict('records')
                                perfil_raw = perfil.tail(1).to_dict('records') if not perfil.empty else {}

                                with st.spinner("Passo 1/2: Analisando padrões comportamentais ocultos..."):
                                    analise_oculta = analisar_intencoes_ocultas(hist_raw, perfil_raw)

                                with st.spinner("Passo 2/2: Criando plano de ação personalizado..."):
                                    analise_final = gerar_diagnostico_final(analise_oculta)
                                    st.session_state.ultimo_diagnostico = analise_final
                                    st.rerun()
                                    
                            except Exception as e: st.error(f"Erro: {e}")
                        else: st.error("Erro ao registrar uso.")

                if "ultimo_diagnostico" in st.session_state:
                    st.info(st.session_state.ultimo_diagnostico)
                    pdf_b = gerar_pdf_formatado(dados_aluno_pdf, top_gatilhos_pdf, st.session_state.ultimo_diagnostico)
                    st.download_button("📥 Baixar PDF", data=pdf_b, file_name="Diagnostico.pdf", mime="application/pdf")

    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    with st.expander("🔐 Acesso Restrito (Equipe)"):
        with st.form("login_admin_footer"):
            email_adm = st.text_input("E-mail:", placeholder="admin@email.com").strip().lower()
            pass_adm = st.text_input("Senha:", type="password", placeholder="******").strip()
            if st.form_submit_button("Entrar no Painel"):
                if email_adm == ADMIN_EMAIL and pass_adm == ADMIN_PASS:
                    st.session_state.admin_logado = True
                    st.session_state.tipo_usuario = 'adm'
                    st.session_state.email_logado = email_adm
                    st.rerun()
                elif email_adm in MADRINHAS_EMAILS and pass_adm == MADRINHA_PASS:
                    st.session_state.admin_logado = True
                    st.session_state.tipo_usuario = 'madrinha'
                    st.session_state.email_logado = email_adm
                    st.rerun()
                else:
                    st.error("Dados incorretos.")

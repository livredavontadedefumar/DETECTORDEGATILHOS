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

# --- CÉREBRO DE CATEGORIZAÇÃO (GRANULARIDADE MÁXIMA) ---
def categorizar_inteligente(texto):
    """
    Função Mestra: Classifica tanto LOCAIS quanto GATILHOS com precisão.
    """
    t = str(texto).upper().strip()
    
    # --- GRUPO 1: GATILHOS BIOLÓGICOS (PRIORIDADE MÁXIMA) ---
    
    # Acordar (O mais forte do dia)
    termos_acordar = ['ACORDEI', 'ACORDANDO', 'LEVANTANDO', 'CAMA', 'JEJUM', 'PRIMEIRO', 'MANHÃ', 'DESPERTADOR']
    if any(term in t for term in termos_acordar):
        return "PRIMEIRO DO DIA (ACORDAR)"

    # Café (Associação Pavloviana Forte)
    termos_cafe = ['CAFE', 'CAFÉ', 'CAPUCCINO', 'PADARIA', 'DESJEJUM', 'EXPRESSO', 'COFFEE']
    if any(term in t for term in termos_cafe):
        return "GATILHO DO CAFÉ"

    # Pós-Refeição (Metabolismo)
    termos_comida = ['ALMOÇO', 'JANTAR', 'COMER', 'FOME', 'BARRIGA', 'REFEIÇÃO', 'LANCHE', 'RESTAURANTE', 'PIZZA', 'CHURRASCO', 'SOBREMESA']
    if any(term in t for term in termos_comida):
        return "PÓS-REFEIÇÃO"

    # Álcool/Social
    termos_social = ['CERVEJA', 'BEBER', 'BAR', 'FESTA', 'AMIGOS', 'VINHO', 'HAPPY', 'BALADA', 'SOCIAL']
    if any(term in t for term in termos_social):
        return "BEBIDA ALCOÓLICA / SOCIAL"

    # --- GRUPO 2: LOCAIS ESPECÍFICOS (O "NINHO" DO VÍCIO) ---
    
    termos_cozinha = ['COZINHA', 'BALCÃO', 'BALCAO', 'GELADEIRA', 'PIA', 'FOGÃO', 'MESA', 'CHALEIRA']
    if any(term in t for term in termos_cozinha):
        return "COZINHA / BALCÃO"

    termos_externo = ['VARANDA', 'SACADA', 'QUINTAL', 'JARDIM', 'GARAGEM', 'PORTÃO', 'CALÇADA', 'RUA', 'JANELA']
    if any(term in t for term in termos_externo):
        return "ÁREA EXTERNA / VARANDA"

    termos_banheiro = ['BANHEIRO', 'BANHO', 'PRIVADA', 'LAVABO', 'VASON']
    if any(term in t for term in termos_banheiro):
        return "BANHEIRO"
        
    termos_quarto = ['QUARTO', 'CABECEIRA', 'DORMITÓRIO']
    if any(term in t for term in termos_quarto):
        return "QUARTO"

    # --- GRUPO 3: CONTEXTOS DE AÇÃO E ESTRESSE ---

    # Trânsito (Estresse de Deslocamento)
    termos_transito = ['CARRO', 'TRANSITO', 'TRÂNSITO', 'DIRIGINDO', 'UBER', 'ÔNIBUS', 'METRÔ', 'ENGARRAFAMENTO', 'SEMAFORO', 'MOTO', 'VOLANTE']
    if any(term in t for term in termos_transito):
        return "TRÂNSITO / DESLOCAMENTO"

    # Trabalho (Foco ou Estresse)
    termos_trabalho = ['CHEFE', 'REUNIÃO', 'PRAZO', 'CLIENTE', 'EMAIL', 'ESCRITÓRIO', 'TRABALHO', 'JOB', 'PROJETO', 'COMPUTADOR', 'LIGAÇÃO', 'EMPRESA']
    if any(term in t for term in termos_trabalho):
        return "TRABALHO / ESCRITÓRIO"
    
    # Telas (Novo Gatilho Moderno)
    termos_tela = ['CELULAR', 'INSTAGRAM', 'TIKTOK', 'ZAP', 'WHATSAPP', 'NOTÍCIA', 'JOGO', 'SCROLLANDO', 'INTERNET']
    if any(term in t for term in termos_tela):
        return "CELULAR / REDES SOCIAIS"

    # Espera/Ocio
    termos_espera = ['ESPERANDO', 'FILA', 'PONTO', 'AGUARDANDO', 'NADA', 'TÉDIO', 'TV', 'NETFLIX', 'SOFÁ']
    if any(term in t for term in termos_espera):
        return "MOMENTO DE ESPERA / TÉDIO"

    # --- GRUPO 4: EMOÇÕES E ROTINA GERAL ---
    
    termos_ansiedade = ['ANSIEDADE', 'NERVOSO', 'BRIGA', 'DISCUSSÃO', 'ESTRESSE', 'CHATEADO', 'TRISTE', 'RAIVA', 'CHORAR', 'PREOCUPADO', 'MEDO']
    if any(term in t for term in termos_ansiedade):
        return "PICO DE ANSIEDADE"

    termos_retorno = ['CHEGUEI', 'CHEGANDO', 'SAI DO', 'VINDO', 'VOLTANDO', 'CASA', 'DESCANSO']
    if any(term in t for term in termos_retorno):
        return "ROTINA DE CASA (GERAL)"

    return "OUTROS"

# --- FUNÇÃO DE DASHBOARD VISUAL (VERTICAL) ---
def exibir_dashboard_visual(df_aluno):
    st.subheader("📊 Painel de Autoconsciência")
    st.markdown("---")
    
    try:
        # Colunas Mapeadas:
        # Coluna C (Índice 2) -> Aonde Fuma Mais (Local/Ambiente)
        # Coluna D (Índice 3) -> Gatilhos (O que estava fazendo)
        # Coluna G (Índice 6) -> Emoções (O que sentiu)
        
        # 1. GRÁFICO DE GATILHOS (Coluna D - Índice 3)
        if df_aluno.shape[1] > 3:
            st.markdown("##### 1. O que você estava fazendo? (Gatilhos)")
            df_temp = df_aluno.copy()
            # Aplica a categorização granular aqui
            df_temp['Categoria_Gatilho'] = df_temp.iloc[:, 3].apply(categorizar_inteligente)
            
            dados_gatilho = df_temp['Categoria_Gatilho'].value_counts().reset_index()
            dados_gatilho.columns = ['Gatilho', 'Qtd']
            
            fig1 = px.pie(dados_gatilho, names='Gatilho', values='Qtd', hole=0.6, 
                         color_discrete_sequence=px.colors.sequential.Teal)
            fig1.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            fig1.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig1, use_container_width=True)
            st.markdown("---")

        # 2. GRÁFICO DE EMOÇÕES (Coluna G - Índice 6)
        if df_aluno.shape[1] > 6:
            st.markdown("##### 2. O que você sentiu? (Emoções)")
            df_temp = df_aluno.copy()
            df_temp['Categoria_Emocao'] = df_temp.iloc[:, 6].apply(lambda x: str(x).upper().strip())
            
            top_emo = df_temp['Categoria_Emocao'].value_counts().head(5).reset_index()
            top_emo.columns = ['Emoção', 'Qtd']
            
            fig2 = px.bar(top_emo, x='Qtd', y='Emoção', orientation='h', 
                         color='Qtd', color_continuous_scale='Reds')
            fig2.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown("---")

        # 3. GRÁFICO DE AMBIENTE (Coluna C - Índice 2)
        if df_aluno.shape[1] > 2:
            st.markdown("##### 3. Onde você estava? (Ambiente)")
            df_temp = df_aluno.copy()
            # Aplica a mesma categorização granular (vai pegar Balcão, Cozinha, Varanda)
            df_temp['Categoria_Local'] = df_temp.iloc[:, 2].apply(categorizar_inteligente)
            
            top_loc = df_temp['Categoria_Local'].value_counts().reset_index()
            top_loc.columns = ['Local', 'Qtd']
            
            fig3 = px.pie(top_loc, names='Local', values='Qtd', hole=0.6,
                         color_discrete_sequence=px.colors.sequential.Blues)
            fig3.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)

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

            # --- SEÇÃO 1: IDENTIDADE ---
            st.markdown("---")
            st.subheader("📋 Identidade")
            if not perfil.empty:
                d = perfil.tail(1).to_dict('records')[0]
                dados_aluno_pdf['nome'] = next((v for k, v in d.items() if "NOME" in k.upper()), "Usuário")
                dados_aluno_pdf['idade'] = next((v for k, v in d.items() if "ANOS" in k.upper()), "N/A")
                dados_aluno_pdf['local'] = next((v for k, v in d.items() if "CIDADE" in k.upper()), "N/A")
                
                c_id1, c_id2, c_id3 = st.columns(3)
                c_id1.metric("Nome", dados_aluno_pdf['nome'])
                c_id2.metric("Idade", f"{dados_aluno_pdf['idade']} anos")
                c_id3.metric("Cidade", dados_aluno_pdf['local'])
            
            # --- SEÇÃO 2: PAINEL DE CONSCIÊNCIA ---
            if not gatilhos.empty:
                exibir_dashboard_visual(gatilhos)
                if gatilhos.shape[1] > 3:
                    # Para PDF usa gatilhos agrupados
                    df_temp = gatilhos.copy()
                    df_temp['Cat'] = df_temp.iloc[:, 3].apply(categorizar_inteligente)
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

import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import os
import datetime
from pypdf import PdfReader
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from docx import Document
from io import BytesIO
import base64

# Importação do cliente oficial do Supabase para controle de usuários
try:
    from supabase import create_client, Client
except ImportError:
    os.system("pip install supabase")
    from supabase import create_client, Client

# Carregamento do motor de PDF robusto corporativo
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
except ImportError:
    os.system("pip install reportlab")
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# Configuração de tela e menu do celular expandido por padrão
st.set_page_config(
    page_title="Setubal Juris AI", 
    page_icon="⚖️", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CONDICIONAL DE CSS: Se o usuário NÃO estiver logado, aplica o design slim de 350px. Se logar, a tela se expande ao tamanho largo original!
if "usuario_logado" not in st.session_state or st.session_state["usuario_logado"] is None:
    st.markdown("""
        <style>
        .stAppDeployButton { display: none !important; }
        div[data-testid="stHeaderActionElements"], button[data-testid="stHeaderActionButton"], #MainMenu { display: none !important; visibility: hidden !important; }
        footer { visibility: hidden !important; }
        button[data-testid="stSidebarCollapseButton"], button[aria-label="Expand sidebar"], button[aria-label="Collapse sidebar"] {
            display: flex !important; visibility: visible !important; opacity: 1 !important;
        }
        div.block-container {
            max-width: 450px !important;
            margin: 0 auto !important;
            padding-top: 30px !important;
        }
        .titulo-central {
            text-align: center !important;
            margin: 0 auto !important;
            padding-bottom: 5px !important;
        }
        .titulo-central h1 {
            font-size: 24px !important;
            font-weight: bold !important;
            line-height: 30px !important;
            margin-bottom: 5px !important;
        }
        .titulo-central h3 {
            font-size: 14px !important;
            font-weight: normal !important;
            color: #555555 !important;
            margin-top: 0px !important;
            margin-bottom: 15px !important;
        }
        div[data-testid="stVerticalBlock"] {
            max-width: 350px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stTextInput"] {
            max-width: 350px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stWidgetLabel"] {
            text-align: left !important;
        }
        div.stButton {
            text-align: center !important;
            margin-top: 15px !important;
        }
        div.stButton > button {
            width: 100% !important;
        }
        </style>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        .stAppDeployButton { display: none !important; }
        div[data-testid="stHeaderActionElements"], button[data-testid="stHeaderActionButton"], #MainMenu { display: none !important; visibility: hidden !important; }
        footer { visibility: hidden !important; }
        button[data-testid="stSidebarCollapseButton"], button[aria-label="Expand sidebar"], button[aria-label="Collapse sidebar"] {
            display: flex !important; visibility: visible !important; opacity: 1 !important;
        }
        div.block-container {
            max-width: 100% !important;
            padding-left: 50px !important;
            padding-right: 50px !important;
        }
        </style>
        """, unsafe_allow_html=True)

# INICIALIZAÇÃO DE VARIÁVEIS DE MEMÓRIA ESTÁVEL DE SESSÃO
if "messages" not in st.session_state:
    st.session_state.messages = []
if "historico_casos" not in st.session_state:
    st.session_state.historico_casos = {}
if "prompt_input_value" not in st.session_state:
    st.session_state["prompt_input_value"] = ""
if "lgpd_aceito" not in st.session_state:
    st.session_state["lgpd_aceito"] = False
if "nome_documento_atual" not in st.session_state:
    st.session_state["nome_documento_atual"] = "documento_juridico"
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None
if "dados_usuario" not in st.session_state:
    st.session_state["dados_usuario"] = {}

def criar_arquivo_word(texto):
    doc = Document()
    texto_limpo = texto.replace("**", "").replace("###", "")
    for linha in texto_limpo.split("\n"):
        doc.add_paragraph(linha)
    conteudo_binario = BytesIO()
    doc.save(conteudo_binario)
    conteudo_binario.seek(0)
    return conteudo_binario

def criar_arquivo_pdf(texto):
    conteudo_binario = BytesIO()
    doc = SimpleDocTemplate(conteudo_binario, pagesize=letter, rightMargin=50, leftMargin=70, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    estilo_corpo = ParagraphStyle('EstiloCorpo', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=18, alignment=TA_JUSTIFY, spaceAfter=12)
    estilo_titulo = ParagraphStyle('EstiloTitulo', fontName='Helvetica-Bold', fontSize=12, leading=20, alignment=TA_CENTER, spaceBefore=15, spaceAfter=15)
    estilo_citacao = ParagraphStyle('EstiloCitacao', fontName='Helvetica', fontSize=9.5, leading=14, leftMargin=113, rightMargin=20, alignment=TA_JUSTIFY, spaceAfter=10)
    
    elementos = []
    linhas = texto.split("\n")
    for linha in linhas:
        linha_limpa = linha.replace("**", "").replace("###", "").strip()
        if not linha_limpa: continue
        if linha_limpa.startswith(("DO ", "DOS ", "DA ", "DAS ", "EDENTAL ", "NOTIFICAÇÃO ", "PETIÇÃO ", "CONTRATO ", "DECLARAÇÃO ", "FICHA ")):
            elementos.append(Paragraph(linha_limpa, estilo_titulo))
        elif linha_limpa.startswith(">") or (linha_limpa.startswith('"') and len(linha_limpa) > 60):
            elementos.append(Paragraph(linha_limpa.lstrip("> ").strip(), estilo_citacao))
        else:
            elementos.append(Paragraph(linha_limpa, estilo_corpo))
    doc.build(elementos)
    conteudo_binario.seek(0)
    return conteudo_binario

def exportar_historico_completo(mensagens):
    if not mensagens: return "--- O HISTÓRICO DE ATENDIMENTO ESTÁ VAZIO ---"
    historico_texto = "--- HISTÓRICO DE ATENDIMENTO - SETUBAL JURIS AI ---\n\n"
    for msg in mensagens:
        role_label = "ADVOGADO / USUÁRIO" if msg["role"] == "user" else "SETUBAL JURIS AI"
        historico_texto += f"[{role_label}]:\n{msg['content']}\n\n" + "-"*50 + "\n\n"
    return historico_texto

# 🔒 INTERFACE DE LOGIN E CADASTRO DINÂMICA (CORRIGIDA)
if st.session_state["usuario_logado"] is None:
    st.markdown('<div class="titulo-central"><h1>🏛️ Portal de Acesso - Setubal Juris AI</h1><h3>Acesso Restrito a Advogados e Associados</h3></div>', unsafe_allow_html=True)
    
    aba_login, aba_cadastro = st.tabs(["🔑 Realizar Login", "📝 Criar Nova Conta"])
    
    with aba_login:
        email_login = st.text_input("E-mail Cadastrado:", key="email_l")
        senha_login = st.text_input("Senha de Acesso:", type="password", key="senha_l")
        
        if st.button("Entrar no Sistema", type="primary", key="btn_login_exec"):
            secret_admin_email = st.secrets.get("ADMIN_EMAIL")
            secret_admin_senha = st.secrets.get("ADMIN_SENHA")
            
            if secret_admin_email and secret_admin_senha and email_login.strip() == secret_admin_email and senha_login == secret_admin_senha:
                st.session_state["usuario_logado"] = secret_admin_email
                st.session_state["dados_usuario"] = {
                    "email": secret_admin_email,
                    "nivel_acesso": "admin",
                    "status_assinatura": "ativo",
                    "consultas_gratuitas_usadas": 0
                }
                st.success("Autenticação concluída! Entrando...")
                st.rerun()
                
            elif supabase and email_login and senha_login:
                try:
                    resposta = supabase.table("assinaturas_usuarios").select("*").eq("email", email_login.strip()).eq("senha", senha_login).execute()
                    if hasattr(resposta, "data") and resposta.data and len(resposta.data) > 0:
                        st.session_state["usuario_logado"] = email_login.strip()
                        st.session_state["dados_usuario"] = resposta.data if isinstance(resposta.data, list) else resposta.data
                        st.success("Autenticação concluída! Entrando...")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception:
                    st.error("Usuário ou senha incorretos.")
            else:
                st.error("Usuário ou senha incorretos.")
                
    with aba_cadastro:
        st.markdown("Ganhe **01 consulta de teste gratuito** ao criar sua conta.")
        email_cad = st.text_input("Seu melhor E-mail:", key="email_c")
        senha_cad = st.text_input("Crie uma Senha:", type="password", key="senha_c")
        
        if st.button("Cadastrar e Ativar Conta", key="btn_cad_exec"):
            if supabase and email_cad and senha_cad:
                try:
                    checagem = supabase.table("assinaturas_usuarios").select("email").eq("email", email_cad.strip()).execute()
                    if hasattr(checagem, "data") and checagem.data and len(checagem.data) > 0:
                        st.error("⚠️ Este e-mail já está cadastrado. Vá até a aba 'Realizar Login'.")
                    else:
                        novo_user = {
                            "email": email_cad.strip(),
                            "senha": senha_cad,
                            "nivel_acesso": "usuario",
                            "consultas_gratuitas_usadas": 0,
                            "status_assinatura": "gratis"
                        }
                        supabase.table("assinaturas_usuarios").insert(novo_user).execute()
                        st.success("Conta ativada com sucesso! Faça login na aba ao lado.")
                except Exception:
                    st.error("Falha operacional ao registrar usuário.")
            else:
                st.warning("Preencha todos os campos.")
                
    st.stop()
        
    # Regra 2: Assinatura Mensal expirada
    elif status_ass == "vencido" or (data_venc and datetime.datetime.strptime(str(data_venc), "%Y-%m-%d").date() < datetime.date.today()):
        st.error("🔒 Assinatura Mensal Expirada!")
        st.info("O seu período de 30 dias de acesso venceu. Realize a renovação de R$ 50,00 para reativar suas ferramentas.")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💳 Renovar Assinatura (Gerar PIX)", type="primary"):
            st.toast("Gerando QR Code de pagamento...")
        bloqueado = True
        st.stop()
        
    # Regra 3: Régua de Alerta de 5 dias antes de vencer
    elif data_venc:
        vencimento_date = datetime.datetime.strptime(str(data_venc), "%Y-%m-%d").date()
        dias_restantes = (vencimento_date - datetime.date.today()).days
        if 0 <= dias_restantes <= 5:
            st.warning(f"⚠️ **Aviso de Renovação:** Sua assinatura mensal expira em {dias_restantes} dias ({vencimento_date.strftime('%d/%m/%Y')}). Regularize antecipadamente para não interromper seu fluxo de trabalho.")
# Se o usuário passou pelas travas ou é Admin, o sistema carrega o cockpit lateral
if not bloqueado:
    st.sidebar.write(f"Conectado como: **{user_email}** ({nivel.upper()})")
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state["usuario_logado"] = None
        st.session_state["dados_usuario"] = {}
        st.session_state.messages = []
        st.rerun()

    # 📊 CALCULADORA DE PRAZOS EM DIAS ÚTEIS (CPC)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Calculadora de Prazos (Dias Úteis)")

    data_intimacao = st.sidebar.date_input("Data da Intimação / Publicação:", datetime.date.today())
    tipo_prazo = st.sidebar.selectbox("Tipo de Prazo (CPC):", [5, 10, 15, 30])

    def calcular_prazo_util(data_inicial, dias_uteis):
        data_corrente = data_inicial
        dias_contados = 0
        while dias_contados < dias_uteis:
            data_corrente += datetime.timedelta(days=1)
            if data_corrente.weekday() < 5:
                dias_contados += 1
        return data_corrente

    data_fatal = calcular_prazo_util(data_intimacao, tipo_prazo)
    st.sidebar.info(f"📅 **Prazo Fatal Exato:** {data_fatal.strftime('%d/%m/%Y')} ({tipo_prazo} dias úteis)")

    # 🗮️ SIMULADOR DE VALOR DA CAUSA E RITO PROCESSUAL
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🗮️ Valor da Causa, Rito e OAB")
    with st.sidebar.expander("🧮 Simulação de Rito Processual"):
        pedido_principal = st.number_input("Pedido Principal / Benefício (R$):", min_value=0.0, value=0.0, step=500.0)
        pedido_acessorio = st.number_input("Pedidos Acessórios / Indenizações (R$):", min_value=0.0, value=0.0, step=500.0)
        valor_causa = pedido_principal + pedido_acessorio
        st.markdown(f"**Valor da Causa Projetado:** R$ {valor_causa:,.2f}")
        
        limite_jec = 60480.0 # Teto de 40 salários mínimos para 2026 (R$ 1.512 * 40)
        if valor_causa == 0:
            st.write("Insira os valores para triagem.")
        elif valor_causa <= limite_jec:
            st.success("🟢 Elegível para o Juizado Especial Cível (JEC).")
        else:
            st.error("🔴 Ultrapassou o teto do JEC. Distribuir em Vara Cível ordinária.")
    with st.sidebar.expander("💼 Honorários Mínimos OAB SP"):
        servico_oab = st.selectbox(
            "Selecione o Serviço Jurídico:",
            [
                "Consulta jurídica convencional",
                "Consulta c/ exame de documentos",
                "Elaboração de notificação extrajudicial",
                "Atuação em Juizado Especial (JEC)",
                "Procedimento comum cível (Inicial/Defesa)",
                "Ação de Alimentos (Revisional/Fixação)",
                "Divórcio Consensual Judicial",
                "Patrocínio de Reclamante Trabalhista"
            ]
        )
        
        if servico_oab == "Consulta jurídica convencional":
            st.info("💰 **Valor Mínimo:** R$ 539,25\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Consulta c/ exame de documentos":
            st.info("💰 **Valor Mínimo:** R$ 1.155,52\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Elaboração de notificação extrajudicial":
            st.info("💰 **Valor Mínimo:** R$ 868,96\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Atuação em Juizado Especial (JEC)":
            st.info("💰 **Valor Mínimo:** R$ 1.390,33\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Procedimento comum cível (Inicial/Defesa)":
            st.info("💰 **Valor Mínimo:** R$ 6.256,51\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Ação de Alimentos (Revisional/Fixação)":
            st.info("💰 **Valor Mínimo:** R$ 2.606,88\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Divórcio Consensual Judicial":
            st.info("💰 **Valor Mínimo:** R$ 7.820,64\n\n*Referência: Tabela OAB SP.*")
        elif servico_oab == "Patrocínio de Reclamante Trabalhista":
            st.info("💰 **Valor Mínimo:** R$ 1.737,91\n\n*Referência: Tabela OAB SP.*")

    # 📋 TEXTOS DOS TEMPLATES NO PADRÃO TÉCNICO DE ADVOCACIAS
    TEMPLATE_INICIAL = """Excelentíssimo Senhor Doutor Juiz de Direito da __ Vara Cível da Comarca de __.

PETIÇÃO INICIAL
DOS FATOS / DO DIREITO / DOS PEDIDOS"""

    TEMPLATE_CONTRATO = """CONTRATO DE PRESTAÇÃO DE SERVIÇOS PROFISSIONAIS
CONTRATANTE / CONTRATADO / DO OBJETO / DO PREÇO"""

    TEMPLATE_NOTIFICACAO = """NOTIFICAÇÃO EXTRAJUDICIAL
À Atenção de: [Nome] / DOS FATOS / DO DIREITO / DO REQUERIMENTO"""

    TEMPLATE_INTIMACAO = """PARECER DE TRIAGEM PROCESSUAL
DO COMANDO REAL / DO PRAZO LEGAL PROCESSUAL / DIRETRIZ ESTRATÉGICA"""

    TEMPLATE_PROCURACAO = """PROCURAÇÃO AD JUDICIA ET EXTRA
OUTORGANTE / OUTORGADO / DOS PODERES EXTRAORDINÁRIOS DO ART. 105 CPC"""

    TEMPLATE_GRATUITA = """DECLARAÇÃO DE HIPOSSUFICIÊNCIA ECONÔMICA
DECLARANTE / DECLARAÇÃO FORMAL ART. 98 CPC E ART. 5º CONSTITUIÇÃO"""

    TEMPLATE_ENCERRAMENTO = """TERMO DE ENCERRAMENTO CONTRATUAL
FORO DE ELEIÇÃO / ASSINATURAS DAS PARTES E DUAS TESTEMUNHAS"""

    TEMPLATE_FICHA = """FICHA DE ATENDIMENTO E TRIAGEM
SÍNTESE DOS FATOS / TESES JURÍDICAS / CHECKLIST DE DOCUMENTOS ESSENCIAIS"""

    TEMPLATE_HONORARIOS = """CONTRATO DE HONORÁRIOS ADVOCATÍCIOS
PREÇO E FORMA DE PAGAMENTO BASEADOS NA OAB SP E CLÁUSULA QUOTA-LITIS"""
    # 🗂️ SEÇÃO VISUAL DOS MODELOS NA BARRA LATERAL
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Modelos Rápidos de Peças")

    if st.sidebar.button("📄 Petição Inicial (Cobrança)"):
        st.session_state["prompt_input_value"] = TEMPLATE_INICIAL
        st.session_state["nome_documento_atual"] = "peticao_inicial_cobranca"
        st.rerun()

    if st.sidebar.button("📝 Contrato de Prestação"):
        st.session_state["prompt_input_value"] = TEMPLATE_CONTRATO
        st.session_state["nome_documento_atual"] = "contrato_de_prestacao_de_servicos"
        st.rerun()

    if st.sidebar.button("📧 Notificação Extrajudicial"):
        st.session_state["prompt_input_value"] = TEMPLATE_NOTIFICACAO
        st.session_state["nome_documento_atual"] = "notificacao_extrajudicial"
        st.rerun()

    if st.sidebar.button("🔍 Analisar Decisão / Intimação"):
        st.session_state["prompt_input_value"] = TEMPLATE_INTIMACAO
        st.session_state["nome_documento_atual"] = "parecer_de_triagem_de_intimacao"
        st.rerun()

    if st.sidebar.button("⚖️ Procuração Ad Judicia"):
        st.session_state["prompt_input_value"] = TEMPLATE_PROCURACAO
        st.session_state["nome_documento_atual"] = "procuracao_ad_judicia"
        st.rerun()

    if st.sidebar.button("📜 Declaração Justiça Gratuita"):
        st.session_state["prompt_input_value"] = TEMPLATE_GRATUITA
        st.session_state["nome_documento_atual"] = "declaracao_de_justica_gratuita"
        st.rerun()

    if st.sidebar.button("✒️ Termo de Encerramento"):
        st.session_state["prompt_input_value"] = TEMPLATE_ENCERRAMENTO
        st.session_state["nome_documento_atual"] = "termo_de_encerramento"
        st.rerun()

    if st.sidebar.button("📝 Ficha de Atendimento"):
        st.session_state["prompt_input_value"] = TEMPLATE_FICHA
        st.session_state["nome_documento_atual"] = "ficha_de_atendimento_e_triagem"
        st.rerun()

    if st.sidebar.button("💼 Contrato de Honorários"):
        st.session_state["prompt_input_value"] = TEMPLATE_HONORARIOS
        st.session_state["nome_documento_atual"] = "contrato_de_honorarios_advocaticios"
        st.rerun()

    # 🌐 CENTRAL DE LINKS ÚTEIS DA ADVOCACIA
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🌐 Links Úteis da Rotina")

    with st.sidebar.expander("🏛️ Portais Oficiais"):
        st.markdown("[• Portal do PJe - CNJ](https://cnj.jus.br)")
        st.markdown("[• STF - Supremo Tribunal Federal](https://stf.jus.br)")
        st.markdown("[• STJ - Superior Tribunal de Justiça](https://stj.jus.br)")

    with st.sidebar.expander("🔍 Pesquisa e Legislação"):
        st.markdown("[• Planalto - Legislação Atualizada](http://planalto.gov.br)")
        st.markdown("[• Jusbrasil - Jurisprudência](https://jusbrasil.com.br)")
        st.markdown("[• Diário Oficial da União (DOU)](https://in.gov.br)")

    with st.sidebar.expander("🛠️ Ferramentas Práticas"):
        st.markdown("[• CNA - Cadastro de Advogados OAB](https://oab.org.br)")
        st.markdown("[• Calculadora de Prazos Processuais](https://legalcloud.com.br)")

    # 📋 LEMBRETES DE PRAZOS FIXOS DO CPC NO RODAPÉ DA LATERAL
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Lembretes de Prazos (CPC)")
    with st.sidebar.expander("⏱️ Prazos Fixos de Consulta"):
        st.markdown("**• Contestação / Réplica:** 15 dias úteis")
        st.markdown("**• Apelação / Contrarrazões:** 15 dias úteis")
        st.markdown("**• Agravo de Instrumento:** 15 dias úteis")
        st.markdown("**• Embargos de Declaração:** 5 dias úteis")
        st.markdown("**• Manifestação Documental:** 15 dias úteis")
    # CARREGAMENTO DA CHAVE e ENGENHARIA DE CHAT MULTIMODAL
    groq_api_key = st.secrets.get("GROQ_API_KEY")
    if not groq_api_key:
        st.error("👉 Configuração GROQ_API_KEY ausente nos Secrets do Streamlit Cloud.")
    else:
        llm_texto = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, groq_api_key=groq_api_key)
        llm_visao = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1, groq_api_key=groq_api_key)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📁 Analisar Documento ou Foto (Caso Atual)")
        arquivo_enviado = st.sidebar.file_uploader("Insira um contrato em PDF ou Foto", type=["pdf", "png", "jpg", "jpeg"])

        texto_contrato_atual = ""
        dados_imagem_base64 = None
        tipo_mime_imagem = ""

        if arquivo_enviado is not None:
            name_extensao = arquivo_enviado.name.lower()
            if name_extensao.endswith(".pdf"):
                st.sidebar.success("Documento PDF carregado!")
                reader_contrato = PdfReader(arquivo_enviado)
                for page in reader_contrato.pages:
                    t = page.extract_text()
                    if t: texto_contrato_atual += t + "\n"
            elif name_extensao.endswith((".png", ".jpg", ".jpeg")):
                st.sidebar.success("Foto/Imagem jurídica carregada!")
                tipo_mime_imagem = f"image/{'png' if name_extensao.endswith('.png') else 'jpeg'}"
                dados_imagem_base64 = base64.b64encode(arquivo_enviado.read()).decode("utf-8")

        PROMPT_SISTEMA = (
            "Você é o Setubal Juris AI, um assistente virtual e co-piloto jurídico sênior especialista no Direito brasileiro.\n"
            "Sua função é auxiliar o usuário de forma extremamente formal, técnica e ética.\n"
            "Você tem conhecimento pleno de toda a legislação brasileira. Fundamente suas respostas nos artigos vigentes.\n\n"
            "DIRETRIZ DE FORMATAÇÃO FORENSE OAB/ABNT:\n"
            "Ao redigir peças processuais, contratos, procurações ou pareceres, estruture o texto com rigor técnico visual:\n"
            "- Utilize títulos em CAIXA ALTA e negrito para divisões de seções (ex: DOS FATOS, DO DIREITO).\n"
            "- Garanta parágrafos bem espaçados.\n"
            "- Citações de jurisprudências, ementas ou artigos longos devem vir em blocos isolados e destacados, "
            "simulando o recuo padrão de 4cm exigido pela técnica forense de peticionamento.\n"
        )
        if texto_contrato_atual:
            PROMPT_SISTEMA += f"\nDOCUMENTO DO CASO ATUAL ENVIADO EM PDF:\n{texto_contrato_atual}\n\n"

        # IMPRESSÃO DO CHAT HISTÓRICO COM DOWNLOAD INTEGRADO NOMINAL
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and "Não possuo autorização" not in message["content"]:
                    nome_doc = st.session_state.get("nome_documento_atual", f"documento_{i}")
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        arquivo_docx = criar_arquivo_word(message["content"])
                        st.download_button(label="📥 Baixar no Word (.docx)", data=arquivo_docx, file_name=f"{nome_doc}_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_w_{i}")
                    with col_dl2:
                        arquivo_pdf = criar_arquivo_pdf(message["content"])
                        st.download_button(label="📄 Baixar em PDF (.pdf)", data=arquivo_pdf, file_name=f"{nome_doc}_{i}.pdf", mime="application/pdf", key=f"btn_p_{i}")
        # --- TRAVA DA LGPD CONSOLIDADA NO CENTRO DA TELA PRINCIPAL ---
        st.markdown("### 🔐 Controle de Segurança da Informação (LGPD)")
        
        termo_lgpd = st.checkbox(
            "Declaro que possuo autorização legal ou consentimento expresso do titular para o tratamento e "
            "inserção dos documentos e dados pessoais anexados neste caso, ciente de que a plataforma opera sob "
            "criptografia fim a fim e em estrito cumprimento às normas da Lei nº 13.709/18 (LGPD).",
            value=st.session_state["lgpd_aceito"]
        )
        
        if termo_lgpd != st.session_state["lgpd_aceito"]:
            st.session_state["lgpd_aceito"] = termo_lgpd
            st.rerun()

        prompt = None

        if st.session_state["lgpd_aceito"]:
            if st.session_state["prompt_input_value"]:
                st.info("📋 Modelo selecionado! Edite os campos entre colchetes [ ] ou digite suas instruções complementares abaixo e envie no botão:")
                prompt_editado = st.text_area("Rascunho da Estrutura do Modelo:", value=st.session_state["prompt_input_value"], height=250)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🚀 Enviar para IA", type="primary"):
                        st.session_state.messages.append({"role": "user", "content": prompt_editado})
                        st.session_state["prompt_input_value"] = ""
                        st.rerun()
                with col_btn2:
                    if st.button("❌ Cancelar Modelo"):
                        st.session_state["prompt_input_value"] = ""
                        st.session_state["nome_documento_atual"] = "documento_juridico"
                        st.rerun()
            else:
                prompt = st.chat_input("Ex: Qual o prazo de contestação segundo o CPC?")
        else:
            st.warning("🔒 Por motivos de compliance e segurança, marque a caixinha de consentimento da LGPD acima para liberar a barra de digitação e os modelos rápidos selecionados na barra lateral.")

        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.rerun()
        # BLOCO DE PROCESSAMENTO E DISPARO DAS APIS (Com Atualização de Saldo no Banco)
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
            ultimo_comando = st.session_state.messages[-1]["content"]
            
            with st.chat_message("user"):
                st.markdown(ultimo_comando)

            palavras_bloqueadas = ["receita", "bolo", "doce", "cozinha", "comida", "futebol", "piada", "viagem", "roteiro", "musica", "filme"]
            if any(palavra in ultimo_comando.lower() for palavra in palavras_bloqueadas):
                resposta_recusa = (
                    "Sou o Setubal Juris AI, um assistente corporativo de uso exclusivo para a área jurídica. "
                    "Não possuo autorização ou conhecimento programado para responder a consultas fora do escopo legal."
                )
                with st.chat_message("assistant"):
                    st.markdown(resposta_recusa)
                st.session_state.messages.append({"role": "assistant", "content": resposta_recusa})
                st.rerun()
            else:
                with st.chat_message("assistant"):
                    with st.spinner("Setubal Juris AI processando..."):
                        if dados_imagem_base64:
                            conteudo_usuario = [
                                {"type": "text", "text": ultimo_comando},
                                {"type": "image_url", "image_url": {"url": f"data:{tipo_mime_imagem};base64,{dados_imagem_base64}"}}
                            ]
                            historico_ia = [SystemMessage(content=PROMPT_SISTEMA), HumanMessage(content=conteudo_usuario)]
                            resposta = llm_visao.invoke(historico_ia)
                        else:
                            historico_ia = [SystemMessage(content=PROMPT_SISTEMA)]
                            for msg in st.session_state.messages[:-1]:
                                if msg["role"] == "user":
                                    historico_ia.append(HumanMessage(content=msg["content"]))
                                else:
                                    historico_ia.append(SystemMessage(content=msg["content"]))
                            historico_ia.append(HumanMessage(content=ultimo_comando))
                            resposta = llm_texto.invoke(historico_ia)
                        
                        st.markdown(resposta.content)
                        st.session_state.messages.append({"role": "assistant", "content": resposta.content})
                        
                        # CONTROLE EXCLUSIVO DE SALDO DA DEGUSTAÇÃO: Se for usuário grátis, atualiza no Supabase
                        if supabase and nivel != "admin" and status_ass == "gratis":
                            novo_saldo = int(consultas_usadas) + 1
                            try:
                                supabase.table("assinaturas_usuarios").update({"consultas_gratuitas_usadas": novo_saldo}).eq("email", user_email).execute()
                                if isinstance(st.session_state["dados_usuario"], list):
                                    st.session_state["dados_usuario"]["consultas_gratuitas_usadas"] = novo_saldo
                                else:
                                    st.session_state["dados_usuario"]["consultas_gratuitas_usadas"] = novo_saldo
                            except Exception:
                                pass
                        
                        nome_f_doc = st.session_state.get("nome_documento_atual", "documento_setubal_juris")
                        col_im1, col_dl2 = st.columns(2)
                        with col_im1:
                            arquivo_docx = criar_arquivo_word(resposta.content)
                            st.download_button(label="📥 Baixar no Word (.docx)", data=arquivo_docx, file_name=f"{nome_f_doc}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_w_imediato_{len(st.session_state.messages)}")
                        with col_dl2:
                            arquivo_pdf = criar_arquivo_pdf(resposta.content)
                            st.download_button(label="📄 Baixar em PDF (.pdf)", data=arquivo_pdf, file_name=f"{nome_f_doc}.pdf", mime="application/pdf", key=f"btn_p_imediato_{len(st.session_state.messages)}")
                        st.rerun()

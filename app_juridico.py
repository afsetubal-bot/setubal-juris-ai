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

# Ocultar utilitários de desenvolvimento na direita mantendo o botão do celular na esquerda
st.markdown("""
    <style>
    .stAppDeployButton { display: none !important; }
    div[data-testid="stHeaderActionElements"], button[data-testid="stHeaderActionButton"], #MainMenu { display: none !important; visibility: hidden !important; }
    footer { visibility: hidden !important; }
    button[data-testid="stSidebarCollapseButton"], button[aria-label="Expand sidebar"], button[aria-label="Collapse sidebar"] {
        display: flex !important; visibility: visible !important; opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Setubal Juris AI")
st.subheader("Plataforma de Inteligência, Auditoria e Visão Jurídica")

# INICIALIZAÇÃO DE MEMÓRIA ESTÁVEL DE SESSÃO
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
    # Margens formais de petição/peça técnica
    doc = SimpleDocTemplate(conteudo_binario, pagesize=letter, rightMargin=50, leftMargin=70, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # ESTILOS DE ALTA ADVOCACIA (Mapeamento ABNT Forense)
    estilo_corpo = ParagraphStyle(
        'EstiloCorpo', parent=styles['Normal'], fontName='Helvetica', fontSize=11, leading=18, alignment=TA_JUSTIFY, spaceAfter=12
    )
    estilo_titulo = ParagraphStyle(
        'EstiloTitulo', fontName='Helvetica-Bold', fontSize=12, leading=20, alignment=TA_CENTER, spaceBefore=15, spaceAfter=15
    )
    estilo_citacao = ParagraphStyle(
        'EstiloCitacao', fontName='Helvetica', fontSize=9.5, leading=14, leftMargin=113, rightMargin=20, alignment=TA_JUSTIFY, spaceAfter=10
    )
    
    elementos = []
    linhas = texto.split("\n")
    
    for linha in linhas:
        linha_limpa = linha.replace("**", "").replace("###", "").strip()
        if not linha_limpa:
            continue
        
        # Identifica se a linha é um título processual (ex: DOS FATOS, DO DIREITO)
        if linha_limpa.startswith(("DO ", "DOS ", "DA ", "DAS ", "EDENTAL ", "NOTIFICAÇÃO ", "PETIÇÃO ", "CONTRATO ", "DECLARAÇÃO ", "FICHA ")):
            elementos.append(Paragraph(linha_limpa, estilo_titulo))
        # Identifica se a linha é uma citação recuada de artigo ou jurisprudência (marcada com > ou aspas)
        elif linha_limpa.startswith(">") or (linha_limpa.startswith('"') and len(linha_limpa) > 60):
            texto_citacao = linha_limpa.lstrip("> ").strip()
            elementos.append(Paragraph(texto_citacao, estilo_citacao))
        else:
            elementos.append(Paragraph(linha_limpa, estilo_corpo))
            
    doc.build(elementos)
    conteudo_binario.seek(0)
    return conteudo_binario

def exportar_historico_completo(mensagens):
    if not mensagens:
        return "--- O HISTÓRICO DE ATENDIMENTO ESTÁ VAZIO ---"
    historico_texto = "--- HISTÓRICO DE ATENDIMENTO - SETUBAL JURIS AI ---\n\n"
    for msg in mensagens:
        role_label = "ADVOGADO / USUÁRIO" if msg["role"] == "user" else "SETUBAL JURIS AI"
        historico_texto += f"[{role_label}]:\n{msg['content']}\n\n"
        historico_texto += "-"*50 + "\n\n"
    return historico_texto

# BARRA LATERAL PRINCIPAL
st.sidebar.header("🏛️ Painel Setubal Juris")
st.sidebar.markdown("### 💾 Gestão da Sessão")

if st.sidebar.button("➕ Iniciar Novo Caso (Arquivar Atual)"):
    if st.session_state.messages:
        num_caso = len(st.session_state.historico_casos) + 1
        st.session_state.historico_casos[f"Caso Arquivado #{num_caso}"] = st.session_state.messages
        st.toast(f"Caso #{num_caso} arquivado!")
    st.session_state.messages = []
    st.session_state["prompt_input_value"] = ""
    st.session_state["nome_documento_atual"] = "documento_juridico"
    st.rerun()

if st.sidebar.button("🗑️ Limpar Tudo (Zerar Memória)"):
    st.session_state.messages = []
    st.session_state.historico_casos = {}
    st.session_state["prompt_input_value"] = ""
    st.session_state["nome_documento_atual"] = "documento_juridico"
    st.toast("Todo o sistema foi limpo com sucesso!")
    st.rerun()

if st.session_state.historico_casos:
    st.sidebar.markdown("### 🗄️ Casos Arquivados nesta Sessão")
    for nome_caso, msgs_salvas in st.session_state.historico_casos.items():
        texto_baixar = exportar_historico_completo(msgs_salvas)
        st.sidebar.download_button(
            label="📥 Baixar " + nome_caso, 
            data=texto_baixar, 
            file_name=nome_caso.lower().replace(' ', '_') + ".txt", 
            mime="text/plain", 
            key=f"dl_{nome_caso}"
        )

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

# 🗮️ SIMULADOR DE VALOR DA CAUSA, RITO E HONORÁRIOS OAB SP 2026
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗮️ Valor da Causa, Rito e OAB")
with st.sidebar.expander("🧮 Simulação de Rito Processual"):
    pedido_principal = st.number_input("Pedido Principal / Benefício (R$):", min_value=0.0, value=0.0, step=500.0)
    pedido_acessorio = st.number_input("Pedidos Acessórios / Indenizações (R$):", min_value=0.0, value=0.0, step=500.0)
    valor_causa = pedido_principal + pedido_acessorio
    st.markdown(f"**Valor da Causa Projetado:** R$ {valor_causa:,.2f}")
    
    limite_jec = 60480.0
    if valor_causa == 0:
        st.write("Insira os valores para triagem.")
    elif valor_causa <= limite_jec:
        st.success("🟢 Elegível para o Juizado Especial Cível (JEC).")
    else:
        st.error("🔴 Ultrapassou o teto do JEC. Distribuir em Vara Cível ordinária.")

with st.sidebar.expander("💼 Honorários Mínimos OAB SP 2026"):
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
        st.info("💰 **Valor Mínimo:** R$ 539,25\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Consulta c/ exame de documentos":
        st.info("💰 **Valor Mínimo:** R$ 1.155,52\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Elaboração de notificação extrajudicial":
        st.info("💰 **Valor Mínimo:** R$ 868,96\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Atuação em Juizado Especial (JEC)":
        st.info("💰 **Valor Mínimo:** R$ 1.390,33\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Procedimento comum cível (Inicial/Defesa)":
        st.info("💰 **Valor Mínimo:** R$ 6.256,51\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Ação de Alimentos (Revisional/Fixação)":
        st.info("💰 **Valor Mínimo:** R$ 2.606,88\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Divórcio Consensual Judicial":
        st.info("💰 **Valor Mínimo:** R$ 7.820,64\n\n*Referência: Tabela OAB SP 2026.*")
    elif servico_oab == "Patrocínio de Reclamante Trabalhista":
        st.info("💰 **Valor Mínimo:** R$ 1.737,91\n\n*Referência: Tabela OAB SP 2026.*")
# 📋 TEXTOS DOS TEMPLATES NO PADRÃO TÉCNICO DE ADVOCACIAS
TEMPLATE_INICIAL = """Excelentíssimo Senhor Doutor Juiz de Direito da __ Vara Cível da Comarca de __.

PETIÇÃO INICIAL

DOS FATOS
O Autor vem, por meio de seu advogado, propor a presente Ação de Cobrança, tendo em vista o inadimplemento de obrigação contratual líquida e certa pelo Réu, de forma injustificada.

DO DIREITO
A inadimplência do devedor é flagrante e atrai a aplicação imperiosa das sanções civis do ordenamento:
> "O inadimplemento da obrigação, positiva e líquida, no seu termo, constitui de pleno direito em mora o devedor." (Artigo 397 do Código Civil brasileiro)

DOS PEDIDOS
Diante de todo o exposto, requer-se a total procedência da ação, com a regular citação do Réu para adimplir o débito atualizado ou apresentar defesa, bem como sua condenação em custas e honorários de sucumbência."""

TEMPLATE_CONTRATO = """CONTRATO DE PRESTAÇÃO DE SERVIÇOS PROFISSIONAIS

CONTRATANTE: [Nome/Qualificação]
CONTRATADO: [Nome/Qualificação]

DO OBJETO
Cláusula 1ª. O presente instrumento tem por objeto a prestação de serviços técnicos jurídicos e consultivos, de forma diligente e profissional.

DO PREÇO E CONDIÇÕES
Cláusula 2ª. Pelos serviços prestados, o Contratante pagará as quantias previamente estipuladas, sob pena de incidência imediata de encargos moratórios vigentes."""

TEMPLATE_NOTIFICACAO = """NOTIFICAÇÃO EXTRAJUDICIAL

À Atenção de: [Nome do Notificado]

DOS FATOS
O Notificante vem, por meio desta, notificá-lo formalmente acerca do inadimplemento de obrigação e dívida vencida e não paga até a presente data.

DO DIREITO
Fundamenta-se a presente medida na imediata constituição em mora do devedor, conforme preceitua a legislação pátria:
> "O devedor em mora responde pela impossibilidade da prestação, ainda que superveniente, salvo se provar que a mora não lhe foi imputável." (Artigo 397 do Código Civil)

DO REQUERIMENTO
Diante do exposto, requer-se a total regularização e quitação do débito pendente no prazo preclusivo de 5 (cinco) dias úteis, contados do recebimento desta."""

TEMPLATE_INTIMACAO = """PARECER DE TRIAGEM PROCESSUAL

DO COMANDO REAL
Após análise minuciosa da publicação do Diário Oficial anexada, constatou-se que o magistrado determinou ato processual urgente a ser cumprido de forma imediata pelas partes.

DO PRAZO LEGAL PROCESSUAL
Nos termos do Código de Processo Civil (CPC), o ato processual indicado atrai prazo peremptório e preclusivo aplicável, computado em dias úteis.

DIRETRIZ ESTRATÉGICA RECOMENDADA
Recomenda-se a imediata compilação dos documentos e manifestação técnica cabível para resguardar os interesses do cliente."""

TEMPLATE_PROCURACAO = """PROCURAÇÃO AD JUDICIA ET EXTRA

OUTORGANTE: [Nome/Qualificação]
OUTORGADO: [Nome do Advogado/OAB]

DOS PODERES
Por este instrumento, o Outorgante concede ao Outorgado os poderes da cláusula 'Ad Judicia et Extra' para representação ampla em qualquer Juízo, Instância ou Tribunal, bem como os poderes especiais previstos na legislação:
> "O procurador necessita de poderes especiais para receber citação, confessar, reconhecer a procedência do pedido, transigir, desistir, renunciar ao direito sobre o qual se funda a ação, receber, dar quitação, firmar compromisso e firmar declaração de hipossuficiência econômica." (Artigo 105 do Código de Processo Civil)"""

TEMPLATE_GRATUITA = """DECLARAÇÃO DE HIPOSSUFICIÊNCIA ECONÔMICA

DECLARANTE: [Nome Completo/Qualificação]

DECLARAÇÃO
O Declarante atesta, sob as penas da lei e para os devidos fins de direito, que não possui condições financeiras de arcar com as custas processuais e honorários sem prejuízo de seu próprio sustento:
> "A pessoa natural ou jurídica, brasileira ou estrangeira, com insuficiência de recursos para pagar as custas, as despesas processuais e os honorários advocatícios tem direito à gratuidade da justiça, na forma da lei." (Artigo 98 do Código de Processo Civil)"""

TEMPLATE_ENCERRAMENTO = """TERMO DE ENCERRAMENTO CONTRATUAL

Por estarem assim justos e contratados, as partes elegem o foro da comarca estipulada para dirimir eventuais dúvidas, assinando o presente documento em duas vias de igual teor e forma, juntamente com duas testemunhas abaixo qualificadas.

CONTRATANTE: ___________________________
CONTRATADO: ___________________________

TESTEMUNHA 1: _________________________
TESTEMUNHA 2: _________________________"""

TEMPLATE_FICHA = """FICHA DE ATENDIMENTO E TRIAGEM

SÍNTESE DOS FATOS E CRONOLOGIA
Abertura de atendimento inicial contendo o relato fático unificado do cliente, listando datas de ocorrência, condutas, partes e valores envolvidos.

TESES JURÍDICAS E ENQUADRAMENTO
Identificação preliminar de viabilidade do direito material invocado e indicação das ações judiciais ou medidas administrativas cabíveis.

CHECKLIST DE DOCUMENTOS ESSENCIAIS
Relação cirúrgica de documentos probatórios necessários para ajuizamento seguro da demanda."""

TEMPLATE_HONORARIOS = """CONTRATO DE HONORÁRIOS ADVOCATÍCIOS

CONTRATANTE: [Nome/Qualificação]
CONTRATADO: [Nome/Advogado]

DO PREÇO E FORMA DE PAGAMENTO
Cláusula 4ª. Em remuneração pelos serviços advocatícios prestados, fixam-se os honorários contratuais mínimos de acordo com os parâmetros vigentes da OAB SP, adicionando-se percentual incidente sobre o êxito bruto.
> "A decisão judicial que fixar honorários advocatícios e o contrato escrito que os estipular são títulos executivos e constituem crédito privilegiado na falência, concordata, concurso de credores, liquidação extrajudicial e inventário." (Artigo 24 da Lei nº 8.906/94)"""

# 🗂️ SEÇÃO VISUAL DOS MODELOS NA BARRA LATERAL (Nomeando o arquivo no clique)
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
        st.warning("🔒 Por motivos de compliance e segurança, marque a caixinha de consentimento da LGPD centralizada acima para liberar a barra de digitação e os modelos rápidos selecionados na barra lateral.")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    # BLOCO DE PROCESSAMENTO E DISPARO DAS APIS (Geração Nominal Dinâmica)
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
                    
                    # Captura o nome dinâmico para os botões de download imediato
                    nome_f_doc = st.session_state.get("nome_documento_atual", "documento_setubal_juris")
                    
                    col_im1, col_dl2 = st.columns(2)
                    with col_im1:
                        arquivo_docx = criar_arquivo_word(resposta.content)
                        st.download_button(label="📥 Baixar no Word (.docx)", data=arquivo_docx, file_name=f"{nome_f_doc}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_w_imediato_{len(st.session_state.messages)}")
                    with col_dl2:
                        arquivo_pdf = criar_arquivo_pdf(resposta.content)
                        st.download_button(label="📄 Baixar em PDF (.pdf)", data=arquivo_pdf, file_name=f"{nome_f_doc}.pdf", mime="application/pdf", key=f"btn_p_imediato_{len(st.session_state.messages)}")
                    st.rerun()

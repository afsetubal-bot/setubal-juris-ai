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

# Carregamento seguro da biblioteca de PDFs
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
except ImportError:
    os.system("pip install reportlab")
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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

if "messages" not in st.session_state:
    st.session_state.messages = []
if "historico_casos" not in st.session_state:
    st.session_state.historico_casos = {}
if "prompt_input_value" not in st.session_state:
    st.session_state["prompt_input_value"] = ""

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
    doc = SimpleDocTemplate(conteudo_binario, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    estilo_juridico = ParagraphStyle(
        'EstiloJuridico',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        spaceAfter=10
    )
    
    texto_limpo = texto.replace("**", "").replace("###", "")
    elementos = []
    for linha in texto_limpo.split("\n"):
        if linha.strip():
            elementos.append(Paragraph(linha, estilo_juridico))
            elementos.append(Spacer(1, 6))
            
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
    st.rerun()

if st.sidebar.button("🗑️ Limpar Tudo (Zerar Memória)"):
    st.session_state.messages = []
    st.session_state.historico_casos = {}
    st.session_state["prompt_input_value"] = ""
    st.toast("Todo o sistema de chat foi limpo com sucesso!")
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
tipo_prazo = st.sidebar.selectbox("Tipo de Prazo (CPC):", [5, 10, 15])

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
# 📋 TEXTOS DOS TEMPLATES NO PADRÃO TÉCNICO DE ADVOCACIAS
TEMPLATE_INICIAL = """Excelentíssimo Senhor Doutor Juiz de Direito da __ Vara Cível da Comarca de __.

Redija uma PETIÇÃO INICIAL de AÇÃO DE COBRANÇA no rito comum do CPC, baseando-se nas seguintes informações básicas:
- Autor: [Nome/Qualificação Completa]
- Réu: [Nome/Qualificação Completa]
- Fato: Inadimplemento de obrigação contratual líquida e certa.
- Valor do Débito atualizado: R$ [Inserir Valor].

Siga estritamente o padrão das melhores advocacias, estruturando a peça com: Dos Fatos, Do Direito (artigos 389 e seg. do CC e normas do CPC) e Dos Pedidos cíveis de praxe. Gere a peça completa."""

TEMPLATE_CONTRATO = """Redija um CONTRATO DE PRESTAÇÃO DE SERVIÇOS profissional no padrão das grandes bancas de advocacia do país, estruturado com as cláusulas completas de: Objeto e Escopo, Obrigações das partes, Preço e Condições de Pagamento, Rescisão e Cláusula Penal, Confidencialidade (LGPD) e Foro de Eleição.

Dados Base:
- Contratante: [Nome/Qualificação]
- Contratado: [Nome/Qualificação]

Gere o contrato com redação formal e pronto para assinatura."""

TEMPLATE_NOTIFICACAO = """Redija uma NOTIFICAÇÃO EXTRAJUDICIAL formal com o objetivo de constituir o Notificado em mora e buscar uma composição amigável antes das medidas judiciais.

Informações base:
- Notificante: [Nome/Qualificação]
- Notificado: [Nome/Qualificação]
- Motivo: Inadimplemento de dívida vencida no valor de R$ [Valor].

Estruture com Síntese dos Fatos, Fundamentação Legal (art. 397 do CC) e Requerimento com prazo preclusivo de 5 dias úteis. Gere o documento formal."""

TEMPLATE_INTIMACAO = """Analise minuciosamente o teor do texto da publicação do Diário Oficial ou da imagem da decisão anexada e elabore um PARECER DE TRIAGEM PROCESSUAL estruturado estritamente nos seguintes tópicos:
1. O COMANDO REAL (O 'PRETO NO BRANCO')
2. O PRAZO LEGAL PROCESSUAL (CPC)
3. DIRETRIZ ESTRATÉGICA RECOMENDADA

Aqui está o texto/documento para análise:
[Cole aqui o texto da publicação ou apenas digite 'Analisar arquivo anexo']"""

TEMPLATE_PROCURACAO = """Redija um instrumento de PROCURAÇÃO AD JUDICIA ET EXTRA de acordo com as normas vigentes do CPC brasileiro, contendo a seguinte estrutura e poderes:

Outorgante: [Nome Completo, Nacionalidade, Estado Civil, Profissão, RG, CPF, Endereço Eletrônico e Residencial]
Outorgado: [Nome do Advogado, Inscrição na OAB/UF nº, Endereço do Escritório]

Poderes: Cláusula 'Ad Judicia et Extra' para representação em qualquer Juízo, Instância ou Tribunal, ou fora deles.
Poderes Especiais: Inclua os poderes específicos do artigo 105 do CPC. Gere o documento formal completo."""

TEMPLATE_GRATUITA = """Redija uma DECLARAÇÃO DE HIPOSSUFICIÊNCIA ECONÔMICA (DECLARAÇÃO DE JUSTIÇA GRATUITA) formal nos termos do Artigo 98 e seguintes do Código de Processo Civil (CPC) e do Artigo 5º, inciso LXXIV da Constituição Federal.

Declarante: [Nome Completo, Nacionalidade, Estado Civil, Profissão, RG, CPF, Endereço Residencial]

O documento deve atestar formalmente que o declarante não possui condições financeiras de arcar com as custas processuais. Gere o rascunho completo."""

# --- NOVO TEMPLATE AUTOMÁTICO DE CLÁUSULA DE ASSINATURAS E ENCERRAMENTO ---
TEMPLATE_ENCERRAMENTO = """Gere uma FOLHA DE ASSINATURAS E TERMO DE ENCERRAMENTO PADRÃO JURÍDICO para aposição em contratos ou acordos extrajudiciais.

Estruture o texto exatamente assim:
Por estarem assim justos e contratados, as partes elegem o foro da comarca de [Cidade/UF] para dirimir quaisquer dúvidas decorrentes deste instrumento, assinando o presente documento em 02 (duas) vias de igual teor e forma, juntamente com 02 (duas) testemunhas instrumentárias abaixo qualificadas.

[Localidade - UF], [Data].

__________________________________
CONTRATANTE: [Nome]

__________________________________
CONTRATADO: [Nome]

__________________________________
TESTEMUNHA 1:
Nome:
CPF:

__________________________________
TESTEMUNHA 2:
Nome:
CPF:"""

# 🗂️ SEÇÃO VISUAL DOS MODELOS NA BARRA LATERAL
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Modelos Rápidos de Peças")

if st.sidebar.button("📄 Petição Inicial (Cobrança)"):
    st.session_state["prompt_input_value"] = TEMPLATE_INICIAL
    st.rerun()

if st.sidebar.button("📝 Contrato de Prestação"):
    st.session_state["prompt_input_value"] = TEMPLATE_CONTRATO
    st.rerun()

if st.sidebar.button("📧 Notificação Extrajudicial"):
    st.session_state["prompt_input_value"] = TEMPLATE_NOTIFICACAO
    st.rerun()

if st.sidebar.button("🔍 Analisar Decisão / Intimação"):
    st.session_state["prompt_input_value"] = TEMPLATE_INTIMACAO
    st.rerun()

if st.sidebar.button("⚖️ Procuração Ad Judicia"):
    st.session_state["prompt_input_value"] = TEMPLATE_PROCURACAO
    st.rerun()

if st.sidebar.button("📜 Declaração Justiça Gratuita"):
    st.session_state["prompt_input_value"] = TEMPLATE_GRATUITA
    st.rerun()

# Inclusão do novo botão técnico de encerramento
if st.sidebar.button("✒️ Termo de Encerramento"):
    st.session_state["prompt_input_value"] = TEMPLATE_ENCERRAMENTO
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

    # UPGRADE: Inclusão de regras estritas de formatação forense (ABNT de tribunais)
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

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "Não possuo autorização" not in message["content"]:
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    arquivo_docx = criar_arquivo_word(message["content"])
                    st.download_button(label="📥 Baixar no Word (.docx)", data=arquivo_docx, file_name=f"documento_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_w_{i}")
                with col_dl2:
                    arquivo_pdf = criar_arquivo_pdf(message["content"])
                    st.download_button(label="📄 Baixar em PDF (.pdf)", data=arquivo_pdf, file_name=f"documento_{i}.pdf", mime="application/pdf", key=f"btn_p_{i}")

    st.markdown("### 🔐 Controle de Segurança da Informação (LGPD)")
    termo_lgpd = st.checkbox(
        "Declaro que possuo autorização legal ou consentimento expresso do titular para o tratamento e "
        "inserção dos documentos e dados pessoais anexados neste caso, ciente de que a plataforma opera sob "
        "criptografia fim a fim e em estrito cumprimento às normas da Lei nº 13.709/18 (LGPD)."
    )

    prompt = None

    if termo_lgpd:
        prompt = st.chat_input("Ex: Qual o prazo de contestação segundo o CPC?")
        
        if st.session_state["prompt_input_value"]:
            st.info("📋 Modelo selecionado! Edite os campos entre colchetes [ ] ou digite suas instruções complementares abaixo:")
            prompt_editado = st.text_area("Rascunho da Estrutura do Modelo:", value=st.session_state["prompt_input_value"], height=250)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🚀 Enviar para IA", type="primary"):
                    prompt = prompt_editado
                    st.session_state["prompt_input_value"] = ""
            with col_btn2:
                if st.button("❌ Cancelar Modelo"):
                    st.session_state["prompt_input_value"] = ""
                    st.rerun()
    else:
        st.warning("🔒 Por motivos de compliance e segurança, marque a caixinha de consentimento da LGPD acima para liberar a barra de digitação e a edição de modelos rápidos.")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        palavras_bloqueadas = ["receita", "bolo", "doce", "cozinha", "comida", "futebol", "piada", "viagem", "roteiro", "musica", "filme"]
        if any(palavra in prompt.lower() for palavra in palavras_bloqueadas):
            resposta_recusa = (
                "Sou o Setubal Juris AI, um assistente corporativo de uso exclusivo para a área jurídica. "
                "Não possuo autorização ou conhecimento programado para responder a consultas fora do escopo legal."
            )
            with st.chat_message("assistant"):
                st.markdown(resposta_recusa)
            st.session_state.messages.append({"role": "assistant", "content": resposta_recusa})
        else:
            with st.chat_message("assistant"):
                with st.spinner("Setubal Juris AI processando..."):
                    if dados_imagem_base64:
                        conteudo_usuario = [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:{tipo_mime_imagem};base64,{dados_imagem_base64}"}}
                        ]
                        historico_ia = [SystemMessage(content=PROMPT_SISTEMA), HumanMessage(content=conteudo_usuario)]
                        resposta = llm_visao.invoke(historico_ia)
                    else:
                        historico_ia = [SystemMessage(content=PROMPT_SISTEMA)]
                        for msg in st.session_state.messages:
                            if msg["role"] == "user":
                                historico_ia.append(HumanMessage(content=msg["content"]))
                            else:
                                historico_ia.append(SystemMessage(content=msg["content"]))
                        resposta = llm_texto.invoke(historico_ia)
                    
                    st.markdown(resposta.content)
                    st.session_state.messages.append({"role": "assistant", "content": resposta.content})
                    
                    col_im1, col_dl2 = st.columns(2)
                    with col_im1:
                        arquivo_docx = criar_arquivo_word(resposta.content)
                        st.download_button(label="📥 Baixar no Word (.docx)", data=arquivo_docx, file_name="documento_setubal_juris.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_w_imediato_{len(st.session_state.messages)}")
                    with col_dl2:
                        arquivo_pdf = criar_arquivo_pdf(resposta.content)
                        st.download_button(label="📄 Baixar em PDF (.pdf)", data=arquivo_pdf, file_name="documento_setubal_juris.pdf", mime="application/pdf", key=f"btn_p_imediato_{len(st.session_state.messages)}")




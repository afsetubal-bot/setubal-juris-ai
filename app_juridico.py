import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import os
from pypdf import PdfReader
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from docx import Document
from io import BytesIO
import base64

# CONFIGURAÇÃO DE TELA E MENU DO CELULAR EXPANDIDO
st.set_page_config(
    page_title="Setubal Juris AI", 
    page_icon="⚖️", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# DESIGN PREMIUM: Aplicação de Paleta Corporativa (Grafite, Dourado e Marfim)
st.markdown("""
    <style>
    /* Ocultar elementos de desenvolvimento */
    .stAppDeployButton { display: none !important; }
    div[data-testid="stHeaderActionElements"], button[data-testid="stHeaderActionButton"], #MainMenu { display: none !important; visibility: hidden !important; }
    footer { visibility: hidden !important; }
    
    /* Forçar a persistência do botão sanduíche no celular */
    button[data-testid="stSidebarCollapseButton"], button[aria-label="Expand sidebar"], button[aria-label="Collapse sidebar"] {
        display: flex !important; visibility: visible !important; opacity: 1 !important; color: #D4AF37 !important;
    }

    /* Fundo Geral do Aplicativo (Grafite Escuro) */
    .stApp {
        background-color: #1A1A1A !important;
        color: #F5F5F0 !important;
    }

    /* Estilização da Barra Lateral */
    section[data-testid="stSidebar"] {
        background-color: #121212 !important;
        border-right: 1px solid #2C2C28 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h3 {
        color: #E6E6FA !important;
    }

    /* Títulos em Dourado / Bronze Imperial */
    h1, h2, h3, .stSubheader {
        color: #D4AF37 !important;
        font-family: 'Georgia', serif !important;
        font-weight: bold !important;
    }

    /* Caixas de Mensagens do Advogado (User) */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #262626 !important;
        border-left: 4px solid #D4AF37 !important;
        border-radius: 4px !important;
        color: #F5F5F0 !important;
    }

    /* Caixas de Mensagens da IA (Assistant) */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #1E1E1E !important;
        border-left: 4px solid #4A6984 !important;
        border-radius: 4px !important;
        color: #E2E8F0 !important;
    }

    /* Customização de Botões Clicáveis */
    .stButton>button {
        background-color: #2C2C28 !important;
        color: #D4AF37 !important;
        border: 1px solid #D4AF37 !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #D4AF37 !important;
        color: #1A1A1A !important;
        border: 1px solid #D4AF37 !important;
    }
    
    /* Botões de Ação Primária (Como Enviar para IA) */
    div.stButton > button[type="submit"], button[data-baseweb="button"] {
        border-radius: 4px !important;
    }
    
    /* Caixas Sanfonadas de Links Úteis */
    .stExpander {
        background-color: #1E1E1E !important;
        border: 1px solid #2C2C28 !important;
    }
    
    /* Links Hipertexto da Barra Lateral */
    a {
        color: #D4AF37 !important;
        text-decoration: none !important;
    }
    a:hover {
        text-decoration: underline !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

def exportar_historico_completo(mensagens):
    if not mensagens:
        return "--- O HISTÓRICO DE ATENDIMENTO ESTÁ VAZIO ---"
    historico_texto = "--- HISTÓRICO DE ATENDIMENTO - SETUBAL JURIS AI ---\n\n"
    for msg in mensagens:
        role_label = "ADVOGADO / USUÁRIO" if msg["role"] == "user" else "SETUBAL JURIS AI"
        historico_texto += f"[{role_label}]:\n{msg['content']}\n\n"
        historico_texto += "-"*50 + "\n\n"
    return historico_texto

# BARRA LATERAL (No celular, inicia expandida por padrão)
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
# 📋 TEXTOS DOS TEMPLATES NO PADRÃO TÉCNICO DE ADVOCACIAS
TEMPLATE_INICIAL = """Excelentíssimo Senhor Doutor Juiz de Direito da __ Vara Cível da Comarca de __.

Redija uma PETIÇÃO INICIAL de AÇÃO DE COBRANÇA no rito comum do CPC, baseando-se nas seguintes informações básicas:
- Autor: [Nome/Qualificação Completa]
- Réu: [Nome/Qualificação Completa]
- Fato: Inadimplemento de obrigação contratual líquida e certa.
- Valor do Débito atualizado: R$ [Inserir Valor].

Siga estritamente o padrão das melhores advocacias, estruturando a peça com:
1. Endereçamento e Qualificação das partes.
2. Dos Fatos (narrativa jurídica clara).
3. Do Direito (fundamentação com os artigos 389 e seguintes do Código Civil, combinados com as normas do CPC).
4. Dos Pedidos (citação do réu, procedência total da ação, condenação em custas e honorários advocatícios de sucumbência conforme artigo 85, § 2º do CPC, e interesse na audiência de conciliação).
5. Dá-se à causa o valor de R$ [Valor].

Gere a peça completa e formal."""

TEMPLATE_CONTRATO = """Redija um CONTRATO DE PRESTAÇÃO DE SERVIÇOS profissional no padrão das grandes bancas de advocacia do país, estruturado com as seguintes cláusulas:

- Contratante: [Nome/Qualificação]
- Contratado: [Nome/Qualificação]
- Objeto do Serviço: [Descrever o serviço de forma técnica]
- Valor e Condições: [Inserir valor e datas de pagamento]

O contrato deve conter de forma minuciosa:
Cláusula 1ª - Do Objeto e Escopo.
Cláusula 2ª - Das Obrigações do Contratante.
Cláusula 3ª - Das Obrigações do Contratado.
Cláusula 4ª - Do Preço e das Condições de Pagamento (incluindo multa e juros de mora por atraso).
Cláusula 5ª - Da Rescisão e Cláusula Penal (multa rescisória profissional em caso de quebra contratual imotivada).
Cláusula 6ª - Da Confidencialidade e Sigilo das Informações (LGPD).
Cláusula 7ª - Do Foro de Eleição para dirimir litígios.

Gere o contrato com redação formal e pronto para assinatura."""

TEMPLATE_NOTIFICACAO = """À Atenção de: [Nome do Notificado] / Endereço: [Inserir Endereço].

Redija uma NOTIFICAÇÃO EXTRAJUDICIAL formal com o objetivo de constituir o Notificado em mora e buscar uma composition amigável antes das medidas judiciais.

Informações base:
- Notificante: [Nome/Qualificação]
- Motivo: Inadimplemento de [Contrato/Parcela/Dívida] vencida em [Data], no valor de R$ [Valor].

Estruture o documento exatamente assim:
1. Cabeçalho formal identificando Notificante e Notificado.
2. Da Síntese dos Fatos (origem da obrigação e descumprimento).
3. Da Fundamentação Legal (menção ao artigo 397 do Código Civil brasileiro sobre o inadimplemento da obrigação positiva e líquida).
4. Do Requerimento e Prazo (Concessão do prazo preclusivo de 5 (cinco) dias úteis para regularização do débito ou apresentação de proposta).
5. Das Advertências Finais (aviso expresso de que o silêncio ensejará a imediata propositura de Ação Judicial cabível).

Gere o documento final formal."""

TEMPLATE_INTIMACAO = """Analise minuciosamente o teor do texto da publicação do Diário Oficial ou da imagem da decisão anexada e elabore um PARECER DE TRIAGEM PROCESSUAL estruturado estritamente nos seguintes tópicos:

1. **O COMANDO REAL (O 'PRETO NO BRANCO')**: Explique em linguagem simples, direta e sem juridiquês o que o magistrado ou tribunal efetivamente determinou (ex: concedeu liminar, extinguiu sem resolução do mérito, determinou emenda, etc.).
2. **O PRAZO LEGAL PROCESSUAL (CPC)**: Identifique qual é o recurso ou a manifestação cabível contra esse despacho/decisão. Indique expressamente o prazo em dias úteis previsto no Código de Processo Civil (ex: 15 dias úteis para contestação, 15 dias úteis para apelação, 5 dias úteis para embargos de declaração, etc.).
3. **DIRETRIZ ESTRATÉGICA RECOMENDADA**: Aponte quais as melhores condutas práticas que o advogado deve adotar para resguardar o direito do cliente em face dessa decisão específica (ex: interpor agravo devido ao risco de perecimento, recolher custas pendentes, etc.).

Aqui está o texto/documento para análise:
[Cole aqui o texto da publicação ou apenas digite 'Analisar arquivo anexo']"""

# 🗂️ SEÇÃO VISUAL DOS MODELOS NA BARRA LATERAL
st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Modelos Rápidos de Peças")

if st.sidebar.button("📄 Petição Inicial (Cobrança)"):
    st.session_state["prompt_input_value"] = TEMPLATE_INICIAL
    st.rerun()

if st.sidebar.button("📝 Contrato de Prestação de Serviços"):
    st.session_state["prompt_input_value"] = TEMPLATE_CONTRATO
    st.rerun()

if st.sidebar.button("📧 Notificação Extrajudicial"):
    st.session_state["prompt_input_value"] = TEMPLATE_NOTIFICACAO
    st.rerun()

if st.sidebar.button("🔍 Analisar Decisão / Intimação"):
    st.session_state["prompt_input_value"] = TEMPLATE_INTIMACAO
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
# CARREGAMENTO DA CHAVE e PROCESSAMENTO
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
        "Você tem conhecimento pleno de toda a legislação brasileira. Fundamente suas respostas nos artigos vigentes.\n"
    )
    if texto_contrato_atual:
        PROMPT_SISTEMA += f"\nDOCUMENTO DO CASO ATUAL ENVIADO EM PDF:\n{texto_contrato_atual}\n\n"

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "Não possuo autorização" not in message["content"]:
                arquivo_docx = criar_arquivo_word(message["content"])
                st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name=f"documento_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_{i}")

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
                    arquivo_docx = criar_arquivo_word(resposta.content)
                    st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name="documento_setubal_juris.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_imediato_{len(st.session_state.messages)}")

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
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from docx import Document
from io import BytesIO
import base64

st.set_page_config(page_title="Setubal Juris AI", page_icon="⚖️", layout="wide")

# Ocultar ferramentas de desenvolvedor e tarjas do Streamlit
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Setubal Juris AI")
st.subheader("Plataforma de Inteligência, Auditoria e Visão Jurídica")

if "messages" not in st.session_state:
    st.session_state.messages = []

# BARRA LATERAL: Configuração das ferramentas
st.sidebar.header("🏛️ Painel Setubal Juris")
st.sidebar.markdown("### 💾 Gestão da Sessão")

if st.sidebar.button("🗑️ Limpar Todo o Chat (Novo Caso)"):
    st.session_state.messages = []
    st.session_state.clear()
    st.toast("Conversa e documentos redefinidos!")
    st.rerun()

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

texto_historico = exportar_historico_completo(st.session_state.messages)
st.sidebar.download_button(
    label="💾 Salvar Histórico (.txt)",
    data=texto_historico,
    file_name="historico_caso_setubal_juris.txt",
    mime="text/plain"
)

# Caminhos configurados corretamente para a nuvem ler do GitHub
PASTA_LEIS = os.path.join(os.path.dirname(__file__), "leis_fixas")
PASTA_BANCO = os.path.join(os.path.dirname(__file__), "banco_vetorial")
os.makedirs(PASTA_LEIS, exist_ok=True)

@st.cache_resource
def inicializar_banco_de_dados():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    if os.path.exists(PASTA_BANCO) and len(os.listdir(PASTA_BANCO)) > 0:
        return Chroma(persist_directory=PASTA_BANCO, embedding_function=embeddings)
    
    documentos_texto = []
    if os.path.exists(PASTA_LEIS):
        arquivos = [f for f in os.listdir(PASTA_LEIS) if f.lower().endswith(".pdf")]
        if not arquivos:
            return None
        for arquivo in arquivos:
            caminho_completo = os.path.join(PASTA_LEIS, arquivo)
            reader = PdfReader(caminho_completo)
            for page in reader.pages:
                texto_pag = page.extract_text()
                if texto_pag:
                    documentos_texto.append(texto_pag)
                    
    if documentos_texto:
        banco = Chroma.from_texts(texts=documentos_texto, embedding=embeddings, persist_directory=PASTA_BANCO)
        return banco
    return None

groq_api_key = st.secrets.get("GROQ_API_KEY")

if not groq_api_key:
    st.error("👉 Configuração GROQ_API_KEY ausente nos Secrets do Streamlit Cloud.")
else:
    llm = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1, groq_api_key=groq_api_key)
    banco_leis = inicializar_banco_de_dados()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 Analisar Documento ou Foto (Caso Atual)")
    arquivo_enviado = st.sidebar.file_uploader(
        "Insira um contrato em PDF ou Foto (PNG, JPG, JPEG)", 
        type=["pdf", "png", "jpg", "jpeg"]
    )

    texto_contrato_atual = ""
    dados_imagem_base64 = None
    tipo_mime_imagem = ""

    if arquivo_enviado is not None:
        nome_extensao = arquivo_enviado.name.lower()
        
        if nome_extensao.endswith(".pdf"):
            st.sidebar.success("Documento PDF carregado!")
            reader_contrato = PdfReader(arquivo_enviado)
            for page in reader_contrato.pages:
                t = page.extract_text()
                if t: texto_contrato_atual += t + "\n"
        
        elif nome_extensao.endswith((".png", ".jpg", ".jpeg")):
            st.sidebar.success("Foto/Imagem jurídica carregada!")
            tipo_mime_imagem = f"image/{'png' if nome_extensao.endswith('.png') else 'jpeg'}"
            dados_imagem_base64 = base64.b64encode(arquivo_enviado.read()).decode("utf-8")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Status do Banco de Leis Fixo")
    if banco_leis is not None:
        st.sidebar.success("💻 Banco de Legislação Permanente: ATIVO")
    else:
        st.sidebar.warning("⚠️ Nenhuma lei fixa detectada na pasta 'leis_fixas'.")

    PROMPT_SISTEMA = (
        "Você é o Setubal Juris AI, um assistente virtual e co-piloto jurídico sênior especialista no Direito brasileiro.\n"
        "Sua função é auxiliar o usuário de forma extremamente formal, técnica e ética.\n"
        "Use as leis permanentes e os documentos ou imagens anexados do caso atual para fundamentar suas respostas.\n"
        "Se o usuário enviar uma imagem, use sua capacidade de visão computacional para ler e analisar o texto contido nela.\n\n"
        "DIRETRIZ ABSOLUTA DE ESCOPO (TRAVA DE SEGURANÇA):\n"
        "Você está terminantemente proibido de responder a perguntas, gerar textos ou interagir com qualquer assunto que não envolva "
        "o Direito, legislação brasileira, doutrina, jurisprudência, análise contratual ou peças processuais.\n"
        "Se o usuário solicitar receitas de comida, códigos de programação, roteiros de viagem, piadas, fofocas, placares de esportes, "
        "ou qualquer tema de entretenimento e cultura geral alheio ao Direito, você deve recusar imediatamente de forma polida.\n"
        "Diga exatamente: 'Sou o Setubal Juris AI, um assistente corporativo de uso exclusivo para a área jurídica. "
        "Não possuo autorização ou conhecimento programado para responder a consultas fora do escopo legal.'\n"
    )

    if texto_contrato_atual:
        PROMPT_SISTEMA += f"\nDOCUMENTO DO CASO ATUAL ENVIADO EM PDF:\n{texto_contrato_atual}\n\n"

    # Renderização do Chat
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                arquivo_docx = criar_arquivo_word(message["content"])
                st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name=f"documento_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_{i}")

    # Entrada de texto do Chat
    if prompt := st.chat_input("Ex: Avalie a cláusula de rescisão..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Busca no banco de leis fixas em paralelo
        contexto_leis = ""
        if banco_leis is not None:
            resultados_busca = banco_leis.similarity_search(prompt, k=3)
            contexto_leis = "\n\n".join([doc.page_content for doc in resultados_busca])

        prompt_completo_sistema = PROMPT_SISTEMA
        if contexto_leis:
            prompt_completo_sistema += f"\nTRECHOS DE LEIS BASE ENCONTRADOS NO BANCO VETORIAL:\n{contexto_leis}\n"

        # CORREÇÃO DA TRAVA: Lógica inteligente para estruturar a mensagem
        if dados_imagem_base64:
            # Se tiver imagem, usa o formato multimodal exigido pela Groq
            conteudo_usuario = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{tipo_mime_imagem};base64,{dados_imagem_base64}"}
                }
            ]
        else:
            # Se NÃO tiver imagem, passa o texto puro direto. Isso evita o BadRequestError!
            conteudo_usuario = prompt

        historico_ia = [
            SystemMessage(content=prompt_completo_sistema),
            HumanMessage(content=conteudo_usuario)
        ]
        
        with st.chat_message("assistant"):
            with st.spinner("Setubal Juris AI processando análise..."):
                resposta = llm.invoke(historico_ia)
                st.markdown(resposta.content)
                st.session_state.messages.append({"role": "assistant", "content": resposta.content})
                
                arquivo_docx = criar_arquivo_word(resposta.content)
                st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name="documento_setubal_juris.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_imediato_{len(st.session_state.messages)}")

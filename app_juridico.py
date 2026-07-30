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

# Configuração da página e ocultação dos botões e barras de desenvolvedor do topo
st.set_page_config(page_title="Setubal Juris AI", page_icon="⚖️", layout="wide")
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
    llm_texto = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, groq_api_key=groq_api_key)
    llm_visao = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1, groq_api_key=groq_api_key)
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
    )

    if texto_contrato_atual:
        PROMPT_SISTEMA += f"\nDOCUMENTO DO CASO ATUAL ENVIADO EM PDF:\n{texto_contrato_atual}\n\n"

    # Renderização das mensagens anteriores na tela
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "Não possuo autorização" not in message["content"]:
                arquivo_docx = criar_arquivo_word(message["content"])
                st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name=f"documento_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_{i}")

    # Processamento de nova entrada no chat
    if prompt := st.chat_input("Ex: Avalie a cláusula de rescisão..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Filtro de escopo jurídico preventivo
        palavras_bloqueadas = ["receita", "bolo", "doce", "cozinha", "comida", "futebol", "piada", "viagem", "roteiro", "musica", "filme"]
        prompt_minusculo = prompt.lower()
        
        if any(palavra in prompt_minusculo for palavra in palavras_bloqueadas):
            resposta_recusa = (
                "Sou o Setubal Juris AI, um assistente corporativo de uso exclusivo para a área jurídica. "
                "Não possuo autorização ou conhecimento programado para responder a consultas fora do escopo legal."
            )
            with st.chat_message("assistant"):
                st.markdown(resposta_recusa)
            st.session_state.messages.append({"role": "assistant", "content": resposta_recusa})
        
        else:
            contexto_leis = ""
            if banco_leis is not None:
                resultados_busca = banco_leis.similarity_search(prompt, k=2)
                contexto_leis = "\n\n".join([doc.page_content for doc in resultados_busca])

            prompt_completo_sistema = PROMPT_SISTEMA
            if contexto_leis:
                prompt_completo_sistema += f"\nTRECHOS DE LEIS BASE ENCONTRADOS NO BANCO VETORIAL:\n{contexto_leis}\n"

            with st.chat_message("assistant"):
                with st.spinner("Setubal Juris AI processando..."):
                    try:
                        if dados_imagem_base64:
                            conteudo_usuario = [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{tipo_mime_imagem};base64,{dados_imagem_base64}"}
                                }
                            ]
                            historico_ia = [
                                SystemMessage(content=prompt_completo_sistema),
                                HumanMessage(content=conteudo_usuario)
                            ]
                            resposta = llm_visao.invoke(historico_ia)
                        else:
                            historico_ia = [SystemMessage(content=prompt_completo_sistema)]
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

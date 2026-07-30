import streamlit as st
import os
from pypdf import PdfReader
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage
from docx import Document
from io import BytesIO

st.set_page_config(page_title="Setubal Juris AI", page_icon="⚖️", layout="wide")
st.title("⚖️ Setubal Juris AI")
st.subheader("Plataforma de Inteligência e Auditoria Jurídica")

if "messages" not in st.session_state:
    st.session_state.messages = []

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

# Buscando a chave direto das configurações ocultas da Nuvem (Secrets)
groq_api_key = st.secrets.get("GROQ_API_KEY")

if not groq_api_key:
    st.error("👉 Configuração GROQ_API_KEY ausente nos Secrets do Streamlit Cloud.")
else:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, groq_api_key=groq_api_key)
    
    # Na nuvem, salvamos temporariamente os vetores na memória do contêiner
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📁 Analisar Novo Documento (Caso Atual)")
    contrato_enviado = st.sidebar.file_uploader("Insira um contrato ou petição em PDF para auditoria", type=["pdf"])

    texto_contrato_atual = ""
    if contrato_enviado is not None:
        st.sidebar.success("Documento do caso carregado!")
        reader_contrato = PdfReader(contrato_enviado)
        for page in reader_contrato.pages:
            t = page.extract_text()
            if t: texto_contrato_atual += t + "\n"

    PROMPT_SISTEMA = (
        "Você é o Setubal Juris AI, um assistente virtual e co-piloto jurídico sênior especialista no Direito brasileiro.\n"
        "Sua função é auxiliar o usuário de forma extremamente formal, técnica e ética.\n"
        "Use os trechos anexados do caso atual para fundamentar suas respostas.\n"
    )

    if texto_contrato_atual:
        PROMPT_SISTEMA += f"\nDOCUMENTO DO CASO ATUAL ENVIADO PELO CLIENTE:\n{texto_contrato_atual}\n\n"

    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                arquivo_docx = criar_arquivo_word(message["content"])
                st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name=f"documento_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_{i}")

    if prompt := st.chat_input("Ex: Analise a cláusula de rescisão do contrato enviado..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        historico_ia = [SystemMessage(content=PROMPT_SISTEMA)]
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                historico_ia.append(HumanMessage(content=msg["content"]))
        
        with st.chat_message("assistant"):
            with st.spinner("Setubal Juris AI processando análise..."):
                resposta = llm.invoke(historico_ia)
                st.markdown(resposta.content)
                st.session_state.messages.append({"role": "assistant", "content": resposta.content})
                
                arquivo_docx = criar_arquivo_word(resposta.content)
                st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name="documento_setubal_juris.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_imediato_{len(st.session_state.messages)}")

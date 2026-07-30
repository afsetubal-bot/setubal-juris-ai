import streamlit as st
import os
from pypdf import PdfReader
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from docx import Document
from io import BytesIO
import base64

# Configuração visual do topo da página (Limpeza de menus de desenvolvedor)
st.set_page_config(page_title="Setubal Juris AI", page_icon="⚖️", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stAppDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE PROTEÇÃO COM USUÁRIO E SENHA ---
def check_password():
    def password_entered():
        if st.session_state["username"] == "admin" and st.session_state["password"] == "setubal123":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Remove a senha da memória por segurança
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Acesso Restrito - Setubal Juris AI")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acesso Restrito - Setubal Juris AI")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        st.error("❌ Usuário ou Senha incorretos.")
        return False
    return True

# Se o login estiver correto, libera o sistema
if check_password():

    st.title("⚖️ Setubal Juris AI")
    st.subheader("Plataforma de Inteligência, Auditoria e Visão Jurídica")

    # Inicializar memórias de sessão
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "historico_casos" not in st.session_state:
        st.session_state.historico_casos = {}

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

    # BARRA LATERAL: Configurações e ferramentas
    st.sidebar.header("🏛️ Painel Setubal Juris")
    st.sidebar.markdown("### 💾 Gestão da Sessão")

    # NOVO BOTÃO INTEGRADO: Iniciar Novo Caso e Arquivar o Anterior na Lateral
    if st.sidebar.button("➕ Iniciar Novo Caso (Arquivar Atual)"):
        if st.session_state.messages:
            num_caso = len(st.session_state.historico_casos) + 1
            st.session_state.historico_casos[f"Caso Arquivado #{num_caso}"] = st.session_state.messages
            st.toast(f"Caso #{num_caso} arquivado com sucesso!")
        st.session_state.messages = []
        st.rerun()

    if st.sidebar.button("🗑️ Limpar Tudo (Zerar Memória)"):
        st.session_state.messages = []
        st.session_state.historico_casos = {}
        st.session_state.clear()
        st.toast("Todo o sistema foi limpo!")
        st.rerun()

    # Exibe a lista de Casos Arquivados para consulta se houver algum salvo
    if st.session_state.historico_casos:
        st.sidebar.markdown("### 🗄️ Casos Arquivados nesta Sessão")
        for nome_caso, msgs_salvas in st.session_state.historico_casos.items():
            texto_baixar = exportar_historico_completo(msgs_salvas)
            st.sidebar.download_button(
                label=f"📥 Baixar {nome_caso}",
                data=texto_baixar,
                file_name=f"{nome_caso.lower().replace(' ', '_')}.txt",
                mime="text/plain",
                key=f"dl_{nome_caso}"
            )

    groq_api_key = st.secrets.get("GROQ_API_KEY")

    if not groq_api_key:
        st.error("👉 Configuração GROQ_API_KEY ausente nos Secrets do Streamlit Cloud.")
    else:
        # Inicialização dos modelos inteligentes na Nuvem do Groq
        llm_texto = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1, groq_api_key=groq_api_key)
        llm_visao = ChatGroq(model="llama-3.2-11b-vision-preview", temperature=0.1, groq_api_key=groq_api_key)

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

        # INSTRUÇÃO COGNITIVA DA IA: Conhecimento nativo de todas as Leis e Códigos do Brasil
        PROMPT_SISTEMA = (
            "Você é o Setubal Juris AI, um assistente virtual e co-piloto jurídico sênior especialista no Direito brasileiro.\n"
            "Sua função é auxiliar o usuário de forma extremamente formal, técnica e ética.\n"
            "Você tem conhecimento pleno de toda a legislação brasileira (Código Civil, CPC, Código Penal, CLT, Constituição Federal, etc.).\n"
            "Fundamente suas respostas nos artigos e regras vigentes do ordenamento jurídico brasileiro.\n"
        )

        if texto_contrato_atual:
            PROMPT_SISTEMA += f"\nDOCUMENTO DO CASO ATUAL ENVIADO EM PDF PELO CLIENTE:\n{texto_contrato_atual}\n\n"

        # Renderização do Chat na tela
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant" and "Não possuo autorização" not in message["content"]:
                    arquivo_docx = criar_arquivo_word(message["content"])
                    st.download_button(label="📥 Baixar no Word", data=arquivo_docx, file_name=f"documento_{i}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_{i}")

        # Entrada do chat
        if prompt := st.chat_input("Ex: Qual o prazo de contestação segundo o CPC? / Analise o contrato enviado..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Filtro preventivo de escopo jurídico
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
                                    SystemMessage(content=PROMPT_SISTEMA),
                                    HumanMessage(content=conteudo_usuario)
                                ]
                                resposta = llm_visao.invoke(historico_ia)
                            else:
                                historico_ia = [SystemMessage(content=PROMPT_SISTEMA)]
                                for msg in st.session_state.messages:
                                    if msg["role"] == "user":
                                        historico_ia.append(HumanMessage(content=msg["content"]))
                                    else:
                                        historico_ia.append(SystemMessage(content=msg["content"]))

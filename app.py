import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
from utils import get_pdf_text, get_text_chunks, create_vector_store, get_rag_response

st.set_page_config(page_title="VTOL VR Trainer", page_icon=":airplane:")

# --- USER AUTHENTICATION ---
def get_authenticator():
    try:
        with open('config.yaml') as file:
            config = yaml.load(file, Loader=SafeLoader)
    except FileNotFoundError:
        st.error("Configuration file not found. Please make sure 'config.yaml' is in the root directory.")
        st.stop()
    return stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )

authenticator = get_authenticator()

name, authentication_status, username = authenticator.login('main')

if not authentication_status:
    if authentication_status == False:
        st.error("Username/password is incorrect")
    elif authentication_status == None:
        st.warning("Please enter your username and password")
    st.stop()

# --- MAIN APP LOGIC ---
st.sidebar.title(f"Welcome {name}")
authenticator.logout('Logout', 'sidebar')

st.title("VTOL VR AI Trainer")
st.write("Your knowledgeable guide to the world of VTOL VR.")

# --- API KEY AND KNOWLEDGE BASE SETUP ---
st.sidebar.header("Setup")
api_key = st.sidebar.text_input("Enter your Google API Key", type="password", key="api_key_input")

if st.sidebar.button("Process Knowledge Base"):
    if not api_key:
        st.sidebar.error("Please enter your Google API Key first.")
    else:
        with st.spinner("Processing... This may take a moment."):
            kb_path = "knowledge_base"
            if not os.path.exists(kb_path) or not any(f.endswith('.pdf') for f in os.listdir(kb_path)):
                st.sidebar.warning("No PDF files found in the 'knowledge_base' directory.")
            else:
                raw_text = get_pdf_text(kb_path)
                if raw_text:
                    text_chunks = get_text_chunks(raw_text)
                    create_vector_store(text_chunks, api_key)
                else:
                    st.sidebar.warning("Could not extract text from PDFs.")

# --- CHAT INTERFACE ---
st.header("Chat")

if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything about VTOL VR!"):
    if not api_key:
        st.warning("Please enter your Google API Key in the sidebar to chat.")
    elif not os.path.exists("faiss_index"):
        st.warning("Please process the knowledge base first.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Thinking..."):
            response = get_rag_response(prompt, api_key)
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


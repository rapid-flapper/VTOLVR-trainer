import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os
import json
from utils import get_pdf_text, get_text_chunks, create_vector_store, get_rag_response

st.set_page_config(page_title="VTOL VR Trainer", page_icon=":airplane:", layout="wide")

# --- CONVERSATION MANAGEMENT ---
def get_user_conversations_path(username):
    path = os.path.join("conversations", username)
    os.makedirs(path, exist_ok=True)
    return path

def list_conversations(username):
    path = get_user_conversations_path(username)
    return [f.replace('.json', '') for f in os.listdir(path) if f.endswith('.json')]

def save_conversation(username, chat_name, messages):
    path = get_user_conversations_path(username)
    with open(os.path.join(path, f"{chat_name}.json"), 'w') as f:
        json.dump(messages, f)

def load_conversation(username, chat_name):
    path = get_user_conversations_path(username)
    with open(os.path.join(path, f"{chat_name}.json"), 'r') as f:
        return json.load(f)

def delete_conversation(username, chat_name):
    path = get_user_conversations_path(username)
    os.remove(os.path.join(path, f"{chat_name}.json"))

# --- USER AUTHENTICATION ---
def get_authenticator():
    try:
        # Load credentials from Streamlit secrets
        config = {
            'credentials': json.loads(st.secrets["credentials"]["usernames"]),
            'cookie': st.secrets["cookie"],
            'preauthorized': json.loads(st.secrets["preauthorized"]["emails"])
        }
    except (KeyError, json.JSONDecodeError) as e:
        st.error(f"Error loading configuration from Streamlit secrets: {e}")
        st.info("Please ensure your secrets are configured correctly in the Streamlit Community Cloud settings.")
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

# --- SESSION STATE INITIALIZATION ---
if 'current_chat' not in st.session_state:
    st.session_state.current_chat = None
if 'messages' not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR --- #
st.sidebar.title(f"Welcome {name}")

st.sidebar.header("Chat History")
if st.sidebar.button("New Chat"):
    st.session_state.messages = []
    st.session_state.current_chat = None
    st.rerun()

conversations = list_conversations(username)
for chat_name in conversations:
    col1, col2, col3 = st.sidebar.columns([3,1,1])
    with col1:
        if st.button(chat_name, key=f"load_{chat_name}", use_container_width=True):
            st.session_state.messages = load_conversation(username, chat_name)
            st.session_state.current_chat = chat_name
            st.rerun()
    with col3:
        if st.button("🗑️", key=f"delete_{chat_name}"):
            delete_conversation(username, chat_name)
            if st.session_state.current_chat == chat_name:
                st.session_state.current_chat = None
                st.session_state.messages = []
            st.rerun()

st.sidebar.header("Setup")
# Get API key from secrets
api_key = st.secrets.get("google_api_key")

if not api_key:
    st.sidebar.error("Google API Key not found. Please add it to your Streamlit secrets.")
    st.stop()

if st.sidebar.button("Process Knowledge Base"):
    with st.spinner("Processing..."):
        raw_text = get_pdf_text("knowledge_base")
        if raw_text:
            text_chunks = get_text_chunks(raw_text)
            create_vector_store(text_chunks, api_key)
        else:
            st.sidebar.warning("No text found in PDFs in 'knowledge_base' folder.")

authenticator.logout('Logout', 'sidebar')

# --- MAIN CHAT INTERFACE --- #
st.title("VTOL VR AI Trainer")

if st.session_state.current_chat:
    st.header(f"Chat: {st.session_state.current_chat}")
else:
    st.header("New Chat")
    if st.session_state.messages:
        new_chat_name = st.text_input("Enter a name for this chat to save it:")
        if st.button("Save Chat"):
            if new_chat_name:
                save_conversation(username, new_chat_name, st.session_state.messages)
                st.session_state.current_chat = new_chat_name
                st.rerun()
            else:
                st.warning("Please enter a name for the chat.")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about VTOL VR!"):
    if not os.path.exists("faiss_index"):
        st.warning("Please process the knowledge base first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking..."):
        response = get_rag_response(prompt, api_key)
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # If the chat is already saved, update the saved file
        if st.session_state.current_chat:
            save_conversation(username, st.session_state.current_chat, st.session_state.messages)

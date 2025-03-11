"""LlamaIndex RAG app"""

import shutil
from pathlib import Path

import git
import htmltabletomd
import openai
import streamlit as st
from llama_index.core import (
    Document,
    Settings,
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from llama_index.core.readers.base import BaseReader
from llama_index.llms.openai import OpenAI
from streamlit_pills import pills

st.set_page_config(
    page_title="Clinic Chat",
    page_icon="./img/avatar.png",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None,
)
openai.api_key = st.secrets.OPENAI_API_KEY

# Initialize the chat messages history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me a question about the Data Science Clinic!",
        }
    ]

def download_repo(repo_url, repo_path):
    """Download a repo"""
    if Path.exists(Path(repo_path)):
        shutil.rmtree(repo_path)
    git.Repo.clone_from(repo_url, repo_path)


def get_meta(file_path):
    """Builds url metadata."""
    url_prefix = "https://dsi-clinic.github.io/the-clinic/"
    if file_path.startswith("/mount/src/"):
        file_path = file_path.replace(
            "/mount/src/clinic-chat/data/",
            url_prefix,
        )
    elif file_path.startswith("/project/data/"):
        file_path = file_path.replace(
            "/project/data/",
            url_prefix,
        )

    if file_path.endswith(".md"):
        file_path = file_path.replace(".md", ".html")

    return {
        "link": file_path
    }

class OverrideReader(BaseReader):
    """Overrides BaseReader"""
    def load_data(self, file, extra_info=None):
        """Custom data loader

        Args:
            file (Path): Path to the file to read.
            extra_info (dict, optional): Extra args for Document loader. Defaults to None.

        Returns:
            list: List of Document objects.
        """
        if str(file).endswith("/projects.md"):
            print("Loading project data")
            with open(file) as f:
                text = f.read()
                text = htmltabletomd.convert_table(text, content_conversion_ind=True)
                print(text)
        else:
            with open(file) as f:
                text = f.read()
        # load_data returns a list of Document objects
        return [Document(text=text, extra_info=extra_info or {})]



@st.cache_resource(show_spinner=False)
def load_data():
    """Load data from repository and build index."""
    repo_url = "https://github.com/dsi-clinic/the-clinic.git"
    repo_path = "./data"
    download_repo(repo_url, repo_path)
    reader = SimpleDirectoryReader(
        input_dir=repo_path,
        required_exts=[".md", ".pdf"],
        recursive=True,
        file_metadata=get_meta,
        file_extractor={".md": OverrideReader()}
    )
    docs = reader.load_data()
    Settings.llm = OpenAI(
        model="gpt-4o-mini",
        temperature=0.8,
        system_prompt="""You are an expert on 
        the Data Science Clinic and your 
        job is to answer questions. 
        Assume that all questions are related 
        to the Data Science Clinic. Keep 
        your answers based on 
        facts – do not hallucinate features.""",
    )
    index = VectorStoreIndex.from_documents(docs)
    return index


index = load_data()

# Initialize the chat engine
if "chat_engine" not in st.session_state.keys():
    st.session_state.chat_engine = index.as_chat_engine(
        chat_mode="condense_question", verbose=True, streaming=True
    )

selected = pills(
    "Choose a question to get started or write your own below.",
    [
        "How do I get involved in Clinic?",
        "What are the coding standards?",
        "How do I get an A in the class?"

    ],
    clearable=False,
    index=None,
)

# Prompt for user input and save to chat history
if prompt := st.chat_input("Ask a question"):
    st.session_state.messages.append({"role": "user", "content": prompt})

# Write message history to UI
for message in st.session_state.messages:
    # If message is from assistant, write it to the UI as a chat message
    if message["role"] == "assistant":
        with st.chat_message(message["role"], avatar="./img/avatar.png"):
            st.write(message["content"])
    else:
        with st.chat_message(message["role"]):
            st.write(message["content"])

# To avoid duplicated display of answered pill questions each rerun
if selected and selected not in st.session_state.get(
    "displayed_pill_questions", set()
):
    st.session_state.setdefault("displayed_pill_questions", set()).add(selected)

    with st.chat_message("user"):
        st.write(selected)
        user_message = {"role": "user", "content": selected}
        st.session_state.messages.append(user_message)

    st.session_state["chat_engine"].stream_chat(selected)

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant", avatar="./img/avatar.png"):
        response_stream = st.session_state.chat_engine.stream_chat(prompt)
        st.write_stream(response_stream.response_gen)
        message = {"role": "assistant", "content": response_stream.response}
        # Add response to message history
        st.session_state.messages.append(message)

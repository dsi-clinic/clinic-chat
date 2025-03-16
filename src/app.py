"""LlamaIndex RAG app"""
from pathlib import Path

import openai
import streamlit as st
from llama_index.core import (
    Settings,
    VectorStoreIndex,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.redis import RedisVectorStore
from redisvl.schema import IndexSchema
from streamlit_pills import pills

parent_dir = Path(__file__).parent.parent
config_dir = parent_dir / "config"

st.set_page_config(
    page_title="Clinic Chat",
    page_icon="./img/avatar.png",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None,
)
openai.api_key = st.secrets.OPENAI_API_KEY
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
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

# Initialize the chat messages history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me a question about the Data Science Clinic!",
        }
    ]

@st.cache_resource(show_spinner=False)
def load_data():
    """Load index from redis vectorstore."""
    embed_model = Settings.embed_model
    redis_user = "default"
    redis_pwd = st.secrets.REDIS_PASSWORD
    redis_host = "redis-16124.c261.us-east-1-4.ec2.redns.redis-cloud.com"
    redis_port = 16124
    redis_url = f"redis://{redis_user}:{redis_pwd}@{redis_host}:{redis_port}"

    vector_store = RedisVectorStore(
        schema=IndexSchema.from_yaml(config_dir / "index_schema.yaml"),
        redis_url=redis_url,
        overwrite=False
    )
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        embed_model=embed_model
    )
    
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
        "How do I get an A in the class?",
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

        # Add response to message history
        message = {"role": "assistant", "content": response_stream.response}
        st.session_state.messages.append(message)

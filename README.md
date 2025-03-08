# clinic-chat
## About
This repository contains a Streamlit chatbot powered by LlamaIndex. The chatbot uses RAG on the Data Science Clinic's GitHub repository to provide responses to queries about the Data Science Clinic.

## Demo
Visit the [live demo](https://clinic-chat.streamlit.app/). 

## Usage
Create a [project secrets file](https://docs.streamlit.io/develop/concepts/connections/secrets-management) to store your OpenAI key at `.streamlit/secrets.toml`. The contents of this file should read:
```toml
OPENAI_API_KEY = "sk-proj..."
```

Run the Streamlit application locally with the following command:
```
make run-app
```

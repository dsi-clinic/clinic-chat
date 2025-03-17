# clinic-chat
## About
This repository contains a Streamlit chatbot powered by LlamaIndex. The chatbot uses RAG on the Data Science Clinic's GitHub repository to provide responses to queries about the Data Science Clinic.

## Demo
Visit the [live demo](https://clinic-chat.streamlit.app/). 

## Usage

### Ingest Data
The code for ingesting data is located in `src/ingest.py`. It loads data from GitHub and Google Drive, parses metadata and inserts those documents into a remote Redis vector store.

1. Create a Google service account key and save it to the root of this directory as `service_account_key.json`.
2. Get a Redis database password.
3. Run the following command:
```
make run-ingest REDIS_PASSWORD=<password>
```

### Run Streamlit App
Create a [project secrets file](https://docs.streamlit.io/develop/concepts/connections/secrets-management) to store your keys at `.streamlit/secrets.toml`. The contents of this file should read:
```toml
OPENAI_API_KEY="sk-proj..."
REDIS_PASSWORD="xD2C..."
```

Run the Streamlit application locally with the following command:
```
make run-app
```

# clinic-chat
## About
This repository contains a Streamlit chatbot powered by LlamaIndex. The chatbot uses RAG on the Data Science Clinic's GitHub repository to provide responses to queries about the Data Science Clinic.

## Demo
Visit the [live demo](https://clinic-chat.streamlit.app/). 

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for fast Python package management. Install uv if you haven't already:

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Install dependencies:
```bash
uv sync
```

## Usage

### Ingest Data
The code for ingesting data is located in `src/ingest.py`. It loads data from GitHub and Google Drive, parses metadata and inserts those documents into a remote Redis vector store.

1. Create a Google service account key and save it to the root of this directory as `service_account_key.json`.
2. Get a Redis database password.
3. Run the following command:
```bash
make run-ingest REDIS_PASSWORD=<password>
```

### Run Streamlit App
Create a [project secrets file](https://docs.streamlit.io/develop/concepts/connections/secrets-management) to store your keys at `.streamlit/secrets.toml`. The contents of this file should read:
```toml
OPENAI_API_KEY="sk-proj..."
REDIS_PASSWORD="xD2C..."
```

Run the Streamlit application locally with the following command:
```bash
make run-app
```

## Development

### Adding Dependencies
To add new dependencies, update the `dependencies` list in `pyproject.toml` and run:
```bash
uv sync
```

### Running with uv
You can also run the application directly with uv:
```bash
# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the ingestion script
python src/ingest.py

# Run the Streamlit app
streamlit run src/app.py
```

"""Ingestion pipeline for Clinic Chat."""

import json
import os
import shutil
from pathlib import Path

import dotenv
import git
import htmltabletomd
import openai
import redis
from llama_index.core import (
    Document,
    Settings,
    SimpleDirectoryReader,
)
from llama_index.core.ingestion import (
    DocstoreStrategy,
    IngestionPipeline,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.readers.google import GoogleDriveReader
from llama_index.storage.docstore.redis import RedisDocumentStore
from llama_index.vector_stores.redis import RedisVectorStore
from redisvl.schema import IndexSchema

dotenv.load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")


def download_repo(repo_url, to_path):
    """Clones a repo to a path.

    Args:
        repo_url (str): GitHub URL
        to_path (Path): Path to clone to
    """
    if Path.exists(Path(to_path)):
        shutil.rmtree(to_path)
    git.Repo.clone_from(repo_url, to_path)


def get_meta(file_path):
    """Builds url metadata.

    Args:
        file_path (str): File path
    Returns:
        dict: Metadata
    """
    url_prefix = "https://clinic.ds.uchicago.edu/"

    # Find the position of "data/" in the path and replace everything before it
    data_index = file_path.find("/data/")
    if data_index != -1:
        # Replace everything up to and including "/data/" with the URL prefix
        file_path = (
            url_prefix + file_path[data_index + 6 :]
        )  # +6 to skip "/data/"
    else:
        print(f"Warning: 'data/' not found in file path: {file_path}")

    if file_path.endswith(".md"):
        file_path = file_path.replace(".md", ".html")

    return {"link": file_path}


def load_key(file_path):
    """Loads key from a file.

    Args:
        file_path (Path): Path to service account file
    Returns:
        dict: Dict of service account key
    """
    with file_path.open() as f:
        return json.load(f)


def load_google_data(file_ids):
    """Custom google loader.

    Args:
        file_ids (list): List of file ids

    Returns:
        list: list of Documents
    """
    file_dir = Path(__file__).parent.parent
    service_account_key = load_key(file_dir / "service_account_key.json")
    loader = GoogleDriveReader(service_account_key=service_account_key)
    docs = loader.load_data(file_ids=file_ids)
    for doc in docs:
        doc.id_ = doc.metadata.get("file path", "none")
    return docs


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
            with Path.open(file) as f:
                text = f.read()
                text = htmltabletomd.convert_table(
                    text, content_conversion_ind=True
                )
        elif "/admin/" in str(file):
            # skip admin files
            return ""
        else:
            with Path.open(file) as f:
                text = f.read()

        return [Document(text=text, extra_info=extra_info or {})]


def main():
    """Main function"""
    parent_dir = Path(__file__).parent.parent
    config_dir = parent_dir / "config"

    # changing the global default
    embed_model = OpenAIEmbedding()
    Settings.embed_model = embed_model

    # Chunk size
    Settings.chunk_size = 1024
    Settings.chunk_overlap = 20

    # Define and save schema
    custom_schema = IndexSchema.from_dict(
        {
            "index": {"name": "clinic-index", "prefix": "doc"},
            # customize fields that are indexed
            "fields": [
                # required fields for llamaindex
                {"type": "tag", "name": "id"},
                {"type": "tag", "name": "doc_id"},
                {"type": "text", "name": "text"},
                {
                    "type": "vector",
                    "name": "vector",
                    "attrs": {
                        "dims": 1536,
                        "algorithm": "hnsw",
                        "distance_metric": "cosine",
                    },
                },
            ],
        }
    )
    custom_schema.to_yaml(config_dir / "index_schema.yaml")

    # Download git repo
    repo_url = "https://github.com/dsi-clinic/the-clinic.git"
    repo_path = parent_dir / "data"
    download_repo(repo_url, repo_path)

    # Load the local docs
    reader = SimpleDirectoryReader(
        input_dir=repo_path,
        required_exts=[".md", ".pdf"],
        recursive=True,
        file_metadata=get_meta,
        file_extractor={".md": OverrideReader()},
    )
    local_docs = reader.load_data()

    google_docs = load_google_data(
        file_ids=[
            "1XtyqoFgvX2aUhKBBjA0Oba8DbvZsuf3sdQeFH1Nt1TA",
            "1E5wyLk4vXHeg_c0WmxvVYlKI9wnTj7P4pktkH7csLn8",
            "1ovkawtyIw7Itfx1Kj1uw0wnKyrMNBpdldNCFsTd2fcw",
        ]
    )

    # Combine local and google docs
    docs = local_docs + google_docs

    # Set up Redis connection and vectorstore
    redis_host = os.getenv("REDIS_HOST")
    redis_port = os.getenv("REDIS_PORT")
    redis_url = f"redis://{redis_host}:{redis_port}"

    if redis_host != "localhost":
        redis_user = "default"
        redis_pwd = os.getenv("REDIS_PASSWORD")
        redis_url = (
            f"redis://{redis_user}:{redis_pwd}@{redis_host}:{redis_port}"
        )

    redis_client = redis.Redis.from_url(redis_url)
    vector_store = RedisVectorStore(
        redis_client=redis_client, overwrite=True, schema=custom_schema
    )
    docstore = RedisDocumentStore.from_redis_client(
        redis_client=redis_client, namespace="document_store"
    )

    # Create and run ingestion pipeline
    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(),
            embed_model,
        ],
        docstore=docstore,
        vector_store=vector_store,
        docstore_strategy=DocstoreStrategy.UPSERTS,
    )
    pipeline.run(documents=docs)


if __name__ == "__main__":
    main()

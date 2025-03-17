"""Ingestion pipeline for Clinic Chat."""

import json
import os
import shutil
from pathlib import Path

import dotenv
import git
import htmltabletomd
from llama_index.core import (
    Document,
    Settings,
    SimpleDirectoryReader,
)
from llama_index.core.ingestion import (
    IngestionPipeline,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.readers.base import BaseReader
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.google import GoogleDriveReader
from llama_index.vector_stores.redis import RedisVectorStore
from redisvl.schema import IndexSchema

dotenv.load_dotenv()


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
    elif file_path.startswith("/Users/hannifan/work/clinic-chat/data/"):
        file_path = file_path.replace(
            "/Users/hannifan/work/clinic-chat/data/",
            url_prefix,
        )

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
        else:
            with Path.open(file) as f:
                text = f.read()
        # load_data returns a list of Document objects
        return [Document(text=text, extra_info=extra_info or {})]


def main():
    """Main function"""
    parent_dir = Path(__file__).parent.parent
    config_dir = parent_dir / "config"

    # changing the global default
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.embed_model = embed_model

    # Define and save schema
    custom_schema = IndexSchema.from_dict(
        {
            "index": {"name": "GDRIVE", "prefix": "doc"},
            # customize fields that are indexed
            "fields": [
                # required fields for llamaindex
                {"type": "tag", "name": "id"},
                {"type": "tag", "name": "doc_id"},
                {"type": "text", "name": "text"},
                # custom vector field for bge-small-en-v1.5 embeddings
                {
                    "type": "vector",
                    "name": "vector",
                    "attrs": {
                        "dims": 384,
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
    docs = google_docs + local_docs

    # Set up Redis connection and vectorstore
    redis_user = "default"
    redis_pwd = os.getenv("REDIS_PASSWORD")
    redis_host = "redis-16124.c261.us-east-1-4.ec2.redns.redis-cloud.com"
    redis_port = 16124
    redis_url = f"redis://{redis_user}:{redis_pwd}@{redis_host}:{redis_port}"
    vector_store = RedisVectorStore(
        redis_url=redis_url, overwrite=True, schema=custom_schema
    )

    # Create and run ingestion pipeline
    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(),
            embed_model,
        ],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
    )
    pipeline.run(documents=docs)


if __name__ == "__main__":
    main()

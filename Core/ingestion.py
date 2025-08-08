# ingestion.py
import os
import json
import time
import traceback
import requests
from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

def safe_fetch_url_text(url: str, timeout=15) -> str:
    try:
        res = requests.get(url, timeout=timeout)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        # remove scripts/styles
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        text = soup.get_text(separator="\n")
        return "\n".join([ln.strip() for ln in text.splitlines() if ln.strip()])
    except Exception:
        return ""
#  pypdf

def read_pdf_text(path: str) -> str:
    try:
        reader = PdfReader(path)
        pages = []
        for p in reader.pages:
            pages.append(p.extract_text() or "")
        return "\n".join(pages)
    except Exception:
        return ""

def load_files(file_paths: List[str]):
    docs = []
    for path in file_paths:
        if not path:
            continue
        p = Path(path)
        if not p.exists():
            continue
        if p.suffix.lower() == ".pdf":
            txt = read_pdf_text(str(p))
            docs.append(Document(page_content=txt, metadata={"source": str(p.name)}))
        elif p.suffix.lower() in [".json", ".txt"]:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                docs.append(Document(page_content=fh.read(), metadata={"source": str(p.name)}))
        else:
            # fallback to reading bytes as text
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                    docs.append(Document(page_content=fh.read(), metadata={"source": str(p.name)}))
            except Exception:
                continue
    return docs

def create_bot_from_config(config: dict, bot_dir: str):
    """
    1) Gather texts from config["knowledge_sources"] (urls & files)
    2) Chunk and embed
    3) Create FAISS vector store and save to bot_dir/<faiss_store_name>
    4) Copy templates (app & chat_graph) and inject config pointers
    """
    os.makedirs(bot_dir, exist_ok=True)
    meta_path = os.path.join(bot_dir, "bot_config.json")

    # Gather sources
    texts = []
    docs = []

    # URLs
    urls = config.get("knowledge_sources", {}).get("urls", []) or []
    for u in urls:
        t = safe_fetch_url_text(u)
        if t:
            docs.append(Document(page_content=t, metadata={"source": u}))

    # Files (uploaded)
    uploaded = config.get("_uploaded_files", []) or []
    docs.extend(load_files(uploaded))

    # Files provided as filenames relative to server (e.g., demo3.pdf stored in uploads/...), handle if provided
    declared_files = config.get("knowledge_sources", {}).get("files", []) or []
    for fname in declared_files:
        candidate = os.path.join("uploads", fname)
        if os.path.exists(candidate):
            docs.extend(load_files([candidate]))

    if not docs:
        # Create a small doc from system prompt as a fallback
        docs.append(Document(page_content=config.get("system_prompt", ""), metadata={"source": "system_prompt"}))

    # Chunk documents
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    # Embeddings
    emb_model = config.get("embedding_model") or "models/embedding-001"
    api_key = config.get("llm", {}).get("api_key") or os.getenv("GOOGLE_API_KEY")
    embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=api_key)

    # Create FAISS and save
    faiss_store_name = config.get("faiss_store_name", f"faiss_{int(time.time())}")
    faiss_dir = os.path.join(bot_dir, faiss_store_name)
    os.makedirs(faiss_dir, exist_ok=True)

    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(faiss_dir)

    # Write a metadata file pointing to index
    manifest = {
        "bot_name": config.get("bot_name"),
        "created_at": config.get("created_at"),
        "faiss_dir": faiss_dir,
        "llm": config.get("llm"),
        "embedding_model": emb_model,
    }
    with open(os.path.join(bot_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    # Copy templates and make minimal substitutions: we'll copy templates exactly and bot will load manifest.json
    copy_templates(bot_dir)

def copy_templates(bot_dir: str):
    """
    Copy the template files from templates/ into bot_dir.
    The templates are written to load bot_config.json or manifest.json.
    """
    import shutil
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    for name in ["app_template.py", "chat_graph_template.py", "prompt.txt"]:
        src = os.path.join(template_dir, name)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(bot_dir, name.replace("_template", "")))

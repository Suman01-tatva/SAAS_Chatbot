# templates/app_template.py
"""
This is the per-bot app that will be copied into each bot folder as `app.py`.
It loads bot's manifest.json and bot_config.json from the same directory to find faiss index and LLM key.
Run with: python app.py
"""
import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_core.messages import HumanMessage
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph
from chat_graph import build_chat_graph  # local import, template also copies chat_graph.py
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")

BASE = os.path.dirname(__file__)
# load manifest
with open(os.path.join(BASE, "manifest.json"), "r", encoding="utf-8") as fh:
    manifest = json.load(fh)

faiss_dir = manifest.get("faiss_dir")
llm_conf = manifest.get("llm") or {}
emb_model = manifest.get("embedding_model")

# Setup embeddings & load vectorstore
try:
    embeddings = GoogleGenerativeAIEmbeddings(model=emb_model, google_api_key=llm_conf.get("api_key") or os.getenv("GOOGLE_API_KEY"))
    vector_store = FAISS.load_local(faiss_dir, embeddings, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
except Exception as e:
    logging.exception("Failed to load FAISS store")
    retriever = None

# Build langgraph graph (assumes chat_graph.py is present)
try:
    graph = build_chat_graph()
except Exception:
    graph = None

def retrieve_knowledge(query: str):
    if not retriever:
        return ""
    docs = retriever.similarity_search(query, k=3)
    return "\n".join([d.page_content for d in docs])

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    knowledge_context = retrieve_knowledge(user_input)
    final_input = f"{user_input}\n\nContext:\n{knowledge_context}"

    messages = [HumanMessage(content=final_input)]

    if not graph:
        return jsonify({"response": "Chat engine not available"}), 500

    try:
        result = graph.invoke({"messages": messages})
    except Exception as e:
        logging.exception("LangGraph invoke failed")
        return jsonify({"response": "Chat backend error"}), 500

    last_msg = result["messages"][-1]
    if isinstance(last_msg, dict) and "output" in last_msg:
        response_text = last_msg["output"]
    elif hasattr(last_msg, "content"):
        response_text = last_msg.content
    else:
        response_text = str(last_msg)

    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

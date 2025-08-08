# # saas_manager.py
# import os, shutil, json, hashlib, logging
# from flask import Flask, request, jsonify
# from werkzeug.utils import secure_filename
# from bs4 import BeautifulSoup
# import requests
# from langchain_community.vectorstores import FAISS
# from langchain_google_genai import GoogleGenerativeAIEmbeddings
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_core.documents import Document

# BASE_DIR = os.path.dirname(__file__)
# TENANTS_DIR = os.path.join(BASE_DIR, "tenants")
# TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# os.makedirs(TENANTS_DIR, exist_ok=True)

# app = Flask(__name__)

# def scrape_website(url):
#     try:
#         res = requests.get(url, timeout=10)
#         soup = BeautifulSoup(res.text, "html.parser")
#         return soup.get_text()
#     except Exception as e:
#         logging.error(f"Scraping failed: {e}")
#         return ""

# def process_business(biz_id, site_url, api_key, files_data, json_data={}):
#     tenant_dir = os.path.join(TENANTS_DIR, biz_id)
#     os.makedirs(tenant_dir, exist_ok=True)

#     # 1. Save .env
#     with open(os.path.join(tenant_dir, ".env"), "w") as f:
#         f.write(f"GOOGLE_API_KEY={api_key}\nSITE_URL={site_url}\n")

#     # 2. Save knowledge json
#     json_path = os.path.join(tenant_dir, "restaurant-data.json")
#     with open(json_path, "w") as f:
#         json.dump(json_data, f)

#     # 3. Process files
#     docs = []
#     for file_storage in files_data:
#         filename = secure_filename(file_storage.filename)
#         filepath = os.path.join(tenant_dir, filename)
#         file_storage.save(filepath)
#         with open(filepath, "r", errors="ignore") as ff:
#             content = ff.read()
#             docs.append(Document(page_content=content, metadata={"source": filename}))

#     # 4. Scrape website
#     scraped_text = scrape_website(site_url)
#     docs.append(Document(page_content=scraped_text, metadata={"source": site_url}))

#     # 5. Embed & store FAISS
#     embeddings = GoogleGenerativeAIEmbeddings(
#         model="models/embedding-001", google_api_key=api_key
#     )
#     splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
#     chunks = splitter.split_documents(docs)
#     vector_store = FAISS.from_documents(chunks, embeddings)
#     faiss_dir = os.path.join(tenant_dir, "faiss_store")
#     vector_store.save_local(faiss_dir)

#     # 6. Copy chatbot template
#     for fname in ["app.py", "chat_graph.py", "prompt.txt"]:
#         shutil.copy(os.path.join(TEMPLATE_DIR, fname), tenant_dir)

#     return True

# @app.route("/register-business", methods=["POST"])
# def register_business():
#     biz_name = request.form.get("business_name")
#     site_url = request.form.get("website_url")
#     api_key = request.form.get("api_key")
#     files = request.files.getlist("files")

#     biz_id = secure_filename(biz_name.lower().replace(" ", "_"))

#     process_business(
#         biz_id, site_url, api_key,
#         files_data=files,
#         json_data={"business": biz_name, "website": site_url}
#     )
#     return jsonify({"status": "success", "tenant_folder": f"tenants/{biz_id}"})


# if __name__ == "__main__":
#     app.run(port=5000, debug=True)

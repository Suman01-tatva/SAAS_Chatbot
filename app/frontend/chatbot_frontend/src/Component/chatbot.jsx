import React, { useState } from "react";
import axios from "axios";

function Chatbot() {
  const [botName, setBotName] = useState("");
  const [botDomain, setBotDomain] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [urls, setUrls] = useState([""]);
  const [files, setFiles] = useState([]);
  const [llmProvider, setLlmProvider] = useState("gemini");
  const [llmModel, setLlmModel] = useState("gemini-2.0-flash");
  const [apiKey, setApiKey] = useState("");
  const [embeddingModel, setEmbeddingModel] = useState("models/embedding-001");
  const [faissStoreName, setFaissStoreName] = useState("dynamic_bot_store");

  const handleUrlChange = (value, index) => {
    const updatedUrls = [...urls];
    updatedUrls[index] = value;
    setUrls(updatedUrls);
  };

  const addUrlField = () => setUrls([...urls, ""]);
  const removeUrlField = (index) => {
    setUrls(urls.filter((_, i) => i !== index));
  };

  const handleFilesChange = (e) => {
    setFiles([...e.target.files]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      bot_name: botName,
      bot_domain: botDomain,
      system_prompt: systemPrompt,
      knowledge_sources: {
        urls: urls.filter((url) => url.trim() !== ""),
        files: files.map((file) => file.name), // Names only, upload handled separately
      },
      llm: {
        provider: llmProvider,
        model: llmModel,
        api_key: apiKey,
      },
      embedding_model: embeddingModel,
      faiss_store_name: faissStoreName,
      created_at: new Date().toISOString(),
    };

    // Create form data for files + JSON
    const formData = new FormData();
    formData.append("metadata", JSON.stringify(payload));
    files.forEach((file) => formData.append("files", file));

    try {
      const res = await axios.post("http://localhost:5000/api/create-bot", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      alert("Chatbot created successfully!");
      console.log(res.data);
    } catch (err) {
      console.error(err);
      alert("Error creating chatbot.");
    }
  };

  return (
    <div style={{ padding: "20px", maxWidth: "600px", margin: "auto" }}>
      <h1>Create Your Chatbot</h1>
      <form onSubmit={handleSubmit}>
        <label>Bot Name</label>
        <input value={botName} onChange={(e) => setBotName(e.target.value)} required />

        <label>Bot Domain</label>
        <input value={botDomain} onChange={(e) => setBotDomain(e.target.value)} required />

        <label>System Prompt</label>
        <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} required />

        <h3>Knowledge Source URLs</h3>
        {urls.map((url, index) => (
          <div key={index} style={{ display: "flex", gap: "10px", marginBottom: "5px" }}>
            <input
              value={url}
              onChange={(e) => handleUrlChange(e.target.value, index)}
              placeholder="Enter website URL"
            />
            {index > 0 && <button type="button" onClick={() => removeUrlField(index)}>Remove</button>}
          </div>
        ))}
        <button type="button" onClick={addUrlField}>+ Add URL</button>

        <h3>Upload Knowledge Files</h3>
        <input type="file" multiple onChange={handleFilesChange} />

        <h3>LLM Configuration</h3>
        <label>Provider</label>
        <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)}>
          <option value="gemini">Gemini</option>
          <option value="openai">OpenAI</option>
        </select>

        <label>Model</label>
        <input value={llmModel} onChange={(e) => setLlmModel(e.target.value)} />

        <label>API Key</label>
        <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} required />

        <label>Embedding Model</label>
        <input value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)} />

        <label>FAISS Store Name</label>
        <input value={faissStoreName} onChange={(e) => setFaissStoreName(e.target.value)} />

        <br />
        <button type="submit" style={{ marginTop: "20px" }}>Create Chatbot</button>
      </form>
    </div>
  );
}

export default Chatbot;

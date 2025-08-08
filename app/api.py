# api.py
import os
import uuid
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTasks
from dotenv import load_dotenv
from celery import Celery

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Celery config
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_routes = {"worker.create_bot_task": {"queue": "ingest"}}

app = FastAPI()
UPLOAD_DIR = os.path.abspath("uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
BOTS_DIR = os.path.abspath("bots")
os.makedirs(BOTS_DIR, exist_ok=True)

@app.post("/create-bot")
async def create_bot_endpoint(
    background_tasks: BackgroundTasks,
    payload: str = Form(...),
    files: list[UploadFile] | None = None
):
    try:
        config = json.loads(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload JSON: {e}")

    bot_name = config.get("bot_name") or f"bot_{uuid.uuid4().hex[:8]}"
    bot_id = f"{bot_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
    bot_dir = os.path.join(BOTS_DIR, bot_id)
    os.makedirs(bot_dir, exist_ok=True)

    # Save uploaded files (if any) into uploads/<bot_id> and pass paths in config
    saved_files = []
    if files:
        bot_upload_dir = os.path.join(UPLOAD_DIR, bot_id)
        os.makedirs(bot_upload_dir, exist_ok=True)
        for f in files:
            save_path = os.path.join(bot_upload_dir, f.filename)
            with open(save_path, "wb") as wf:
                wf.write(await f.read())
            saved_files.append(save_path)

    # Persist initial meta to bot_dir
    config_path = os.path.join(bot_dir, "bot_config.json")
    with open(config_path, "w", encoding="utf-8") as fh:
        # Attach uploaded file paths so worker can pick them up
        config["_uploaded_files"] = saved_files
        json.dump(config, fh, ensure_ascii=False, indent=2)

    # Enqueue Celery task to build the bot (async)
    celery_result = celery_app.send_task("worker.create_bot_task", args=[bot_dir])
    return JSONResponse({
        "status": "queued",
        "bot_id": bot_id,
        "bot_dir": bot_dir,
        "task_id": celery_result.id
    })
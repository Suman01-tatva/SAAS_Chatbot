# worker.py
import os
import json
from celery import Celery
from dotenv import load_dotenv
from ingestion import create_bot_from_config

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)

@celery.task(name="worker.create_bot_task", bind=True, soft_time_limit=1800)
def create_bot_task(self, bot_dir: str):
    """
    Celery task entrypoint. It receives the path to the folder containing bot_config.json
    """
    config_path = os.path.join(bot_dir, "bot_config.json")
    if not os.path.exists(config_path):
        raise Exception("bot_config.json not found")

    with open(config_path, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    # call ingestion.provision function that will:
    # - ingest urls + files
    # - create FAISS index
    # - populate bot directory with chatbot app & graph templates
    try:
        create_bot_from_config(config, bot_dir)
    except Exception as e:
        # In production: save error to DB or send webhook
        raise e

    return {"status": "completed", "bot_dir": bot_dir}

import json
import os

BASE_DIR = os.path.dirname(__file__)


def load_messages(filename):
    with open(os.path.join(BASE_DIR, f"../messages/{filename}"), encoding="utf-8") as f:
        return json.load(f)

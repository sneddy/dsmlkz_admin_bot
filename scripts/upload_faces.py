import os
import json
import requests
from uuid import uuid4
from urllib.parse import urlparse
from pathlib import Path
from supabase import create_client
import supabase
from configs.config import SUPABASE_URL, SUPABASE_KEY, FACES_BUCKET, USER_ID
import ipdb
import mimetypes


def download_image(url, save_path):
    try:
        r = requests.get(url)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"❌ Failed to download {url}: {e}")
        return False


def upload_image(local_path, storage_path):
    try:
        # Get correct content-type
        content_type, _ = mimetypes.guess_type(local_path)
        content_type = content_type or "application/octet-stream"

        # Build only valid headers
        file_options = {"content-type": content_type}

        # Upload using path string
        supabase.storage.from_(bucket_name).upload(
            path=storage_path, file=local_path, file_options=file_options
        )

        print(f"✅ Uploaded: {storage_path}")
        return f"{bucket_name}/{storage_path}"
    except Exception as e:
        print(f"❌ Failed to upload {local_path}: {e}")
        return None


def process_member(m):
    slug = m["name"].replace(" ", "_").replace("&nbsp;", "_")
    ext = Path(urlparse(m["image_url"]).path).suffix or ".jpg"
    local_filename = f"tmp/{uuid4()}{ext}"
    storage_path = f"{image_folder}/{slug}{ext}"
    if not download_image(m["image_url"], local_filename):
        return
    uploaded_path = upload_image(local_filename, storage_path)
    if not uploaded_path:
        return

    db_data = {
        "name": m["name"],
        "title": m.get("title"),
        "title_ru": m.get("title_ru"),
        "description": m.get("description"),
        "description_ru": m.get("description_ru"),
        "location": m.get("location"),
        "image_path": uploaded_path,
        "linkedin": m.get("linkedin"),
        "website": m.get("website"),
        "telegram": m.get("telegram"),
        "kaggle": m.get("kaggle"),
        "display_order": m.get("display_order"),
        "user_id": USER_ID,
    }

    try:
        supabase.table("community_faces").insert(db_data).execute()
        print(f"✅ Inserted {m['name']}")
    except Exception as e:
        print(f"❌ DB insert failed for {m['name']}: {e}")


if __name__ == "__main__":
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    bucket_name = FACES_BUCKET
    image_folder = "faces"

    # Load member list
    with open("faces.json", "r") as f:
        members = json.load(f)["communityMembers"]

    os.makedirs("tmp", exist_ok=True)

    # Process all members
    for member in members[1:]:
        process_member(member)

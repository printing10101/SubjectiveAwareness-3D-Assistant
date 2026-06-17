"""Download HuggingFace model to local directory using direct HTTP."""
import os

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

requests.packages.urllib3.disable_warnings()
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

MODEL_NAME = "unsloth/Llama-3.2-1B-Instruct-bnb-4bit"
LOCAL_DIR = "c:/Users/Lenovo/Desktop/微信程序开发/models/base_model"

os.makedirs(LOCAL_DIR, exist_ok=True)

# Get file list from API
api_url = f"https://huggingface.co/api/models/{MODEL_NAME}"
r = requests.get(api_url, verify=False, timeout=30)
data = r.json()
files = [s["rfilename"] for s in data.get("siblings", [])]
print(f"Model: {MODEL_NAME}")
print(f"Total files: {len(files)}")
for f in files:
    print(f"  {f}")

skip_extensions = (".md", ".gitattributes")


def download_file(filename):
    if any(filename.endswith(ext) for ext in skip_extensions):
        return filename, "skipped"
    filepath = os.path.join(LOCAL_DIR, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
        return filename, "cached"
    url = f"https://huggingface.co/{MODEL_NAME}/resolve/main/{filename}"
    try:
        r = requests.get(url, verify=False, stream=True, timeout=300)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            sz = os.path.getsize(filepath)
            return filename, f"ok ({sz/1024/1024:.1f}MB)"
        else:
            return filename, f"failed ({r.status_code})"
    except Exception as e:
        return filename, f"error ({e})"


print("\nDownloading files...")
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(download_file, f): f for f in files}
    for future in as_completed(futures):
        name, status = future.result()
        print(f"  {name}: {status}")

# Create config symlink for config.json -> adapter_config.json
config_path = os.path.join(LOCAL_DIR, "config.json")
adapter_path = os.path.join(LOCAL_DIR, "adapter_config.json")
if os.path.exists(config_path) and not os.path.exists(adapter_path):
    import shutil
    shutil.copy2(config_path, adapter_path)
    print("Created adapter_config.json from config.json")

print("\nDownload complete!")
print(f"Model saved to: {LOCAL_DIR}")
for f in sorted(os.listdir(LOCAL_DIR)):
    fp = os.path.join(LOCAL_DIR, f)
    sz = os.path.getsize(fp)
    print(f"  {f}: {sz/1024/1024:.1f}MB" if sz > 1024*1024 else f"  {f}: {sz}bytes")

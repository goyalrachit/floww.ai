import os
from sentence_transformers import SentenceTransformer

# Set persistent Hugging Face cache directory (used by Render's /data volume)
HF_CACHE_DIR = "/data/huggingface"
MODEL_CACHE_DIR = os.path.join(HF_CACHE_DIR, "models")

os.environ["HF_HOME"] = HF_CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = MODEL_CACHE_DIR

model_name = 'all-MiniLM-L6-v2'

print(f"[INFO] Setting Hugging Face cache dir to: {MODEL_CACHE_DIR}")
print(f"[INFO] Preloading model '{model_name}' to cache...")

try:
    model = SentenceTransformer(model_name)
    print("[SUCCESS] Model downloaded and cached successfully.")
    print(f"[INFO] Model path: {model.cache_folder}")
except Exception as e:
    print(f"[ERROR] Failed to preload model '{model_name}': {str(e)}")
    exit(1)

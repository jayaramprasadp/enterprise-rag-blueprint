import os
from fastembed import TextEmbedding, SparseTextEmbedding

# Explicitly set the target cache directories
os.environ["HF_HOME"] = "/app/hf_cache"
os.environ["FASTEMBED_CACHE_PATH"] = "/app/fastembed_cache"

print("📥 Initiating enterprise model pre-download sequence...")

# Direct model generation download trigger
print("-> Downloading Dense Embeddings model...")
dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

print("-> Downloading Sparse Embeddings model...")
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

print("✅ All open-source model weights successfully cached locally!")
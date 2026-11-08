import os
import streamlit as st

# Direct FastEmbed and Hugging Face to read from your pre-baked image cache
os.environ["HF_HOME"] = "/app/hf_cache"
os.environ["FASTEMBED_CACHE_PATH"] = "/app/fastembed_cache"

from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding
import google.generativeai as genai

QDRANT_HOST = os.getenv("QDRANT_HOST", "http://localhost:6333")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
COLLECTION_NAME = "enterprise_knowledge"

@st.cache_resource
def init_engines():
    q_client = QdrantClient(url=QDRANT_HOST)
    st.sidebar.info("🤖 Loading pre-baked BGE Dense + BM25 Sparse Models...")
    dense_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        
    return q_client, dense_model, sparse_model

qdrant_client, dense_engine, sparse_engine = init_engines()

# FIX: Explicitly name the dense vector configuration dictionary key as "default"
try:
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "default": models.VectorParams(
                    size=384,  # bge-small-en vector dimension
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams()
            }
        )
except Exception as e:
    st.error(f"Failed initializing collection: {str(e)}")

st.set_page_config(page_title="🛡️ Secure Hybrid RAG", layout="wide")
st.title("🛡️ Enterprise Secure Hybrid RAG Cluster")
st.success("🔒 Isolated System Status: 100% Air-Gapped Local Vectorization Active!")

st.sidebar.markdown("### 🔑 Identity & Governance")
user_dept = st.sidebar.selectbox("Your Department", ["Finance", "Engineering", "HR"])
user_role = st.sidebar.selectbox("Your Security Level", ["User", "Manager", "Executive"])

st.sidebar.markdown("### 📥 Document Ingestion Engine")
uploaded_file = st.sidebar.file_uploader("Upload reference documents (TXT format only):", type=["txt"])

if uploaded_file is not None:
    raw_text = uploaded_file.read().decode("utf-8")
    if st.sidebar.button("Embed & Index Documents"):
        with st.sidebar.spinner("Generating Local Embeddings..."):
            chunks = [c.strip() for c in raw_text.split("\n\n") if c.strip()]
            
            # Generate vectors from pre-downloaded cache weights
            dense_vectors = list(dense_engine.embed(chunks))
            sparse_vectors = list(sparse_engine.embed(chunks))
            
            points = []
            for i, chunk in enumerate(chunks):
                sparse_val = models.SparseVector(
                    indices=sparse_vectors[i].indices.tolist(),
                    values=sparse_vectors[i].values.tolist()
                )
                
                points.append(models.PointStruct(
                    id=i,
                    vector={
                        "default": dense_vectors[i].tolist(),
                        "text-sparse": sparse_val
                    },
                    payload={
                        "page_content": chunk,
                        "department": user_dept.lower(),
                        "security_level": user_role.lower()
                    }
                ))
            
            qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
            st.sidebar.success(f"Indexed {len(chunks)} chunks with Hybrid Vectors!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_query := st.chat_input("Ask a question about the reference library:"):
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("assistant"):
        if not GEMINI_KEY:
            st.error("Missing Gemini Key configuration. Check cluster Secrets.")
            st.stop()
            
        with st.spinner("Executing Hybrid Query (Dense Semantic + Sparse Keyword)..."):
            # Format dense query vector list
            query_dense = list(dense_engine.embed([user_query]))[0].tolist()
            
            # Format sparse query vector list
            query_sparse_raw = list(sparse_engine.embed([user_query]))[0]
            query_sparse = models.SparseVector(
                indices=query_sparse_raw.indices.tolist(),
                values=query_sparse_raw.values.tolist()
            )
            
            security_filter = models.Filter(must=[
                models.FieldCondition(key="department", match=models.MatchValue(value=user_dept.lower())),
                models.FieldCondition(key="security_level", match=models.MatchValue(value=user_role.lower()))
            ])
            
            # Run pre-filtered dual search
            query_results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                prefetch=[
                    models.Prefetch(query=query_dense, using="default", filter=security_filter, limit=10),
                    models.Prefetch(query=query_sparse, using="text-sparse", filter=security_filter, limit=10)
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=3
            )
            
            context_chunks = [point.payload.get("page_content", "") for point in query_results.points]
            context = "\n".join(context_chunks) if context_chunks else "No authorized context matches found."
            
            with st.expander("🔧 Hybrid Retrieval Debugger Metadata", expanded=False):
                st.write(f"Matches found: {len(query_results.points)}")
                for point in query_results.points: 
                    st.json({"score": point.score, "payload": point.payload})
                    
            model = genai.GenerativeModel('gemini-3.8-flash')
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
            prompt = f"You are a secure corporate assistant. Context from database:\n{context}\n\nRecent History:\n{history_context}\n\nQuestion: {user_query}\n\nAnswer strictly using provided context."
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})


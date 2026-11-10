import os
import uuid
import gc
import streamlit as st
from pypdf import PdfReader

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

# Helper Function: Text Chunking by Words with Moving Windows
def chunk_text_by_words(text, chunk_size=150, overlap=25):
    """
    Slices raw document string into chunks bounded by word lengths.
    150 words roughly translates to 200 tokens, staying perfectly safe 
    within the 512 max limit of bge-small-en-v1.5.
    """
    words = text.split()
    chunks = []
    if len(words) <= chunk_size:
        return [text] if text.strip() else []
        
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk.strip())
        if i + chunk_size >= len(words):
            break
    return chunks

qdrant_client, dense_engine, sparse_engine = init_engines()

# Setup named multi-vector collection
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
uploaded_file = st.sidebar.file_uploader("Upload reference documents:", type=["txt", "pdf"])

if uploaded_file is not None:
    # MODIFICATION: Prepare structural storage for pages and text
    pages_to_process = []  # List of tuples: (page_text, page_number)
    
    if uploaded_file.name.endswith(".pdf"):
        try:
            pdf_reader = PdfReader(uploaded_file)
            for idx, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    # PDF pages are 0-indexed internally, add 1 for human reading (Page 1, Page 2...)
                    pages_to_process.append((text, idx + 1))
        except Exception as pdf_err:
            st.sidebar.error(f"Failed to extract PDF text: {str(pdf_err)}")
    else:
        # TXT files don't have natural pages; treat the whole file as "Page 1"
        raw_text = uploaded_file.read().decode("utf-8")
        if raw_text.strip():
            pages_to_process.append((raw_text, 1))

    if pages_to_process and st.sidebar.button("Embed & Index Documents"):
        with st.sidebar.spinner("Generating Local Embeddings..."):
            
            # MODIFICATION: Group all processing tasks across structural elements
            final_chunks = []
            final_page_mappings = []
            
            for page_text, page_num in pages_to_process:
                page_chunks = chunk_text_by_words(page_text, chunk_size=150, overlap=25)
                for chunk in page_chunks:
                    final_chunks.append(chunk)
                    final_page_mappings.append(page_num)
            
            if not final_chunks:
                st.sidebar.warning("No readable text extracted from document.")
                st.stop()
                
            # Generate vectors simultaneously 
            dense_vectors = list(dense_engine.embed(final_chunks))
            sparse_vectors = list(sparse_engine.embed(final_chunks))
            
            points = []
            for i, chunk in enumerate(final_chunks):
                sparse_val = models.SparseVector(
                    indices=sparse_vectors[i].indices.tolist(),
                    values=sparse_vectors[i].values.tolist()
                )
                
                unique_point_id = str(uuid.uuid4())
                
                # MODIFICATION: Inject 'page_number' context directly into payload
                points.append(models.PointStruct(
                    id=unique_point_id,
                    vector={
                        "default": dense_vectors[i].tolist(),
                        "text-sparse": sparse_val
                    },
                    payload={
                        "page_content": chunk,
                        "document_name": uploaded_file.name,
                        "page_number": final_page_mappings[i],
                        "department": user_dept.lower(),
                        "security_level": user_role.lower()
                    }
                ))
            
            qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)
            st.sidebar.success(f"Indexed {len(final_chunks)} chunks with structural metadata!")
            
            del dense_vectors, sparse_vectors, points, final_chunks, final_page_mappings
            gc.collect()

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
            query_dense = list(dense_engine.embed([user_query]))[0].tolist()
            
            query_sparse_raw = list(sparse_engine.embed([user_query]))[0]
            query_sparse = models.SparseVector(
                indices=query_sparse_raw.indices.tolist(),
                values=query_sparse_raw.values.tolist()
            )
            
            security_filter = models.Filter(must=[
                models.FieldCondition(key="department", match=models.MatchValue(value=user_dept.lower())),
                models.FieldCondition(key="security_level", match=models.MatchValue(value=user_role.lower()))
            ])
            
            query_results = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                prefetch=[
                    models.Prefetch(query=query_dense, using="default", filter=security_filter, limit=10),
                    models.Prefetch(query=query_sparse, using="text-sparse", filter=security_filter, limit=10)
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=3
            )
            
            # MODIFICATION: Format prompt context track to provide document sources and pages to Gemini
            context_chunks = []
            for point in query_results.points:
                p_text = point.payload.get("page_content", "")
                p_doc = point.payload.get("document_name", "Unknown File")
                p_num = point.payload.get("page_number", 1)
                context_chunks.append(f"[Source: {p_doc} | Page: {p_num}]\n{p_text}")
                
            context = "\n\n".join(context_chunks) if context_chunks else "No authorized context matches found."
            
            with st.expander("🔧 Hybrid Retrieval Debugger Metadata", expanded=False):
                st.write(f"Matches found: {len(query_results.points)}")
                for point in query_results.points: 
                    st.json({"score": point.score, "payload": point.payload})
                    
            model = genai.GenerativeModel('gemini-3.8-flash')
            history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
            
            # MODIFICATION: Instructed Gemini to use and cite the structural markers provided
            prompt = (
                f"You are a secure corporate assistant. Context from database:\n{context}\n\n"
                f"Recent History:\n{history_context}\n\n"
                f"Question: {user_query}\n\n"
                f"Answer strictly using provided context. Explicitly cite the document name and page number "
                f"where your answer was pulled from."
            )
            
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            del query_dense, query_sparse_raw, query_sparse, query_results
            gc.collect()

# enterprise-rag-blueprint
Decoupled privacy-first enterprise RAG architecture using microservices.

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:
   python -m pip install -r app/requirements.txt
3. Start Qdrant locally on port 6333.
4. Run the UI:
   streamlit run app/main.py

Set the environment variable GEMINI_API_KEY if you want the assistant to call Gemini.

# 🛡️ Enterprise Air-Gapped GenAI secure Hybrid RAG Architecture

A production-grade, highly secure, and privacy-focused Hybrid Retrieval-Augmented Generation (RAG) blueprint [1.37]. This decoupled microservices architecture is engineered for enterprise environments where data sovereignty is paramount, ensuring zero data exfiltration risks by utilizing fully containerized local embedding layers paired with role-based database constraints [6.26, 1.37].

## 🏗️ System Architecture & Service Boundaries
The application is entirely decoupled into isolated containerized services to guarantee independent scaling, data resilience, and microservice firewall protection [7.29]:
* **Presentation Layer:** Python Streamlit interface orchestrating asynchronous multi-user chat history threads [5.547].
* **Vector Indexing & Storage Layer:** Qdrant Vector Database utilizing dual-vector mappings (named `"default"` for BGE Dense Semantic arrays and `"text-sparse"` for BM25 Keyword indices) combined with pre-filtered Reciprocal Rank Fusion (RRF) [1.37].
* **Inference Layer:** Fully air-gapped container image containing pre-downloaded, baked-in open-source model weights (`BAAI/bge-small-en-v1.5` and `Qdrant/bm25`) to bypass runtime internet dependencies, integrated with `google-genai` (Gemini 3.8-Flash) for contextual synthesis [1.37, 5.295].

---

## 👥 User Guide (User Perspective)

This application serves as a **Secure Corporate Librarian**. It acts as an intelligent chat assistant but strictly filters information based on your departmental clearance pass key.

### 1. Navigating the Security Controls
When you launch the web portal, look at the **left-hand sidebar panel** labeled `🔑 Identity & Governance`. Before uploading or asking questions, you must establish your corporate identity:
* **Your Department:** Select your target domain (`Finance`, `Engineering`, or `HR`).
* **Your Security Level:** Choose your clearance depth (`User`, `Manager`, or `Executive`).

### 2. Ingesting Corporate Files
1. Go to the `📥 Document Ingestion Engine` section in the sidebar.
2. Click **Browse files** and upload any standard text file (`.txt`).
3. Set your sidebar to the identity that **owns** this file (e.g., Department: `Finance`, Security: `Manager`).
4. Click the **Embed & Index Documents** button. 
5. *The system will locally chunk the text, generate dual-vector maps, lock the data with your clearance tags, and store it permanently.*

### 3. Interacting with the Conversational Chat Loop
* Type any question into the chat input bar at the bottom of the main dashboard page and press enter.
* **The Security Firewall Rule:** The database runs an instant verification check. If you try to ask about `Finance` files while your sidebar is set to `Engineering`, the database blocks the records entirely, the app reports `No authorized context matches found`, and the assistant will politely refuse to leak the information.
* **Back-and-Forth Thread Context:** The chat loop maintains a sliding-window session history, allowing you to ask follow-up questions naturally while keeping your context secure.

---

## 🛠️ Infrastructure Deployment Guide (Operator Perspective)

### 📋 Prerequisites
* Kubernetes Cluster (e.g., Local **Kind v0.24+** or Managed **Google GKE**) [1.37].
* `kubectl` CLI installed and connected to the active cluster context [1.37].
* Google AI Studio developer API Key [1.14].

### 🚀 3-Step Local Deployment

#### Step 1: Securely Inject the Cloud API Key Credentials
Create an encrypted Kubernetes Secret to store your Gemini token securely in the cluster's memory workspace, bypassing any text file exposures:
```bash
kubectl create secret generic ai-secrets --from-literal=api-key="YOUR_ACTUAL_GEMINI_KEY"
```

#### Step 2: Compile the Air-Gapped Container Layers
To compile your custom Python application with the heavy open-source model weights pre-baked into the image disk, build and inject it straight into your cluster's node store:
```bash
# Build the local Docker image layers
docker build -t streamlit-rag-app:latest .

# Inject the completed bundle directly into your Kind node cache
kind load docker-image streamlit-rag-app:latest --name erag-cluster
```

#### Step 3: Deploy the Declarative Microservice Manifests
Push your manual multi-tier blueprint manifest file live to your cluster to provision persistent storage, run your isolated database firewall, and start the frontend interface [1.37]:
```bash
kubectl apply -f k8s/rag-stack.yaml
```
Verify that all pods successfully transition into a clean, stable state:
```bash
kubectl get pods,pvc,svc
```

#### Step 4: Open the Secure Network Tunnel Link
To route the internal container network interface directly to your local web browser, map the traffic port:
```bash
kubectl port-forward svc/streamlit-service 8501:8501
```
*Open your web browser pointing to `http://localhost:8501` to use the application.*

---

## 📂 Project Directory Map
```text
├── app/
│   ├── download_models.py   # Code architecture cache pre-downloader script
│   ├── main.py              # Core Streamlit app UI and RAG execution logic
│   └── requirements.txt     # Locked pipeline dependencies (Streamlit, Qdrant-Client)
├── k8s/
│   └── rag-stack.yaml       # Manual Native K8s Manifest File (Deployments, Services, PVC)
├── Dockerfile               # Multi-tier container build system definition instructions
└── README.md                # System documentation manifest
```

---
*Disclaimer: This is an independent, personal research and development project conducted entirely on personal infrastructure outside of professional hours. It holds no affiliation with any corporate entity or employer.*

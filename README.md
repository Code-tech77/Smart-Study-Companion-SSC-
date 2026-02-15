# 📚 Smart Study Companion (SSC)

**Smart Study Companion (SSC)** is a **fully local, privacy first study assistant** designed for university students who want fast, accurate answers directly from their **own lecture PDFs**  without relying on cloud-based AI services or file upload limits.

This project was built to solve a real academic problem:

> LLM platforms are powerful, but lecture notes are often too large, restricted, or privacy sensitive to upload.

SSC removes that limitation entirely.

---

## 🚀 Why Smart Study Companion?

- 🔒 **100% Local & Secure** : no data leaves your machine  
- 📄 **Built for real lecture PDFs** (large, detailed, multi file)  
- 🚫 **No AI APIs, no subscriptions, no upload caps**  
- 🧠 **Context aware answers** from your own notes  
- 🗂️ **Multiple chat sessions**, each with its own PDFs and history  

Built by a university student, **for university students**.

---

## ✨ Key Features

- Upload multiple PDFs per study session  
- Ask natural language questions based on lecture content  
- Get **concise, relevant answers** with source attribution  
- Separate chat sessions for different modules  
- Chat history preserved per session (while server runs)  
- Modern, animated UI with smooth UX  

---

## 🛠️ Technology Stack (Toolkit)

**Backend**
- Python
- Flask (REST API & session handling)

**Document Processing**
- PyMuPDF (fitz) : local PDF text extraction

**Search & Ranking**
- TF-IDF Vectorization (scikit learn)
- Cosine Similarity for relevance scoring

**Frontend**
- HTML
- CSS (custom dark UI & animations)
- Vanilla JavaScript

**Security & Design**
- Fully offline
- No external APIs
- No cloud services
- No data sharing

---

## 🧠 How It Works (High Level)

1. PDFs are uploaded and processed **locally**
2. Text is chunked and indexed using **TF-IDF**
3. User questions are vectorized and compared using **cosine similarity**
4. The most relevant section is returned as a concise answer
5. Each chat session maintains its own PDFs and history

---

## 📦 Installation & Setup

### Prerequisites
- Python **3.9+**
- pip

### Install dependencies
```bash
pip install flask pymupdf scikit-learn
```
### 🎯 Use Cases
	•	University lecture revision
	•	Exam preparation
	•	Large module handouts
	•	Privacy-sensitive academic notes
	•	Offline studying

⸻

### 🔐 Privacy & Security

#### SSC is privacy first by design:
	•	No internet connection required after setup
	•	No third party APIs
	•	No telemetry or tracking
	•	All data stays on your local machine
  
⸻

### 👨‍💻 Author
Mohammed Zuoriki
Cybersecurity Student | Aspiring Cloud Security Architect
<br> LinkedIn: https://www.linkedin.com/in/mohammed-zuoriki-856133250/

⸻

### ⭐ Contributing

Contributions, feedback, and ideas are welcome.
Feel free to fork the repository or open an issue.

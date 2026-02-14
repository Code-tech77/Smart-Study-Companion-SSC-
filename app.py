from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import fitz
import re
from datetime import datetime, timedelta
from uuid import uuid4

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = "pdfs"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=7)

# ---------------- SESSION STORE (in-memory) ----------------
# Each session = one "chat" with its own PDFs + index + history.
sessions = {}  # session_id -> dict
session_counter = 0


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def make_session():
    global session_counter
    session_counter += 1

    sid = str(uuid4())
    sessions[sid] = {
        "id": sid,
        "name": f"Chat {session_counter}",
        "created_at": now_iso(),
        "pdfs": {},          # filename -> text
        "chunks": {},        # filename -> list[str]
        "history": [],       # list of {"role": "...", "text": "...", "meta": "...", "ts": "..."}
        "tfidf_vectorizer": None,
        "tfidf_matrix": None,
        "chunk_sources": []  # list of (filename, chunk)
    }
    return sessions[sid]


def get_session(session_id: str):
    if not session_id or session_id not in sessions:
        # If missing/invalid, create a new one (safe default)
        return make_session()
    return sessions[session_id]


# ---------------- PDF + SEARCH ----------------
def extract_text_from_pdf(path: str, max_pages: int | None = 40) -> str:
    """Extract text from PDF. Limit pages for speed (set None for full)."""
    text = []
    pdf = fitz.open(path)
    for i, page in enumerate(pdf):
        if max_pages is not None and i >= max_pages:
            break
        text.append(page.get_text("text"))
    pdf.close()
    return "\n".join(text)


def chunk_text(text: str, max_chars: int = 1600):
    raw_parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for p in raw_parts:
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            start = 0
            while start < len(p):
                chunks.append(p[start:start + max_chars].strip())
                start += max_chars
    return chunks


def clean_short_answer(text: str, max_chars: int = 260) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "I found a relevant section, but it contains no readable text."

    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join(sentences[:2]).strip()
    if len(short) < 80 and len(sentences) > 2:
        short = " ".join(sentences[:3]).strip()

    if len(short) > max_chars:
        short = short[:max_chars].rsplit(" ", 1)[0].strip() + "…"
    return short


def build_search_index(sess: dict):
    """Build TF-IDF index across all chunks for a session."""
    chunk_sources = []
    for pdf_name, chunks in sess["chunks"].items():
        for ch in chunks:
            chunk_sources.append((pdf_name, ch))

    sess["chunk_sources"] = chunk_sources

    if not chunk_sources:
        sess["tfidf_vectorizer"] = None
        sess["tfidf_matrix"] = None
        return

    docs = [c[1] for c in chunk_sources]
    vec = TfidfVectorizer(lowercase=True, stop_words="english", max_features=25000)
    mat = vec.fit_transform(docs)

    sess["tfidf_vectorizer"] = vec
    sess["tfidf_matrix"] = mat


def search_pdfs(sess: dict, query: str):
    if sess["tfidf_vectorizer"] is None or sess["tfidf_matrix"] is None or not sess["chunk_sources"]:
        return {"answer": "Upload PDFs first so I can search them.", "source": None, "score": 0.0}

    q = (query or "").strip()
    if not q:
        return {"answer": "Type a question first.", "source": None, "score": 0.0}

    q_vec = sess["tfidf_vectorizer"].transform([q])
    sims = cosine_similarity(q_vec, sess["tfidf_matrix"]).flatten()

    best_idx = int(sims.argmax())
    best_score = float(sims[best_idx])

    # Threshold to avoid random matches
    if best_score < 0.08:
        return {"answer": "I couldn’t find a clear match in this chat’s PDFs. Try keywords from headings.", "source": None, "score": best_score}

    pdf_name, chunk = sess["chunk_sources"][best_idx]
    return {"answer": clean_short_answer(chunk, max_chars=260), "source": pdf_name, "score": best_score}


def add_history(sess: dict, role: str, text: str, meta: str | None = None):
    sess["history"].append({
        "role": role,  # "user" | "bot" | "system"
        "text": text,
        "meta": meta,
        "ts": now_iso()
    })


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/sessions", methods=["GET"])
def api_sessions():
    # List session summaries
    out = []
    for sid, s in sessions.items():
        out.append({
            "id": s["id"],
            "name": s["name"],
            "created_at": s["created_at"],
            "pdf_count": len(s["pdfs"]),
            "message_count": len(s["history"])
        })
    # newest first
    out.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify({"sessions": out})


@app.route("/api/session/new", methods=["POST"])
def api_new_session():
    s = make_session()
    add_history(s, "system", "New chat created. Upload PDFs to begin.")
    return jsonify({
        "session": {
            "id": s["id"],
            "name": s["name"],
            "created_at": s["created_at"]
        },
        "history": s["history"],
        "pdf_list": sorted(list(s["pdfs"].keys()))
    })


@app.route("/api/session/<session_id>", methods=["GET"])
def api_get_session(session_id):
    s = get_session(session_id)
    return jsonify({
        "session": {"id": s["id"], "name": s["name"], "created_at": s["created_at"]},
        "history": s["history"],
        "pdf_list": sorted(list(s["pdfs"].keys()))
    })


@app.route("/upload", methods=["POST"])
def upload():
    # session_id comes from form data
    session_id = request.form.get("session_id", "")
    sess = get_session(session_id)

    files = request.files.getlist("pdfs")
    messages = []

    # Store PDFs under per-session folder so chats stay separated
    session_dir = os.path.join(app.config["UPLOAD_FOLDER"], sess["id"])
    os.makedirs(session_dir, exist_ok=True)

    for file in files:
        filename = secure_filename(file.filename)
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(session_dir, filename)
        file.save(pdf_path)

        # Cache extracted text per session+file
        cache_path = pdf_path + ".txt"
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            messages.append(f"⚡ Used cache for {filename}")
        else:
            text = extract_text_from_pdf(pdf_path, max_pages=40)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
            messages.append(f"✅ Indexed {filename} (first 40 pages)")

        sess["pdfs"][filename] = text
        sess["chunks"][filename] = chunk_text(text, max_chars=1600)
        messages.append(f"📄 {filename}: {len(sess['chunks'][filename])} chunks ready")

    build_search_index(sess)

    for m in messages:
        add_history(sess, "system", m)

    return jsonify({
        "messages": messages if messages else ["⚠️ No PDFs were uploaded."],
        "pdf_list": sorted(list(sess["pdfs"].keys())),
        "session_id": sess["id"]
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    session_id = data.get("session_id", "")
    sess = get_session(session_id)

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"response": "Type a question first.", "source": None})

    add_history(sess, "user", f"You: {message}")

    result = search_pdfs(sess, message)
    bot_text = f"Assistant: {result['answer']}"
    meta = f"Source: {result['source']}" if result["source"] else None

    add_history(sess, "bot", bot_text, meta=meta)

    return jsonify({
        "response": result["answer"],
        "source": result["source"],
        "session_id": sess["id"]
    })


# ---------------- RUN ----------------
if __name__ == "__main__":
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Create one default session at boot (nice UX)
    if not sessions:
        s = make_session()
        add_history(s, "system", "Welcome back. Create a new chat or upload PDFs to start.")

    HOST = "127.0.0.1"
    PORT = 5022  # macOS-friendly
    print(f"Starting server at: http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)
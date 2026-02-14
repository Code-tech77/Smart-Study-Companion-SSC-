// ✅ NEW: Premium reload animation (does NOT change app functionality)
(function pageReloadAnimation(){
  const loader = document.getElementById("pageLoader");
  const fill = document.getElementById("loaderBarFill");
  if(!loader || !fill) return;

  loader.classList.remove("hidden");

  let p = 0;
  const timer = setInterval(() => {
    p = Math.min(92, p + Math.random() * 10);
    fill.style.width = `${p}%`;
  }, 220);

  window.addEventListener("load", () => {
    clearInterval(timer);
    fill.style.width = "100%";

    setTimeout(() => {
      loader.classList.add("hidden");
      setTimeout(() => loader.remove(), 520);
    }, 350);
  });
})();

// ---------- Existing code (unchanged logic) ----------
const chat = document.getElementById("chat");
const input = document.getElementById("input");
const send = document.getElementById("send");
const upload = document.getElementById("upload");
const pdfs = document.getElementById("pdfs");
const pdfList = document.getElementById("pdfList");

const sessionList = document.getElementById("sessionList");
const newChatBtn = document.getElementById("newChat");
const clearChatBtn = document.getElementById("clearChat");
const activeChatName = document.getElementById("activeChatName");
const activeChatMeta = document.getElementById("activeChatMeta");

const dropzone = document.getElementById("dropzone");

let currentSessionId = localStorage.getItem("ssc_session_id") || "";

// ---------- UI helpers ----------
function addBubble(text, who, meta=null, isTyping=false){
  const wrap = document.createElement("div");
  wrap.className = `msg ${who}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  if(isTyping){
    bubble.innerHTML = `
      <span class="typing">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </span>
    `;
  } else {
    bubble.textContent = text;
    if(meta){
      const m = document.createElement("div");
      m.className = "meta";
      m.textContent = meta;
      bubble.appendChild(m);
    }
  }

  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return wrap;
}

function clearChatView(){
  chat.innerHTML = "";
}

function renderPdfList(list){
  pdfList.innerHTML = "";
  if(!list || list.length === 0){
    pdfList.innerHTML = `<div class="hint">Upload PDFs to see them here.</div>`;
    return;
  }
  list.forEach(name => {
    const item = document.createElement("div");
    item.className = "pdf-item";
    item.textContent = name;
    pdfList.appendChild(item);
  });
}

function renderHistory(history){
  clearChatView();
  if(!history || history.length === 0){
    addBubble("Assistant: This chat is empty. Upload PDFs to begin.", "bot");
    return;
  }
  history.forEach(msg => {
    if(msg.role === "user"){
      addBubble(msg.text, "user");
    } else if(msg.role === "bot"){
      addBubble(msg.text, "bot", msg.meta || null);
    } else {
      addBubble(`Assistant: ${msg.text}`, "bot");
    }
  });
}

function renderSessions(list){
  sessionList.innerHTML = "";
  if(!list || list.length === 0){
    sessionList.innerHTML = `<div class="hint">No chats yet.</div>`;
    return;
  }

  list.forEach(s => {
    const item = document.createElement("div");
    item.className = "session-item" + (s.id === currentSessionId ? " active" : "");
    item.innerHTML = `
      <div class="session-left">
        <div class="session-name">${s.name}</div>
        <div class="session-meta">${s.pdf_count} PDF(s) • ${s.message_count} msg</div>
      </div>
      <div class="session-right">${new Date(s.created_at).toLocaleDateString()}</div>
    `;

    item.addEventListener("click", () => selectSession(s.id));
    sessionList.appendChild(item);
  });
}

function setActiveHeader(name, createdAt){
  activeChatName.textContent = name || "Chat";
  if(createdAt){
    activeChatMeta.textContent = `Created: ${new Date(createdAt).toLocaleString()}`;
  } else {
    activeChatMeta.textContent = "—";
  }
}

// ---------- API ----------
async function refreshSessions(){
  const res = await fetch("/api/sessions");
  const data = await res.json();
  renderSessions(data.sessions || []);
}

async function createNewSession(){
  const res = await fetch("/api/session/new", { method: "POST" });
  const data = await res.json();

  currentSessionId = data.session.id;
  localStorage.setItem("ssc_session_id", currentSessionId);

  setActiveHeader(data.session.name, data.session.created_at);
  renderPdfList(data.pdf_list || []);
  renderHistory(data.history || []);

  await refreshSessions();
}

async function loadSession(sessionId){
  const res = await fetch(`/api/session/${sessionId}`);
  const data = await res.json();

  currentSessionId = data.session.id;
  localStorage.setItem("ssc_session_id", currentSessionId);

  setActiveHeader(data.session.name, data.session.created_at);
  renderPdfList(data.pdf_list || []);
  renderHistory(data.history || []);

  await refreshSessions();
}

async function selectSession(sessionId){
  await loadSession(sessionId);
}

// ---------- Chat ----------
async function sendMessage(){
  const msg = input.value.trim();
  if(!msg) return;

  addBubble(`You: ${msg}`, "user");
  input.value = "";

  const typingNode = addBubble("", "bot", null, true);

  try{
    const res = await fetch("/chat", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({message: msg, session_id: currentSessionId})
    });
    const data = await res.json();

    typingNode.remove();
    const meta = data.source ? `Source: ${data.source}` : null;
    addBubble(`Assistant: ${data.response}`, "bot", meta);

    await refreshSessions();

  } catch(err){
    typingNode.remove();
    addBubble("Assistant: ⚠️ Backend error. Check terminal logs.", "bot");
  }
}

send.addEventListener("click", sendMessage);
input.addEventListener("keydown", (e) => {
  if(e.key === "Enter") sendMessage();
});

clearChatBtn.addEventListener("click", () => {
  clearChatView();
  addBubble("Assistant: Cleared view. Select the chat again to reload full history.", "bot");
});

// ---------- Upload ----------
upload.addEventListener("click", async () => {
  const files = pdfs.files;
  if(!files || files.length === 0){
    addBubble("Assistant: Choose one or more PDFs first.", "bot");
    return;
  }

  const fd = new FormData();
  for(const f of files) fd.append("pdfs", f);
  fd.append("session_id", currentSessionId);

  const typingNode = addBubble("", "bot", "Uploading & indexing PDFs…", true);

  try{
    const res = await fetch("/upload", {method:"POST", body: fd});
    const data = await res.json();

    typingNode.remove();
    (data.messages || []).forEach(m => addBubble(`Assistant: ${m}`, "bot"));
    renderPdfList(data.pdf_list || []);

    await refreshSessions();

  } catch(err){
    typingNode.remove();
    addBubble("Assistant: ⚠️ Upload failed. Check terminal logs.", "bot");
  }
});

// Drag UI
if (dropzone){
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });
  dropzone.addEventListener("drop", () => {
    dropzone.classList.remove("dragover");
  });
}

// New Chat
newChatBtn.addEventListener("click", async () => {
  await createNewSession();
});

// Boot
(async function init(){
  await refreshSessions();

  if(currentSessionId){
    try{
      await loadSession(currentSessionId);
      return;
    }catch{}
  }
  await createNewSession();
})();
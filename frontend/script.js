let token = null;

// -------------------------
// Auth Functions
// -------------------------
async function signup() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const msg = document.getElementById("auth-msg");

  if (!email || !password) { msg.textContent = "Enter email & password"; return; }

  try {
    const res = await fetch("http://127.0.0.1:8000/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) throw new Error(`Signup failed: ${res.status}`);
    const data = await res.json();
    token = data.access_token;
    showMainSection();
  } catch (e) { msg.textContent = e.message; }
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const msg = document.getElementById("auth-msg");

  if (!email || !password) { msg.textContent = "Enter email & password"; return; }

  try {
    const res = await fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) throw new Error(`Login failed: ${res.status}`);
    const data = await res.json();
    token = data.access_token;
    showMainSection();
  } catch (e) { msg.textContent = e.message; }
}

function logout() {
  token = null;
  document.getElementById("auth-section").style.display = "flex";
  document.getElementById("main-section").style.display = "none";
}

// Show chat after login
function showMainSection() {
  document.getElementById("auth-section").style.display = "none";
  document.getElementById("main-section").style.display = "block";
}

// -------------------------
// PDF Upload
// -------------------------
async function uploadPDF() {
  const fileInput = document.getElementById("pdf-file");
  const msg = document.getElementById("upload-msg");

  if (!fileInput.files.length) { msg.textContent = "Select a PDF"; return; }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    const res = await fetch("http://127.0.0.1:8000/upload_pdf", {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` },
      body: formData
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    const data = await res.json();
    msg.textContent = data.message;
  } catch (e) { msg.textContent = e.message; }
}

// -------------------------
// Chat Functions
// -------------------------
async function sendMessage() {
  const input = document.getElementById("message");
  const text = input.value.trim();
  if (!text) return;

  const chat = document.getElementById("chat");
  input.value = "";

  // Add user message
  const userDiv = document.createElement("div");
  userDiv.className = "message user";
  userDiv.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
  chat.appendChild(userDiv);
  scrollToBottom();

  try {
    const res = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ message: text })
    });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    // Add bot message
    const botDiv = document.createElement("div");
    botDiv.className = "message bot";
    botDiv.innerHTML = `<div class="message-content complete">${escapeHtml(data.reply)}</div>`;
    chat.appendChild(botDiv);
    scrollToBottom();
  } catch (e) {
    const errDiv = document.createElement("div");
    errDiv.className = "message bot";
    errDiv.innerHTML = `<div class="message-content complete" style="background:#fee;color:#c33;">Error: ${escapeHtml(e.message)}</div>`;
    chat.appendChild(errDiv);
  }
}

function scrollToBottom() {
  const chat = document.getElementById("chat");
  chat.scrollTop = chat.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// -------------------------
// Load Chat History
// -------------------------
async function loadHistory() {
  const historyDiv = document.getElementById("history");
  historyDiv.innerHTML = "<h3>Chat History:</h3>";

  try {
    const res = await fetch("http://127.0.0.1:8000/chat_history", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (!res.ok) throw new Error(`Failed to load history: ${res.status}`);
    const data = await res.json();
    data.forEach(c => {
      const q = document.createElement("div");
      q.className = "message user";
      q.innerHTML = `<div class="message-content">${escapeHtml(c.question)}</div>`;
      const a = document.createElement("div");
      a.className = "message bot";
      a.innerHTML = `<div class="message-content complete">${escapeHtml(c.answer)}</div>`;
      historyDiv.appendChild(q);
      historyDiv.appendChild(a);
    });
  } catch (e) {
    historyDiv.innerHTML += `<p style="color:red;">${escapeHtml(e.message)}</p>`;
  }
}

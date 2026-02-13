// ================= TOKEN MANAGEMENT =================

function getToken() {
  return localStorage.getItem("auth_token");
}

function setToken(token) {
  localStorage.setItem("auth_token", token);
}

function clearToken() {
  localStorage.removeItem("auth_token");
}

// Auto check login
window.addEventListener("DOMContentLoaded", () => {
  const token = getToken();
  if (token) verifyToken(token);
});

async function verifyToken(token) {
  try {
    const res = await fetch("http://127.0.0.1:8000/verify_token", {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (res.ok) showMainSection();
    else clearToken();
  } catch {
    clearToken();
  }
}

// ================= AUTH =================

async function signup() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const msg = document.getElementById("auth-msg");

  if (!email || !password) {
    msg.textContent = "Enter email and password";
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:8000/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) throw new Error("Signup failed");

    const data = await res.json();
    setToken(data.access_token);
    msg.textContent = "Signup successful!";
    showMainSection();
  } catch (e) {
    msg.textContent = e.message;
  }
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const msg = document.getElementById("auth-msg");

  if (!email || !password) {
    msg.textContent = "Enter email and password";
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) throw new Error("Login failed");

    const data = await res.json();
    setToken(data.access_token);
    showMainSection();
  } catch (e) {
    msg.textContent = e.message;
  }
}

function logout() {
  clearToken();
  document.getElementById("auth-section").style.display = "flex";
  document.getElementById("main-section").style.display = "none";
}

// Switch UI
function showMainSection() {
  document.getElementById("auth-section").style.display = "none";
  document.getElementById("main-section").style.display = "flex";
}

// ================= PDF UPLOAD =================

async function uploadPDF() {
  const fileInput = document.getElementById("pdf-file");
  const msg = document.getElementById("upload-msg");
  const token = getToken();

  if (!token) {
    logout();
    return;
  }

  if (!fileInput.files.length) {
    msg.textContent = "Select a PDF file";
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  msg.textContent = "Uploading...";

  try {
    const res = await fetch("http://127.0.0.1:8000/upload_pdf", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData
    });

    if (!res.ok) throw new Error("Upload failed");

    msg.textContent = "Uploaded successfully!";
    fileInput.value = "";
  } catch (e) {
    msg.textContent = e.message;
  }
}

// ================= CHAT =================

async function sendMessage() {
  const input = document.getElementById("message");
  const text = input.value.trim();
  const token = getToken();

  if (!text) return;
  if (!token) {
    logout();
    return;
  }

  const chat = document.getElementById("chat");

  // Remove welcome message
  const welcome = chat.querySelector(".welcome");
  if (welcome) welcome.remove();

  input.value = "";

  // Add user message
  addMessage(text, "user");

  // Add temporary bot message
  const loading = addMessage("Thinking...", "bot");

  try {
    const res = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ message: text })
    });

    if (!res.ok) throw new Error("Server error");

    const data = await res.json();

    loading.querySelector(".message-content").textContent = data.reply;

  } catch (e) {
    loading.querySelector(".message-content").textContent = "Error: " + e.message;
  }

  scrollToBottom();
}

function addMessage(text, type) {
  const chat = document.getElementById("chat");

  const wrapper = document.createElement("div");
  wrapper.className = `message ${type}`;

  const content = document.createElement("div");
  content.className = "message-content";
  content.textContent = text;

  wrapper.appendChild(content);
  chat.appendChild(wrapper);

  scrollToBottom();
  return wrapper;
}

function scrollToBottom() {
  const chat = document.getElementById("chat");
  chat.scrollTop = chat.scrollHeight;
}

// ================= HISTORY =================

async function loadHistory() {
  const token = getToken();
  const historyDiv = document.getElementById("history");

  if (!token) {
    logout();
    return;
  }

  historyDiv.innerHTML = "Loading...";

  try {
    const res = await fetch("http://127.0.0.1:8000/chat_history", {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) throw new Error("Failed");

    const data = await res.json();

    if (data.length === 0) {
      historyDiv.innerHTML = "No history yet.";
      return;
    }

    historyDiv.innerHTML = "";

    data.forEach(item => {
      const q = document.createElement("p");
      q.innerHTML = `<strong>Q:</strong> ${item.question}`;

      const a = document.createElement("p");
      a.innerHTML = `<strong>A:</strong> ${item.answer}`;

      historyDiv.appendChild(q);
      historyDiv.appendChild(a);
      historyDiv.appendChild(document.createElement("hr"));
    });

  } catch (e) {
    historyDiv.textContent = e.message;
  }
}
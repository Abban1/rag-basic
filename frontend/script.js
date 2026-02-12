// -------------------------
// Token Management
// -------------------------
function getToken() {
  return localStorage.getItem('auth_token');
}

function setToken(token) {
  localStorage.setItem('auth_token', token);
}

function clearToken() {
  localStorage.removeItem('auth_token');
}

// Check if user is already logged in on page load
window.addEventListener('DOMContentLoaded', () => {
  const token = getToken();
  if (token) {
    // Verify token is still valid
    verifyToken(token);
  }
});

async function verifyToken(token) {
  try {
    const res = await fetch("http://127.0.0.1:8000/verify_token", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (res.ok) {
      showMainSection();
    } else {
      clearToken();
    }
  } catch (e) {
    clearToken();
  }
}

// -------------------------
// Auth Functions
// -------------------------
async function signup() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const msg = document.getElementById("auth-msg");

  if (!email || !password) { 
    msg.textContent = "Please enter both email and password"; 
    return; 
  }

  if (password.length < 6) {
    msg.textContent = "Password must be at least 6 characters";
    return;
  }

  try {
    const res = await fetch("http://127.0.0.1:8000/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || `Signup failed: ${res.status}`);
    }
    
    const data = await res.json();
    setToken(data.access_token);
    msg.textContent = "Signup successful!";
    msg.style.color = "green";
    setTimeout(() => {
      showMainSection();
      msg.textContent = "";
      msg.style.color = "red";
    }, 1000);
  } catch (e) { 
    msg.textContent = e.message; 
  }
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const msg = document.getElementById("auth-msg");

  if (!email || !password) { 
    msg.textContent = "Please enter both email and password"; 
    return; 
  }

  try {
    const res = await fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || `Login failed: ${res.status}`);
    }
    
    const data = await res.json();
    setToken(data.access_token);
    msg.textContent = "Login successful!";
    msg.style.color = "green";
    setTimeout(() => {
      showMainSection();
      msg.textContent = "";
      msg.style.color = "red";
    }, 1000);
  } catch (e) { 
    msg.textContent = e.message; 
  }
}

function logout() {
  clearToken();
  document.getElementById("auth-section").style.display = "flex";
  document.getElementById("main-section").style.display = "none";
  document.getElementById("chat").innerHTML = `
    <div class="welcome-screen">
      <div class="welcome-icon">📄</div>
      <h2>Welcome to PDF Chat</h2>
      <p>Ask anything about your PDFs</p>
    </div>
  `;
  document.getElementById("history").innerHTML = "";
}

// Show chat after login
function showMainSection() {
  document.getElementById("auth-section").style.display = "none";
  document.getElementById("main-section").style.display = "block";
  document.getElementById("email").value = "";
  document.getElementById("password").value = "";
}

// -------------------------
// PDF Upload
// -------------------------
async function uploadPDF() {
  const fileInput = document.getElementById("pdf-file");
  const msg = document.getElementById("upload-msg");
  const token = getToken();

  if (!token) {
    msg.textContent = "Please login first";
    msg.style.color = "red";
    return;
  }

  if (!fileInput.files.length) { 
    msg.textContent = "Please select a PDF file"; 
    msg.style.color = "red";
    return; 
  }

  const file = fileInput.files[0];
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    msg.textContent = "Please select a valid PDF file";
    msg.style.color = "red";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  msg.textContent = "Uploading PDF...";
  msg.style.color = "blue";

  try {
    const res = await fetch("http://127.0.0.1:8000/upload_pdf", {
      method: "POST",
      headers: { 
        "Authorization": `Bearer ${token}`
      },
      body: formData
    });
    
    if (!res.ok) {
      if (res.status === 401) {
        clearToken();
        logout();
        throw new Error("Session expired. Please login again.");
      }
      const error = await res.json();
      throw new Error(error.detail || `Upload failed: ${res.status}`);
    }
    
    const data = await res.json();
    msg.textContent = data.message || "PDF uploaded successfully!";
    msg.style.color = "green";
    fileInput.value = ""; // Clear file input
    
    setTimeout(() => {
      msg.textContent = "";
    }, 3000);
  } catch (e) { 
    msg.textContent = e.message; 
    msg.style.color = "red";
  }
}

// -------------------------
// Chat Functions
// -------------------------
async function sendMessage() {
  const input = document.getElementById("message");
  const text = input.value.trim();
  const token = getToken();

  if (!token) {
    alert("Please login first");
    logout();
    return;
  }

  if (!text) return;

  const chat = document.getElementById("chat");
  
  // Remove welcome screen if present
  const welcomeScreen = chat.querySelector('.welcome-screen');
  if (welcomeScreen) {
    welcomeScreen.remove();
  }

  input.value = "";

  // Add user message
  const userDiv = document.createElement("div");
  userDiv.className = "message user";
  userDiv.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
  chat.appendChild(userDiv);
  scrollToBottom();

  // Add loading message
  const loadingDiv = document.createElement("div");
  loadingDiv.className = "message bot";
  loadingDiv.innerHTML = `<div class="message-content">Thinking...</div>`;
  chat.appendChild(loadingDiv);
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
    
    if (!res.ok) {
      if (res.status === 401) {
        clearToken();
        logout();
        throw new Error("Session expired. Please login again.");
      }
      const error = await res.json();
      throw new Error(error.detail || `Server error: ${res.status}`);
    }
    
    const data = await res.json();

    // Remove loading message
    loadingDiv.remove();

    // Add bot message
    const botDiv = document.createElement("div");
    botDiv.className = "message bot";
    botDiv.innerHTML = `<div class="message-content complete">${escapeHtml(data.reply)}</div>`;
    chat.appendChild(botDiv);
    scrollToBottom();
  } catch (e) {
    // Remove loading message
    loadingDiv.remove();
    
    const errDiv = document.createElement("div");
    errDiv.className = "message bot";
    errDiv.innerHTML = `<div class="message-content complete" style="background:#fee;color:#c33;">Error: ${escapeHtml(e.message)}</div>`;
    chat.appendChild(errDiv);
    scrollToBottom();
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
  const token = getToken();

  if (!token) {
    alert("Please login first");
    logout();
    return;
  }

  historyDiv.innerHTML = "<h3>Chat History:</h3><p>Loading...</p>";

  try {
    const res = await fetch("http://127.0.0.1:8000/chat_history", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    
    if (!res.ok) {
      if (res.status === 401) {
        clearToken();
        logout();
        throw new Error("Session expired. Please login again.");
      }
      throw new Error(`Failed to load history: ${res.status}`);
    }
    
    const data = await res.json();
    historyDiv.innerHTML = "<h3>Chat History:</h3>";
    
    if (data.length === 0) {
      historyDiv.innerHTML += "<p>No chat history yet.</p>";
      return;
    }
    
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
    historyDiv.innerHTML = `<h3>Chat History:</h3><p style="color:red;">${escapeHtml(e.message)}</p>`;
  }
}
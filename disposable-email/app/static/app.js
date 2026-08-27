let currentEmail = "";
let countdownInterval = null;
let fetchInterval = null; // NEW: Added to handle auto-refreshing the inbox
let remainingSeconds = 0;

// 1. Theme Toggle Handler
function toggleTheme() {
    document.body.classList.toggle("light-theme");
    const btn = document.querySelector(".theme-btn");
    
    if (document.body.classList.contains("light-theme")) {
        btn.textContent = "🌙 Dark Mode";
    } else {
        btn.textContent = "☀️ Light Mode";
    }
}

// 2. Generate New Email Address
async function generateNewEmail() {
    try {
        const response = await fetch("/generate");
        const data = await response.json();

        if (data.status === "success") {
            currentEmail = data.email;
            document.getElementById("email-display").value = currentEmail;
            document.getElementById("btn-refresh").disabled = false;

            // Start 10-minute countdown timer
            startTimer(data.ttl_seconds);

            // Immediately check for messages
            fetchMessages();

            // NEW: Automatically check for new emails every 5 seconds!
            if (fetchInterval) clearInterval(fetchInterval);
            fetchInterval = setInterval(fetchMessages, 5000);
        }
    } catch (error) {
        console.error("Error generating email:", error);
    }
}

// 3. Fetch Messages from Redis
async function fetchMessages() {
    if (!currentEmail) return;

    try {
        const response = await fetch(`/inbox/${currentEmail}`);
        const data = await response.json();

        if (data.status === "success") {
            renderMessages(data.emails);
            
            // Sync expiration timer with Redis TTL
            if (data.expires_in_seconds > 0) {
                remainingSeconds = data.expires_in_seconds;
            }
        }
    } catch (error) {
        console.error("Error fetching messages:", error);
    }
}

// 4. Render Messages into DOM
function renderMessages(emails) {
    const container = document.getElementById("inbox-list");

    if (!emails || emails.length === 0) {
        container.innerHTML = `<p class="empty-state">No messages received yet.</p>`;
        return;
    }

    // Build message HTML cards dynamically
    container.innerHTML = emails.map(email => {
        // Fallback: If plain text body is empty, try to show the HTML version, or a default message
        const textContent = email.body || email.html || "No text content.";

        return `
        <div class="message-card">
            <div class="message-header">
                <span>From: ${escapeHtml(email.sender)}</span>
                <span>Subject: ${escapeHtml(email.subject)}</span>
            </div>
            <div class="message-body">${escapeHtml(textContent)}</div>
        </div>
        `;
    }).join("");
}

// 5. Countdown Timer
function startTimer(seconds) {
    remainingSeconds = seconds;
    clearInterval(countdownInterval);

    countdownInterval = setInterval(() => {
        remainingSeconds--;

        if (remainingSeconds <= 0) {
            clearInterval(countdownInterval);
            clearInterval(fetchInterval); // NEW: Stop auto-fetching when expired
            
            document.getElementById("timer").textContent = "Expired";
            document.getElementById("btn-refresh").disabled = true;
            document.getElementById("inbox-list").innerHTML = `
                <p class="empty-state">This inbox has expired. Generate a new email to continue.</p>
            `;
            return;
        }

        const mins = Math.floor(remainingSeconds / 60);
        const secs = remainingSeconds % 60;
        document.getElementById("timer").textContent = 
            `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }, 1000);
}

// Security: Helper to escape HTML characters (Prevents XSS attacks)
function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}
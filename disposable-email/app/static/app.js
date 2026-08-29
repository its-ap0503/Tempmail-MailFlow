let currentEmail = "";
let countdownInterval = null;
let fetchInterval = null;
let remainingSeconds = 0;

// GSAP: Initial Page Load Animations
document.addEventListener("DOMContentLoaded", () => {
    // Stagger the header and cards floating up
    gsap.from("header", { y: -30, opacity: 0, duration: 0.8, ease: "back.out(1.5)" });
    gsap.from(".card", { 
        y: 40, 
        opacity: 0, 
        duration: 0.8, 
        stagger: 0.2, 
        ease: "power3.out", 
        delay: 0.2 
    });
});

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

        // Check for rate limit!
        if (response.status === 429) {
            alert("Whoa there! You're generating emails too fast. Please wait a minute.");
            return; // Stop execution
        }

        const data = await response.json();

        if (data.status === "success") {
            currentEmail = data.email;
            const emailDisplay = document.getElementById("email-display");
            
            emailDisplay.value = currentEmail;
            document.getElementById("btn-refresh").disabled = false;

            // GSAP: Animate the input box receiving the new email
            gsap.fromTo(emailDisplay, 
                { scale: 0.95, borderColor: "var(--text-color)" }, 
                { scale: 1, borderColor: "var(--accent-color)", duration: 0.5, ease: "back.out(2)" }
            );

            // Start 10-minute countdown timer
            startTimer(data.ttl_seconds);

            // Immediately check for messages
            fetchMessages();

            // Automatically check for new emails every 5 seconds!
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

    // GSAP: Spin the sync button softly to show background activity
    gsap.to("#btn-refresh", { rotation: "+=180", duration: 0.5, ease: "power1.inOut" });

    try {
        const response = await fetch(`/inbox/${currentEmail}`);

        // Check for rate limit on auto-refresh!
        if (response.status === 429) {
            const container = document.getElementById("inbox-list");
            // Only overwrite if it's currently empty
            if (container.innerHTML.includes("empty-state")) {
                container.innerHTML = `<p class="empty-state" style="color: #ef4444;">Rate limit reached. Pausing refresh for a moment...</p>`;
            }
            
            // Smart Strategy: Slow down the polling interval to 10 seconds to recover
            clearInterval(fetchInterval);
            fetchInterval = setInterval(fetchMessages, 10000); 
            return; 
        }

        const data = await response.json();

        if (data.status === "success") {
            // Only re-render if we actually have a change in message count (optional optimization)
            const currentMessageCount = document.querySelectorAll('.message-card').length;
            if (data.emails && data.emails.length !== currentMessageCount) {
                renderMessages(data.emails);
            }
            
            // Sync expiration timer with Redis TTL
            if (data.expires_in_seconds > 0) {
                remainingSeconds = data.expires_in_seconds;
            }
        } else if (data.status === "expired") {
            // Inbox has been destroyed on the server — stop everything
            clearInterval(countdownInterval);
            clearInterval(fetchInterval);
            
            const timerEl = document.getElementById("timer");
            timerEl.textContent = "Destroyed";
            timerEl.style.color = "#ef4444";
            
            document.getElementById("btn-refresh").disabled = true;
            document.getElementById("inbox-list").innerHTML = `
                <p class="empty-state" style="color: #ef4444;">This inbox has been destroyed. No one can send emails to this address anymore. Generate a new email to continue.</p>
            `;
            currentEmail = ""; // Clear so no further fetches happen
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

    // GSAP: Animate newly injected message cards
    gsap.from(".message-card", { 
        x: -20, 
        opacity: 0, 
        duration: 0.5, 
        stagger: 0.1, 
        ease: "power2.out" 
    });
}

// 5. Countdown Timer
function startTimer(seconds) {
    remainingSeconds = seconds;
    clearInterval(countdownInterval);

    countdownInterval = setInterval(() => {
        remainingSeconds--;

        if (remainingSeconds <= 0) {
            clearInterval(countdownInterval);
            clearInterval(fetchInterval); // Stop auto-fetching when expired
            
            const timerEl = document.getElementById("timer");
            timerEl.textContent = "Expired";
            timerEl.style.color = "#ef4444"; // Red for expired
            
            document.getElementById("btn-refresh").disabled = true;
            document.getElementById("inbox-list").innerHTML = `
                <p class="empty-state" style="color: #ef4444;">This inbox has expired. Generate a new email to continue.</p>
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
    if (!text) return "";
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}
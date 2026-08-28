export default {
  async email(message, env, ctx) {
    // Read the full raw MIME email (headers + body) as text
    const rawEmailStream = message.raw;
    const recipient = message.to; //new 
    const reader = rawEmailStream.getReader();
    const decoder = new TextDecoder();
    let rawEmail = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      rawEmail += decoder.decode(value, { stream: true });
    }
    rawEmail += decoder.decode(); // flush remaining bytes

    // Forward the RAW email as-is — the backend parses headers itself
    // via email.message_from_string(), so no JSON wrapping needed.
    try {
      const response = await fetch("https://tempmail-mailflow.onrender.com/webhook/email", {
        method: "POST",
        headers: {
          "Content-Type": "message/rfc822",
          "X-Webhook-Secret": "webhookYm1Ibtrdhya#", // Must match WEBHOOK_SECRET on Render exactly
          "X-Forwarded-To": recipient // NEW: Pass the target email to Flask
        },
        body: rawEmail
      });

      if (!response.ok) {
        console.error(`Webhook delivery failed: ${response.status} ${response.statusText}`);
      } else {
        console.log(`Webhook delivered for ${message.to}`);
      }
    } catch (err) {
      console.error(`Fetch to Render failed: ${err.message}`);
    }
  }
};
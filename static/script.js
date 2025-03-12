$(document).ready(function () {
  // Load conversation history when the page loads
  $.ajax({
    url: "/chat-history",
    method: "GET",
    success: function (response) {
      if (response.history.length > 0) {
        response.history.forEach((msg) => {
          appendMessage(msg.role, msg.content);
        });
      }
    },
    error: function (error) {
      console.error("Error loading conversation history:", error);
    },
  });

  // Function to append messages with formatting
  function appendMessage(sender, message) {
      const chatMessages = $("#chat-messages");
      const messageDiv = $("<div>")
          .addClass("d-flex mb-2")
          .addClass(sender === "user" ? "justify-content-end" : "justify-content-start");

      // **Escape HTML special characters**
      let escapedMessage = message
          .replace(/</g, "&lt;")  // Escape `<`
          .replace(/>/g, "&gt;"); // Escape `>`

      // **Detect language & wrap code blocks with Prism.js classes**
      const formattedMessage = escapedMessage.replace(
          /```(\w*)\n([\s\S]*?)```/g, // Detect language (optional) + code block
          function (match, lang, code) {
              const languageClass = lang ? `language-${lang}` : "language-plaintext";
              return `<pre class="rounded-2 mx-3"><code class="${languageClass}">${code}</code></pre>`;
          }
      );

      // **Format Markdown-style text**
      const finalMessage = formattedMessage
          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Bold
          .replace(/`([^`\n]+)`/g, "<code>$1</code>") // Inline code
          .replace(/###\s+(.*?)(\n|$)/g, "<h3>$1</h3>") // Headings
          .replace(/\n\n/g, "<br><br>") // Paragraph breaks
          .replace(/\n/g, "<br>") // Line breaks
          .trim();

      // **Create message content**
      const messageContent = `
        <div class="test py-2 px-3 rounded ${sender === "user" ? "bg-primary text-white" : "bg-light text-dark"}">
            ${finalMessage}
        </div>
      `;

      messageDiv.html(messageContent);
      chatMessages.append(messageDiv);
      chatMessages.scrollTop(chatMessages[0].scrollHeight); // Auto-scroll

      // **Apply Prism syntax highlighting**
      if (typeof Prism !== "undefined") {
          Prism.highlightAll();
      }
    
      let code = document.createElement("code");
      Prism.hooks.add("before-highlight", function (env) {
      env.code = env.element.innerText;
      });
      Prism.highlightElement(code);
  }



  // Send message when clicking the send button
  $("#send-btn").click(function () {
    const message = $("#user-input").val().trim();
    if (!message) return; // Prevent sending empty messages

    appendMessage("user", message); // Append user message
    $("#user-input").val("").prop("disabled", true); // Clear input and disable until response

    $.ajax({
      url: "/chat",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ message: message }),
      success: function (response) {
        appendMessage("assistant", response.response); // Append assistant response
      },
      error: function () {
        appendMessage("assistant", "⚠️ Error: Could not get a response.");
      },
      complete: function () {
        $("#user-input").prop("disabled", false).focus(); // Re-enable input after response
      },
    });
  });

  // Send message when pressing Enter key
  $("#user-input").keypress(function (e) {
    if (e.which == 13 && !e.shiftKey) {
      e.preventDefault(); // Prevent default form submission
      $("#send-btn").click();
    }
  });

  // Sign out user and redirect to login
  $("#signout-btn").click(function () {
    $.get("/logout", function () {
      window.location.href = "/login";
    });
  });
});

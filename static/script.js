let activeConversationId = initialConversationId || null;
let isNewConversation = !activeConversationId;

$(document).ready(function () {
  if (activeConversationId) {
    loadConversationContent(activeConversationId); // Load conversation on page load
  } else {
    console.log("Starting fresh conversation");
  }
  // Load conversation history when the page loads
  function loadConversationContent(conversationId) {
    $("#chat-messages").empty();
    $.ajax({
      url: "/chat-history",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ conversation_id: conversationId }),
      success: function (response) {
        if (response.history.length > 0) {
          response.history.forEach((msg) =>
            appendMessage(msg.role, msg.content)
          );
        }
      },
      error: function (error) {
        console.error("Error loading conversation history:", error);
      },
    });
  }

  function appendInvite(topic) {
    const chatMessages = $("#chat-messages");
    const messageDiv = $("<div>")
      .addClass("d-flex mb-2")
      .addClass("justify-content-start");
    console.log(topic);
    const messageContent = `
      <div class="test py-2 px-3 rounded bg-light text-dark">
          ${topic}
      </div>
    `;

    messageDiv.html(messageContent);
    chatMessages.append(messageDiv);
    chatMessages.scrollTop(chatMessages[0].scrollHeight);
  }

  // Function to append messages with formatting
  function appendMessage(sender, message, invite, topic) {
    const chatMessages = $("#chat-messages");
    const messageDiv = $("<div>")
      .addClass("d-flex mb-2")
      .addClass(
        sender === "user" ? "justify-content-end" : "justify-content-start"
      );

    // **Escape HTML special characters**
    let escapedMessage = message
      .replace(/</g, "&lt;") // Escape `<`
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
        <div class="test py-2 px-3 rounded ${
          sender === "user" ? "bg-primary text-white" : "bg-light text-dark"
        }">
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

    if (invite) {
      console.log(topic);
      appendInvite(topic);
    }
  }

  // Send message when clicking the send button
  $("#send-btn").click(function () {
    const message = $("#user-input").val().trim();
    if (!message) return; // Prevent sending empty messages

    const pathParts = window.location.pathname.split("/");
    let activeConversationId = null;
    let isNewConversation = false;

    if (pathParts[1] === "conversation" && pathParts[2]) {
      // Existing conversation
      activeConversationId = pathParts[2];
    } else {
      // New conversation (default page `/`)
      isNewConversation = true;
    }

    console.log("Active Conversation ID:", activeConversationId);
    console.log("Is New Conversation:", isNewConversation);

    appendMessage("user", message); // Append user message
    $("#user-input").val("").prop("disabled", true); // Clear input and disable until response

    // Determine API URL based on conversation state
    let apiUrl = "/conversation";
    if (!isNewConversation && activeConversationId) {
      apiUrl = `/conversation/${activeConversationId}`;
    }

    $.ajax({
      url: apiUrl,
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ message: message }),
      success: function (response) {
        appendMessage(
          "assistant",
          response.response,
          response.propose_new_chat,
          response.topic
        ); // Append assistant response

        if (isNewConversation) {
          activeConversationId = response.conversation_id;
          isNewConversation = false;

          if (
            !document.querySelector(
              `[data-conversation-id="${response.conversation_id}"]`
            )
          ) {
            const sidebar = document.getElementById("sidebar");
            const newLink = document.createElement("a");
            newLink.href = `/conversation/${response.conversation_id}`;
            newLink.textContent = `Conversation ${response.conversation_id}`;
            newLink.dataset.conversationId = response.conversation_id;
            sidebar.appendChild(newLink);
          }

          window.history.pushState(
            null,
            "",
            `/conversation/${response.conversation_id}`
          );
        }
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

  const textarea = document.getElementById("user-input");
  const sendButton = document.getElementById("send-btn");

  // Auto-grow and limit behavior
  textarea.addEventListener("input", function () {
    this.style.height = "auto"; // Reset height to shrink if needed
    this.style.overflowY = "hidden"; // Hide scroll while resizing

    if (this.scrollHeight <= 150) {
      this.style.height = this.scrollHeight + "px";
    } else {
      this.style.height = "150px";
      this.style.overflowY = "auto"; // Enable scrollbar when limit is hit
    }
  });

  // Reset on send
  sendButton.addEventListener("click", function () {
    textarea.value = "";
    textarea.style.height = "auto";
    textarea.style.overflowY = "hidden";
  });

  // Listen for Back/Forward Button
  window.addEventListener("popstate", function (event) {
    const pathParts = window.location.pathname.split("/");
    if (pathParts[1] === "conversation" && pathParts[2]) {
      activeConversationId = pathParts[2];
      isNewConversation = false;
      loadConversationContent(activeConversationId); // Reload conversation
    } else {
      activeConversationId = null;
      isNewConversation = true;
      clearChatArea(); // Clear chat when returning to `/`
    }
  });
});

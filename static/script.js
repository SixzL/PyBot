let activeConversationId = initialConversationId || null;
let isNewConversation = !activeConversationId;

$(document).ready(function () {
  // Initialize sidebar
  updateSidebarConversations();

  if (activeConversationId) {
    loadConversationContent(activeConversationId);
  } else {
    console.log("Starting fresh conversation");
    $("#welcome-msg").show();
    $("#conversation-title").text("New Conversation");
  }

  // Handle example questions
  $(".example-question").on("click", function () {
    const questionText = $(this).text();
    $("#user-input").val(questionText);
    $("#send-btn").click();
  });

  // Function to update conversation title
  function updateConversationTitle(conversationId) {
    if (!conversationId) {
      $("#conversation-title").text("New Conversation");
      return;
    }

    $.ajax({
      url: "/conversations",
      method: "GET",
      success: function (response) {
        const conversation = response.conversations.find(
          (conv) => conv.conversation_id === conversationId
        );
        if (conversation) {
          let title =
            conversation.title ||
            conversation.topic ||
            `Conversation ${response.conversations.indexOf(conversation) + 1}`;
          $("#conversation-title").text(title);
        }
      },
      error: function (error) {
        console.error("Error fetching conversation title:", error);
      },
    });
  }

  // Load conversation history when the page loads
  function loadConversationContent(conversationId) {
    $("#chat-messages").empty();
    $("#welcome-msg").hide();

    updateConversationTitle(conversationId);

    $.ajax({
      url: "/chat-history",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ conversation_id: conversationId }),
      success: function (response) {
        if (response.history.length > 0) {
          response.history.forEach((msg) => appendMessage(msg));
        }
      },
      error: function (error) {
        console.error("Error loading conversation history:", error);
        showErrorToast("Failed to load conversation history");
      },
    });
  }

  function showErrorToast(message) {
    const toastHTML = `
      <div class="position-fixed bottom-0 end-0 p-3" style="z-index: 5">
        <div class="toast align-items-center text-white bg-danger border-0" role="alert" aria-live="assertive" aria-atomic="true">
          <div class="d-flex">
            <div class="toast-body">
              <i class="fa-solid fa-triangle-exclamation me-2"></i> ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        </div>
      </div>
    `;

    $(document.body).append(toastHTML);
    const toastElement = document.querySelector(".toast");
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();

    // Remove toast from DOM after it's hidden
    toastElement.addEventListener("hidden.bs.toast", function () {
      toastElement.remove();
    });
  }

  function appendInvite(topic) {
    const chatMessages = $("#chat-messages");
    const messageDiv = $("<div>")
      .addClass("d-flex mb-2")
      .addClass("justify-content-start");

    const messageContent = `
      <div class="test py-2 px-3 rounded bg-light text-dark">
          ${topic}
          <div class="mt-2">
            <button class="btn btn-primary btn-sm learn-more-btn" data-topic="${encodeURIComponent(
              topic
            )}">
              <i class="fa-solid fa-book-open me-1"></i> Learn more
            </button>
          </div>
      </div>
    `;

    messageDiv.html(messageContent);
    chatMessages.append(messageDiv);
    chatMessages.scrollTop(chatMessages[0].scrollHeight);

    // Add event listener to the newly created button
    $(".learn-more-btn")
      .last()
      .on("click", function () {
        const topicData = decodeURIComponent($(this).data("topic"));
        createFocusedConversation(topicData);
      });
  }

  // Function to create a new focused conversation
  function createFocusedConversation(topic) {
    return new Promise((resolve, reject) => {
      showLoadingOverlay("Creating new focused conversation...");

      $.ajax({
        url: "/create-focused-conversation",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ topic: topic }),
        success: function (response) {
          hideLoadingOverlay();
          if (response.success && response.conversation_id) {
            window.location.href = `/conversation/${response.conversation_id}`;
            resolve(response);
          } else {
            showErrorToast("Failed to create focused conversation");
            reject();
          }
        },
        error: function () {
          hideLoadingOverlay();
          showErrorToast("Failed to create focused conversation");
          reject();
        },
      });
    });
  }

  function showLoadingOverlay(message) {
    const overlay = $(`
      <div class="loading-overlay">
        <div class="spinner-container">
          <div class="spinner-border text-light" role="status"></div>
          <p class="mt-2 text-light">${message || "Loading..."}</p>
        </div>
      </div>
    `);

    $("body").append(overlay);
  }

  function hideLoadingOverlay() {
    $(".loading-overlay").remove();
  }

  // Function to append messages with formatting
  function appendMessage(message) {
    // Hide welcome message when conversation starts
    $("#welcome-msg").hide();

    const chatMessages = $("#chat-messages");
    const messageDiv = $("<div>")
      .addClass("d-flex mb-2")
      .addClass(
        message.role === "user"
          ? "justify-content-end"
          : "justify-content-start"
      );

    let messageContent = "";

    if (message.type === "invitation") {
      // Create invitation message with button
      messageContent = `
            <div class="test py-2 px-3 rounded bg-light text-dark">
                ${message.content}
                <div class="mt-2">
                    <button class="btn btn-primary btn-sm learn-more-btn" 
                            ${message.accepted ? "disabled" : ""} 
                            data-topic="${encodeURIComponent(message.content)}">
                        <i class="fa-solid fa-book-open me-1"></i> 
                        ${message.accepted ? "Already started" : "Learn more"}
                    </button>
                </div>
            </div>
        `;
    } else {
      // Regular message
      messageContent = `
            <div class="test py-2 px-3 rounded ${
              message.role === "user"
                ? "bg-primary text-white"
                : "bg-light text-dark"
            }">
                ${formatMessage(message.content)}
            </div>
        `;
    }

    messageDiv.html(messageContent);
    chatMessages.append(messageDiv);
    chatMessages.scrollTop(chatMessages[0].scrollHeight);

    // Add event listener to the learn more button if it's an invitation
    if (message.type === "invitation") {
      const button = messageDiv.find(".learn-more-btn");

      // If already accepted, disable the button
      if (message.accepted) {
        button.prop("disabled", true).text("Already started");
      }

      // Add click handler if not accepted
      if (!message.accepted) {
        button.on("click", function () {
          const topicData = decodeURIComponent($(this).data("topic"));
          const button = $(this);

          // First mark the invitation as accepted
          $.ajax({
            url: "/mark-invitation-accepted",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({
              conversation_id: activeConversationId,
              message_id: message._id,
            }),
            success: function () {
              // Disable the button and update text
              button.prop("disabled", true).text("Already started");
              // Then create the focused conversation
              createFocusedConversation(topicData);
            },
            error: function () {
              showErrorToast("Failed to update invitation status");
            },
          });
        });
      }
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

    appendMessage({ role: "user", type: "text", content: message }); // Append user message
    $("#user-input").val("").prop("disabled", true); // Clear input and disable until response

    // Show typing indicator
    const typingIndicator = $("<div>").addClass(
      "d-flex mb-2 justify-content-start typing-indicator"
    ).html(`
        <div class="test py-2 px-3 rounded bg-light text-dark">
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
          <span class="typing-dot"></span>
        </div>
      `);
    $("#chat-messages").append(typingIndicator);
    $("#chat-messages").scrollTop($("#chat-messages")[0].scrollHeight);

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
        // Remove typing indicator
        $(".typing-indicator").remove();

        // Append assistant's text response
        appendMessage({
          role: "assistant",
          type: "text",
          content: response.response,
        });

        // If there's an invitation, append it as a separate message
        if (response.propose_new_chat && response.topic) {
          appendMessage({
            role: "assistant",
            type: "invitation",
            content: response.topic,
            accepted: false,
          });
        }

        if (isNewConversation && response.conversation_id) {
          activeConversationId = response.conversation_id;
          isNewConversation = false;

          // Update the conversation title if provided
          if (response.title) {
            $("#conversation-title").text(response.title);
          }

          // Update the sidebar with the new conversation
          if (typeof window.updateConversationList === "function") {
            window.updateConversationList();
          } else {
            // Dispatch event as fallback
            window.dispatchEvent(new Event("conversationUpdated"));
          }

          window.history.pushState(
            null,
            "",
            `/conversation/${response.conversation_id}`
          );
        }
      },
      error: function () {
        $(".typing-indicator").remove();
        appendMessage({
          role: "assistant",
          type: "text",
          content: "⚠️ Error: Could not get a response.",
        });
        showErrorToast("Failed to get a response from the server");
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
      $("#chat-messages").empty();
      $("#welcome-msg").show();
      updateConversationTitle(null);
    }
  });

  // Function to clear chat area
  function clearChatArea() {
    $("#chat-messages").empty();
    $("#welcome-msg").show();
  }
});

function formatMessage(content) {
  // Escape HTML special characters
  let escapedMessage = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // Detect language & wrap code blocks with Prism.js classes
  const formattedMessage = escapedMessage.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    function (match, lang, code) {
      const languageClass = lang ? `language-${lang}` : "language-plaintext";
      return `<pre class="rounded-2 mx-3"><code class="${languageClass}">${code}</code></pre>`;
    }
  );

  // Format Markdown-style text
  const finalMessage = formattedMessage
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Bold
    .replace(/`([^`\n]+)`/g, "<code>$1</code>") // Inline code
    .replace(/###\s+(.*?)(\n|$)/g, "<h3>$1</h3>") // Headings
    .replace(/\n\n/g, "<br><br>") // Paragraph breaks
    .replace(/\n/g, "<br>") // Line breaks
    .trim();

  // Apply Prism syntax highlighting
  if (typeof Prism !== "undefined") {
    setTimeout(() => Prism.highlightAll(), 0);
  }

  return finalMessage;
}

function updateSidebarConversations() {
  $.ajax({
    url: "/conversations",
    method: "GET",
    success: function (response) {
      const sidebarList = $("#sidebar-list");
      sidebarList.empty(); // Clear existing conversations

      response.conversations.forEach((conv, index) => {
        const li = $("<li>").addClass("nav-item mb-2");
        const link = $("<a>")
          .attr("href", `/conversation/${conv.conversation_id}`)
          .addClass("nav-link text-white text-truncate d-flex flex-column")
          .attr("data-conversation-id", conv.conversation_id);

        // Add active class if this is the current conversation
        if (conv.conversation_id === activeConversationId) {
          link.addClass("active");
        }

        const title = $("<div>").addClass(
          "d-flex justify-content-between align-items-center"
        );

        const convName = $("<span>");
        if (conv.type === "focused") {
          convName.html(
            `<i class="fa-solid fa-code me-1"></i>${
              conv.topic || `Challenge ${index + 1}`
            }`
          );
          if (conv.is_completed) {
            convName.append(
              ' <i class="fa-solid fa-check-circle text-success"></i>'
            );
          }
        } else {
          convName.html(
            `<i class="fa-solid fa-comment me-1"></i>${
              conv.title || `Conversation ${index + 1}`
            }`
          );
        }

        const date = $("<small>")
          .addClass("text-muted")
          .text(formatDate(new Date(conv.last_chat)));

        title.append(convName).append(date);
        link.append(title);
        li.append(link);
        sidebarList.append(li);
      });
    },
    error: function (error) {
      console.error("Error updating sidebar:", error);
    },
  });
}

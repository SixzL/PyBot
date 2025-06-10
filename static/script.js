let activeConversationId = initialConversationId || null;
let isNewConversation = !activeConversationId;

$(document).ready(function () {
  // Mobile Sidebar Toggle
  const sidebarToggle = $("#sidebar-toggle");
  const sidebarContainer = $("#sidebar-container");
  const body = $("body");

  // Create overlay element
  const overlay = $('<div class="sidebar-overlay"></div>');
  body.append(overlay);

  // Toggle sidebar
  sidebarToggle.on("click", function() {
    sidebarContainer.toggleClass("show");
    overlay.toggleClass("show");
  });

  // Close sidebar when clicking overlay
  overlay.on("click", function() {
    sidebarContainer.removeClass("show");
    overlay.removeClass("show");
  });

  // Close sidebar when clicking a link (for mobile)
  $("#sidebar a").on("click", function() {
    if (window.innerWidth < 768) {
      sidebarContainer.removeClass("show");
      overlay.removeClass("show");
    }
  });

  // Handle conversation link clicks
  $(document).on("click", "#sidebar .nav-link", function(e) {
    e.preventDefault();
    const conversationId = $(this).data("conversation-id");
    
    // Update URL without reloading
    window.history.pushState(null, "", `/conversation/${conversationId}`);
    
    // Update active state
    $("#sidebar .nav-link").removeClass("active");
    $(this).addClass("active");
    
    // Load conversation
    activeConversationId = conversationId;
    isNewConversation = false;
    loadConversationContent(conversationId);
    
    // Close mobile sidebar if needed
    if (window.innerWidth < 768) {
      sidebarContainer.removeClass("show");
      overlay.removeClass("show");
    }
  });

  // Initialize sidebar
  updateConversationList();

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
    if (!conversationId) return;

    // Clear current messages and hide welcome
    $("#chat-messages").empty();
    $("#welcome-msg").hide();

    // Show loading state
    showLoadingOverlay("Loading conversation...");

    // Update conversation title
    updateConversationTitle(conversationId);

    $.ajax({
      url: "/chat-history",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ conversation_id: conversationId }),
      success: function (response) {
        hideLoadingOverlay();
        
        if (response.history && response.history.length > 0) {
          response.history.forEach((msg) => {
            appendMessage(msg);
          });
          
          // Scroll to bottom after messages are loaded
          const chatMessages = $("#chat-messages");
          chatMessages.scrollTop(chatMessages[0].scrollHeight);
        }
        
        // Check if conversation is completed
        $.ajax({
          url: "/conversations",
          method: "GET",
          success: function(convResponse) {
            const conversation = convResponse.conversations.find(
              conv => conv.conversation_id === conversationId
            );
            if (conversation && conversation.is_completed) {
              disableInput();
            } else {
              enableInput();
            }
          },
          error: function() {
            console.error("Error checking conversation status");
            enableInput(); // Enable by default if check fails
          }
        });
      },
      error: function (error) {
        hideLoadingOverlay();
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

  // Function to create a new focused conversation
  function createFocusedConversation(
    topic,
    submittedCode = null,
    problemStatement = null
  ) {
    return new Promise((resolve, reject) => {
      showLoadingOverlay("Creating new focused conversation...");

      $.ajax({
        url: "/create-focused-conversation",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({
          topic: topic,
          submitted_code: submittedCode,
          problem_statement: problemStatement,
        }),
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
            <div class="msgBox py-3 px-4 rounded bg-light text-dark invitation-box">
                <div class="invitation-content">
                    <div class="invitation-header mb-2">
                        <i class="fa-solid fa-star text-warning me-2"></i>
                        <strong>Invitation to Focused Learning</strong>
                    </div>
                    <div class="invitation-description mb-3">
                        <p class="invitation-text text-muted mb-2">
                            Join a focused learning session to master this specific topic. 
                            Focused learning helps you understand and solve problems more efficiently 
                            by concentrating on one topic at a time.
                        </p>
                        <strong class="topic-label">Topic:</strong>
                        <div class="topic-content">${message.content}</div>
                    </div>
                    <div class="mt-3">
                        <button class="btn btn-primary btn-sm learn-more-btn" 
                                ${message.accepted ? "disabled" : ""} 
                                data-topic="${encodeURIComponent(message.content)}"
                                data-submitted-code="${encodeURIComponent(
                                  message.submitted_code || ""
                                )}"
                                data-problem="${encodeURIComponent(
                                  message.problem_statement || ""
                                )}"
                                data-message-id="${message._id || ""}">
                            <i class="fa-solid fa-graduation-cap me-1"></i> 
                            ${message.accepted ? "Already started" : "Start focused learning"}
                        </button>
                    </div>
                </div>
            </div>
        `;
    } else {
      // Regular message
      messageContent = `<div class="msgBox py-2 px-3 rounded ${
              message.role === "user"
                ? "bg-primary text-white"
                : "bg-light text-dark"
            } message-content">${formatMessage(message.content)}</div>`;
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
          const submittedCode = decodeURIComponent(
            $(this).data("submitted-code")
          );
          const messageId = $(this).data("message-id");
          const problemStatement = decodeURIComponent($(this).data("problem"));

          if (!messageId) {
            showErrorToast("Cannot process invitation: missing message ID");
            return;
          }

          // Disable the button immediately to prevent double clicks
          button.prop("disabled", true);

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
              // Update button text
              button.text("Already started");
              // Then create the focused conversation
              createFocusedConversation(
                topicData,
                submittedCode,
                problemStatement
              )
                .then(() => {
                  // Keep button disabled on success
                  button.prop("disabled", true).text("Already started");
                })
                .catch(() => {
                  // If focused conversation creation fails, re-enable the button
                  button.prop("disabled", false).text("Start focused learning");
                });
            },
            error: function (xhr) {
              // Re-enable the button on error
              button.prop("disabled", false).text("Start focused learning");
              showErrorToast(
                xhr.responseJSON?.error || "Failed to update invitation status"
              );
            },
          });
        });
      }
    }
  }

  // Send message when clicking the send button
  $("#send-btn").click(function () {
    // Get the raw message without trimming to preserve indentation
    const message = $("#user-input").val();

    // Only check if the message is empty after trimming
    if (!message.trim()) return; // Prevent sending empty messages

    const pathParts = window.location.pathname.split("/");
    if (pathParts[1] === "conversation" && pathParts[2]) {
      // Existing conversation
      activeConversationId = pathParts[2];
      isNewConversation = false;
    } else {
      // New conversation (default page `/`)
      isNewConversation = true;
    }

    console.log("Active Conversation ID:", activeConversationId);
    console.log("Is New Conversation:", isNewConversation);

    appendMessage({ role: "user", type: "text", content: message }); // Use original message with indentation
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
      data: JSON.stringify({ message: message }), // Send original message with indentation preserved
      success: function (response) {
        // Remove typing indicator
        $(".typing-indicator").remove();

        // Update activeConversationId immediately when we get it
        if (isNewConversation && response.conversation_id) {
          activeConversationId = response.conversation_id;
          isNewConversation = false;

          // Update URL and title
          window.history.pushState(
            null,
            "",
            `/conversation/${response.conversation_id}`
          );

          if (response.title) {
            $("#conversation-title").text(response.title);
          }
        }

        // Always append the assistant's response first
        if (response.response) {
          appendMessage({
            role: "assistant",
            type: "text",
            content: response.response,
          });
        }

        // If there's an invitation, append it as a separate message
        if (response.propose_new_chat && response.topic) {
          appendMessage({
            role: "assistant",
            type: "invitation",
            content: response.topic,
            submitted_code: response.submitted_code || "",
            problem_statement: response.problem_statement,
            _id: response.message_id,
          });
        }

        // Check if the conversation is now completed
        if (response.is_completed) {
          disableInput();
        } else {
          $("#user-input").prop("disabled", false).focus(); // Only re-enable if not completed
        }

        // Update the sidebar
        if (typeof window.updateConversationList === "function") {
          window.updateConversationList();
        } else {
          window.dispatchEvent(new Event("conversationUpdated"));
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
        $("#user-input").prop("disabled", false).focus(); // Re-enable input on error
      },
      complete: function () {
        // All input enabling/disabling is now handled in success/error handlers
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

  // Add this function to handle completed conversations
  function disableInput(message = "This conversation is completed. Start a new one to continue learning.") {
    $("#user-input")
        .prop("disabled", true)
        .addClass("completed-conversation-input")
        .attr("placeholder", message);
    $("#send-btn").addClass("completed-conversation-button");
  }

  function enableInput() {
    $("#user-input")
        .prop("disabled", false)
        .removeClass("completed-conversation-input")
        .attr("placeholder", "Type your message here...");
    $("#send-btn").removeClass("completed-conversation-button");
  }
});

function formatMessage(content) {
  // Escape HTML special characters
  let escapedMessage = content.replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // Detect language & wrap code blocks with Prism.js classes
  const formattedMessage = escapedMessage.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    function (match, lang, code) {
      // Default to python if no language is specified
      const languageClass = lang ? `language-${lang}` : "language-python";
      // Clean the code: trim extra whitespace but preserve indentation
      const cleanedCode = code.trim();
      // Create a temporary div to let Prism highlight the code
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = `<pre class="code-block"><code class="${languageClass}">${cleanedCode}</code></pre>`;
      // Manually highlight the code
      Prism.highlightElement(tempDiv.querySelector("code"));
      // Return the highlighted HTML
      return tempDiv.innerHTML;
    }
  );

  // Format Markdown-style text (outside of code blocks)
  const finalMessage = formattedMessage
    // Handle LaTeX symbols first
    .replace(/\\times/g, "×") // Convert \times to × symbol
    .replace(/\\div/g, "÷") // Convert \div to ÷ symbol
    .replace(/\\pm/g, "±") // Convert \pm to ± symbol
    .replace(/\\le/g, "≤") // Convert \le to ≤ symbol
    .replace(/\\ge/g, "≥") // Convert \ge to ≥ symbol
    .replace(/\\ne/g, "≠") // Convert \ne to ≠ symbol
    // Convert LaTeX-style variables to code format
    .replace(/\\\(\s*(.*?)\s*\\\)/g, "`$1`") // Convert \( n \) to `n` (trim spaces)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>") // Bold
    .replace(/`([^`\n]+)`/g, "<code>$1</code>") // Inline code
    .replace(/###\s+(.*?)(\n|$)/g, "<h3>$1</h3>") // Headings
    .replace(/\n\n/g, "<br><br>") // Paragraph breaks
    .replace(/\n/g, "<br>") // Line breaks
    .trim();

  return finalMessage;
}

// Function to append a conversation to the sidebar
function appendConversation(conv, index, isFocused) {
    const li = document.createElement("li");
    li.classList.add("nav-item", "mb-2");

    const link = document.createElement("a");
    link.href = `/conversation/${conv.conversation_id}`;
    link.classList.add(
        "nav-link",
        "text-white",
        "text-truncate",
        "d-flex",
        "flex-column"
    );
    link.setAttribute("data-conversation-id", conv.conversation_id);

    // Add focused class and completion status
    if (conv.type === 'focused') {
        link.classList.add("focused-conversation");
        if (conv.is_completed) {
            link.classList.add("completed-conversation");
        }
    }

    // Highlight current conversation if open
    const pathParts = window.location.pathname.split("/");
    if (pathParts[1] === "conversation" && pathParts[2] === conv.conversation_id) {
        link.classList.add("active");
    }

    // Conversation title and date
    const title = document.createElement("div");
    title.classList.add(
        "d-flex",
        "justify-content-between",
        "align-items-center"
    );

    const convName = document.createElement("span");
    if (conv.type === 'focused') {
        // Add status indicator for focused conversations
        const statusIndicator = document.createElement("span");
        statusIndicator.classList.add(
            "conversation-status",
            conv.is_completed ? "status-completed" : "status-incomplete"
        );
        
        convName.appendChild(statusIndicator);
        convName.innerHTML += `<i class="fa-solid fa-code me-1"></i>${
            conv.topic || `Challenge ${index + 1}`
        }`;
    } else {
        convName.innerHTML = `<i class="fa-solid fa-comment me-1"></i>${
            conv.title || `Conversation ${index + 1}`
        }`;
    }

    const date = document.createElement("small");
    date.classList.add("text-muted");
    date.textContent = formatDate(conv.last_chat);

    title.appendChild(convName);
    title.appendChild(date);

    link.appendChild(title);
    li.appendChild(link);
    return li;
}
// Update the updateConversationList function
function updateConversationList() {
    $.ajax({
        url: "/conversations",
        method: "GET",
        success: function(response) {
            const sidebarList = $("#sidebar-list");
            sidebarList.empty();

            // Group conversations
            const regularConvs = response.conversations.filter(
                conv => !conv.type || conv.type === 'regular'
            );
            const focusedConvs = response.conversations.filter(
                conv => conv.type === 'focused'
            );

            // Add section header for regular conversations if any exist
            if (regularConvs.length > 0) {
                const regularHeader = document.createElement("div");
                regularHeader.classList.add(
                    "sidebar-section-header",
                    "text-white-50",
                    "small",
                    "fw-bold",
                    "px-2",
                    "py-1"
                );
                regularHeader.textContent = "CONVERSATIONS";
                sidebarList.append(regularHeader);

                // Add regular conversations
                regularConvs.forEach((conv, index) => {
                    sidebarList.append(appendConversation(conv, index, false));
                });
            }

            // Add section header for focused conversations if any exist
            if (focusedConvs.length > 0) {
                const focusedHeader = document.createElement("div");
                focusedHeader.classList.add(
                    "sidebar-section-header",
                    "text-white-50",
                    "small",
                    "fw-bold",
                    "px-2",
                    "py-1"
                );
                focusedHeader.textContent = "FOCUSED LEARNING";
                sidebarList.append(focusedHeader);

                // Add focused conversations
                focusedConvs.forEach((conv, index) => {
                    sidebarList.append(appendConversation(conv, index, true));
                });
            }
        },
        error: function(error) {
            console.error("Error updating sidebar:", error);
        }
    });
}


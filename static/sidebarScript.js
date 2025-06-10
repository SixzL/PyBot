document.addEventListener("DOMContentLoaded", function () {
  const regularList = document.querySelector("#regular-conversations");
  const focusedList = document.querySelector("#focused-conversations");
  const newConversationBtn = document.querySelector(".btn-outline-light");

  // Function to update conversation list
  function updateConversationList() {
    $.ajax({
      url: "/conversations",
      method: "GET",
      success: function (response) {
        // Clear existing lists
        regularList.innerHTML = "";
        focusedList.innerHTML = "";

        if (response.conversations.length === 0) {
          const emptyState = document.createElement("div");
          emptyState.classList.add(
            "text-center",
            "text-muted",
            "mt-3",
            "small"
          );
          emptyState.innerHTML = `
            <i class="fa-solid fa-comment-slash mb-2 fs-4"></i>
            <p>No conversations yet</p>
          `;
          regularList.appendChild(emptyState);
          return;
        }

        // Group conversations
        const regularConvs = response.conversations.filter(
          (conv) => !conv.type || conv.type !== "focused"
        );
        const focusedConvs = response.conversations.filter(
          (conv) => conv.type === "focused"
        );

        // Add regular conversations
        if (regularConvs.length > 0) {
          regularConvs.forEach((conv, index) => {
            appendConversation(conv, index, false, regularList);
          });
        } else {
          const emptyState = document.createElement("div");
          emptyState.classList.add(
            "text-center",
            "text-muted",
            "mt-3",
            "small"
          );
          emptyState.innerHTML = `
            <i class="fa-solid fa-comment-slash mb-2 fs-4"></i>
            <p>No regular conversations</p>
          `;
          regularList.appendChild(emptyState);
        }

        // Add focused conversations
        if (focusedConvs.length > 0) {
          focusedConvs.forEach((conv, index) => {
            appendConversation(conv, index, true, focusedList);
          });
        } else {
          const emptyState = document.createElement("div");
          emptyState.classList.add(
            "text-center",
            "text-muted",
            "mt-3",
            "small"
          );
          emptyState.innerHTML = `
            <i class="fa-solid fa-code-slash mb-2 fs-4"></i>
            <p>No focused learning sessions</p>
          `;
          focusedList.appendChild(emptyState);
        }
      },
      error: function () {
        const errorMsg = document.createElement("li");
        errorMsg.classList.add("text-danger", "p-2");
        errorMsg.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-2"></i>Failed to load conversations.`;
        regularList.appendChild(errorMsg.cloneNode(true));
        focusedList.appendChild(errorMsg);
      },
    });
  }

  // Function to append a conversation to the sidebar
  function appendConversation(conv, index, isFocused, targetList) {
    const li = document.createElement("li");
    li.classList.add("nav-item", "mb-2");

    const link = document.createElement("a");
    link.href = `/conversation/${conv.conversation_id}`;
    link.classList.add(
      "nav-link",
      "text-white",
      "text-truncate",
      "d-flex",
      "align-items-center",
      "justify-content-between"
    );
    link.setAttribute("data-conversation-id", conv.conversation_id);

    // Add focused class for styling
    if (isFocused) {
      link.classList.add("focused-conversation");
    }

    // Add completed class if needed
    if (conv.is_completed) {
      link.classList.add("completed-conversation");
    }

    // Highlight current conversation if open
    const pathParts = window.location.pathname.split("/");
    if (
      pathParts[1] === "conversation" &&
      pathParts[2] === conv.conversation_id
    ) {
      link.classList.add("active");
    }

    // Create main content span
    const mainContent = document.createElement("span");
    mainContent.classList.add("d-flex", "align-items-center", "flex-grow-1", "text-truncate");

    // Conversation title
    if (isFocused) {
      // Use the topic name for focused conversations
      mainContent.innerHTML = `<i class="fa-solid fa-code me-1"></i><span class="text-truncate">${
        conv.topic || `Challenge ${index + 1}`
      }</span>`;
    } else {
      // Use the title or fallback for regular conversations
      mainContent.innerHTML = `<i class="fa-solid fa-comment me-1"></i><span class="text-truncate">${
        conv.title || `Conversation ${index + 1}`
      }</span>`;
    }
    
    link.appendChild(mainContent);
    li.appendChild(link);
    targetList.appendChild(li);
  }

  // Initial load of conversations
  updateConversationList();

  // New conversation button handler
  newConversationBtn.addEventListener("click", function () {
    const pathParts = window.location.pathname.split("/");
    // Only redirect if we're not already on the home page
    if (pathParts[1] === "conversation" && pathParts[2]) {
      window.location.href = "/";
    }
  });

  // Listen for custom event that signals conversation updates
  window.addEventListener("conversationUpdated", function () {
    updateConversationList();
  });

  // Export the update function so it can be called from other scripts
  window.updateConversationList = updateConversationList;
});

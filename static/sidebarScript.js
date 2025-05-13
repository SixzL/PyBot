document.addEventListener("DOMContentLoaded", function () {
  const sidebarList = document.querySelector(".nav-pills");

  // Clear existing list items
  sidebarList.innerHTML = "";

  // Fetch user conversations
  $.ajax({
    url: "/conversations",
    method: "GET",
    success: function (response) {
      response.conversations.forEach((conv) => {
        const li = document.createElement("li");
        li.classList.add("nav-item");

        const link = document.createElement("a");
        link.href = `/conversation/${conv.conversation_id}`;
        link.classList.add("nav-link", "text-white");
        link.textContent = `Conversation ${conv.conversation_id}`;

        li.appendChild(link);
        sidebarList.appendChild(li);
      });
    },
    error: function () {
      const li = document.createElement("li");
      li.textContent = "Failed to load conversations.";
      sidebarList.appendChild(li);
    },
  });
});

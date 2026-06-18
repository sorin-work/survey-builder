// Small progressive enhancements for the owner pages.

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  const input = document.querySelector(button.dataset.copy);
  if (!input) return;
  navigator.clipboard.writeText(input.value).then(() => {
    const label = button.textContent;
    button.textContent = "Copied";
    setTimeout(() => (button.textContent = label), 1500);
  });
});

// Mark question cards with unsaved edits and warn before leaving the page.
document.addEventListener("input", (event) => {
  const card = event.target.closest(".question");
  if (card && event.target.name !== "required") card.classList.add("dirty");
});

document.addEventListener("htmx:afterSwap", () => {
  // A swapped-in card is fresh from the server, so nothing is pending there.
  document.querySelectorAll(".question.dirty").forEach((card) => {
    if (!document.body.contains(card)) return;
    if (!card.querySelector("[data-dirty]")) card.classList.remove("dirty");
  });
});

window.addEventListener("beforeunload", (event) => {
  if (document.querySelector(".question.dirty")) {
    event.preventDefault();
    event.returnValue = "";
  }
});

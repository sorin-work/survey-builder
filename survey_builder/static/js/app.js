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
// Saving swaps in a fresh card from the server, which drops the marker.
document.addEventListener("input", (event) => {
  const card = event.target.closest(".question");
  if (card && event.target.name !== "required") card.classList.add("dirty");
});

window.addEventListener("beforeunload", (event) => {
  if (document.querySelector(".question.dirty")) {
    event.preventDefault();
    event.returnValue = "";
  }
});

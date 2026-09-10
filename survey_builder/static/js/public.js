// Respondent-side niceties. The form works without any of this.

// Live "12 / 200" counters under text fields that have a maximum length.
document.querySelectorAll("[data-counter]").forEach((field) => {
  const counter = document.getElementById(field.dataset.counter);
  const max = Number(field.getAttribute("maxlength"));
  const update = () => {
    const length = [...field.value].length;
    counter.textContent = `${length} / ${max}`;
    counter.classList.toggle("near-limit", length > max * 0.9);
  };
  field.addEventListener("input", update);
  update();
});

// After a failed submit, bring the first question with an error into view.
const firstError = document.querySelector(".public-question.has-error");
if (firstError) {
  firstError.scrollIntoView({ block: "center" });
  const input = firstError.querySelector("input, textarea, select");
  if (input) input.focus({ preventScroll: true });
}

// Disable the buttons once the form is on its way, so a double click does not
// send it twice.
document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const clicked = event.submitter;
    form.querySelectorAll("button[type=submit]").forEach((button) => {
      // Keep the clicked button's name/formaction: disable on the next tick.
      setTimeout(() => (button.disabled = true), 0);
    });
    if (clicked && clicked.dataset.busyLabel) clicked.textContent = clicked.dataset.busyLabel;
  });
});

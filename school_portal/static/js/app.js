// Small behaviours that would otherwise need inline handlers, which the
// Content-Security-Policy does not allow.
document.addEventListener("submit", (event) => {
  const form = event.target;
  const question = form.getAttribute("data-confirm");
  if (question && !window.confirm(question)) {
    event.preventDefault();
  }
});

document.addEventListener("click", (event) => {
  const toggle = event.target.closest("[data-check-all]");
  if (!toggle) return;
  const scope = document.querySelector(toggle.getAttribute("data-check-all"));
  if (!scope) return;
  const boxes = scope.querySelectorAll("input[type=checkbox]");
  const anyOff = Array.from(boxes).some((box) => !box.checked);
  boxes.forEach((box) => {
    box.checked = anyOff;
  });
});

// htmx sends the CSRF header from the body's hx-headers; this keeps a
// response error from failing silently on a tablet.
document.addEventListener("htmx:responseError", (event) => {
  const status = event.detail.xhr.status;
  const box = document.getElementById("htmx-error");
  if (box) {
    box.textContent = status === 400 ? "The page is out of date, reload it and try again." : "Something went wrong (" + status + "). Try again.";
    box.hidden = false;
  }
});

document.addEventListener("htmx:afterRequest", (event) => {
  const form = event.detail.elt;
  if (event.detail.successful && form.matches && form.matches("form[data-reset-on-success]")) {
    form.reset();
  }
});

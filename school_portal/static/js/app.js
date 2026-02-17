// Small behaviours that would otherwise need inline handlers, which the
// Content-Security-Policy does not allow.

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



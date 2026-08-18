const form = document.querySelector("#password-form");
const message = document.querySelector("#password-message");
const submitButton = form.querySelector("button[type='submit']");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.hidden = true;
  if (form.newPassword.value !== form.confirmPassword.value) {
    message.textContent = "Die neuen Passwörter stimmen nicht überein.";
    message.hidden = false;
    return;
  }
  submitButton.disabled = true;
  try {
    const response = await fetch("/api/v1/settings/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: form.currentPassword.value,
        new_password: form.newPassword.value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail?.message || "Änderung fehlgeschlagen");
    form.reset();
    message.className = "form-success";
    message.textContent = "Passwort wurde erfolgreich geändert.";
    message.hidden = false;
  } catch (error) {
    message.className = "form-error";
    message.textContent = error.message;
    message.hidden = false;
  } finally {
    submitButton.disabled = false;
  }
});

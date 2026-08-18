const form = document.querySelector("#login-form");
const errorMessage = document.querySelector("#login-error");
const submitButton = form.querySelector("button[type='submit']");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorMessage.hidden = true;
  submitButton.disabled = true;

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: form.username.value,
        password: form.password.value,
      }),
    });
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.detail || "Anmeldung fehlgeschlagen");
    }
    window.location.assign("/");
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    submitButton.disabled = false;
  }
});

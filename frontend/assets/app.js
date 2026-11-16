"use strict";
const app = document.getElementById("app");
const field = (label, type) => `<label>${label}<input name="${label.toLowerCase()}" type="${type}" autocomplete="${label === 'Password' ? (location.pathname === '/register' ? 'new-password' : 'current-password') : label.toLowerCase()}" required ${type === 'password' ? 'minlength="8"' : ''}></label>`;
function clearAuth() { localStorage.removeItem("jwt"); }
async function currentUser(token) {
  const response = await fetch("/api/user", {headers: {Authorization: `Token ${token}`}, cache: "no-store"});
  if (!response.ok) throw new Error("Session unavailable");
  return (await response.json()).user;
}
async function render() {
  app.replaceChildren();
  if (location.pathname === "/settings") {
    const token = localStorage.getItem("jwt");
    if (!token) { location.replace("/login"); return; }
    try {
      const user = await currentUser(token);
      app.innerHTML = '<h1>Settings</h1><p>Signed in as <span data-testid="account-email"></span></p><button type="button">Sign out</button>';
      app.querySelector('[data-testid="account-email"]').textContent = user.email;
      app.querySelector("button").addEventListener("click", () => { clearAuth(); location.assign("/login"); });
    } catch { clearAuth(); location.replace("/login"); }
    return;
  }
  const register = location.pathname === "/register";
  const title = register ? "Sign up" : "Sign in";
  app.innerHTML = `<h1>${title}</h1><form>${register ? field("Username", "text") : ""}${field("Email", "email")}${field("Password", "password")}<button type="submit">${title}</button></form>`;
  app.querySelector("form").addEventListener("submit", async event => {
    event.preventDefault();
    app.querySelector('[role="alert"]')?.remove();
    const form = event.currentTarget, button = form.querySelector("button");
    const user = Object.fromEntries(new FormData(form));
    button.disabled = true;
    clearAuth();
    try {
      const response = await fetch(register ? "/api/users" : "/api/users/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({user})});
      if (!response.ok) throw new Error(register ? "Registration could not be completed." : "Email or password is invalid.");
      const data = await response.json();
      await currentUser(data.user.token);
      localStorage.setItem("jwt", data.user.token);
      location.assign("/settings");
    } catch (error) {
      clearAuth();
      const alert = document.createElement("p"); alert.setAttribute("role", "alert"); alert.textContent = error.message; form.prepend(alert);
    } finally { button.disabled = false; }
  });
}
render();

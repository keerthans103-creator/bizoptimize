import { useState } from "react";
import { api } from "../api/client.js";
import { LogOutIcon } from "./icons.jsx";

export default function AuthPanel({ email, onAuthChange }) {
  const [mode, setMode] = useState("login");
  const [formEmail, setFormEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (email) {
    return (
      <div className="auth-signed-in">
        <span className="user-chip">
          <span className="avatar-dot" />
          {email}
        </span>
        <button
          className="link-button"
          onClick={() => {
            localStorage.removeItem("bizoptimize_token");
            localStorage.removeItem("bizoptimize_email");
            onAuthChange(null);
          }}
        >
          <LogOutIcon size={13} /> Sign out
        </button>
      </div>
    );
  }

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const fn = mode === "login" ? api.login : api.register;
      const { token, email: returnedEmail } = await fn(formEmail, password);
      localStorage.setItem("bizoptimize_token", token);
      localStorage.setItem("bizoptimize_email", returnedEmail);
      onAuthChange(returnedEmail);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form className="auth-panel" onSubmit={submit}>
      <input
        type="email"
        placeholder="email"
        value={formEmail}
        onChange={(e) => setFormEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="password (8+ chars)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit">{mode === "login" ? "Sign in" : "Register"}</button>
      <button
        type="button"
        className="link-button"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
      >
        {mode === "login" ? "Need an account?" : "Have an account?"}
      </button>
      {error && <span className="error small">{error}</span>}
    </form>
  );
}

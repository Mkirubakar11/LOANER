
import { useState } from "react";
import api from "../services/api";
import "./Register.css";

function Register({ onBackToLogin }) {
  const [form, setForm] = useState({
    username: "",
    email: "",
    phone_number: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (form.password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      await api.post("register/", form);

      setSuccess("Registration successful! Please sign in.");
      setForm({
        username: "",
        email: "",
        phone_number: "",
        password: "",
      });
    } catch (err) {
      const data = err.response?.data;

      if (data && typeof data === "object") {
        setError(
          Object.entries(data)
            .map(([field, messages]) =>
              `${field}: ${Array.isArray(messages) ? messages.join(", ") : messages}`
            )
            .join(" | ")
        );
      } else {
        setError("Unable to register. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-page">
      <div className="register-card">
        <div className="register-brand">L</div>

        <h1>Create Owner Account</h1>
        <p>Register to manage your pawn business.</p>

        <form onSubmit={handleSubmit}>
          <label>Username</label>
          <input
            name="username"
            value={form.username}
            onChange={handleChange}
            placeholder="Enter username"
            required
          />

          <label>Email Address</label>
          <input
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            placeholder="Enter email"
            required
          />

          <label>Phone Number</label>
          <input
            name="phone_number"
            value={form.phone_number}
            onChange={handleChange}
            placeholder="Enter phone number"
          />

          <label>Password</label>
          <input
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            placeholder="Create password"
            minLength={8}
            required
          />

          {error && <div className="register-error">{error}</div>}
          {success && <div className="register-success">{success}</div>}

          <button type="submit" disabled={loading}>
            {loading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <div className="register-footer">
          Already have an account?{" "}
          <button type="button" onClick={onBackToLogin}>
            Sign In
          </button>
        </div>
      </div>
    </div>
  );
}

export default Register;

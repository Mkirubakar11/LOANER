
import { useState } from "react";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./Dashboard";
import "./index.css";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(localStorage.getItem("access_token"))
  );

  const [page, setPage] = useState("login");

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    setPage("login");
  };

  if (isAuthenticated) {
    return <Dashboard onLogout={handleLogout} />;
  }

  if (page === "register") {
    return (
      <Register
        onBackToLogin={() => setPage("login")}
      />
    );
  }

  return (
    <Login
      onLogin={handleLogin}
      onRegister={() => setPage("register")}
    />
  );
}

export default App;

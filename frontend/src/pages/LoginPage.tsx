import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { AlertIcon, GearIcon } from "../components/ui/icons";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../lib/errors";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <Panel>
          <div className="brand-mark">
            <GearIcon className="gear-icon" />
            <h1>StockFlow</h1>
            <p>Raktárkezelő Rendszer</p>
          </div>

          {error && (
            <div className="banner banner--error">
              <AlertIcon />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <Field label="E-mail cím" htmlFor="email" required>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                autoFocus
              />
            </Field>
            <Field label="Jelszó" htmlFor="password" required>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" disabled={isSubmitting} style={{ width: "100%" }}>
              {isSubmitting ? "Bejelentkezés…" : "Bejelentkezés"}
            </Button>
          </form>
        </Panel>
        <div className="auth-switch">
          Még nincs fiókja? <Link to="/register">Regisztráció</Link>
        </div>
      </div>
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { AlertIcon, GearIcon } from "../components/ui/icons";
import { Panel } from "../components/ui/Panel";
import { useAuth } from "../context/AuthContext";
import { getErrorMessage } from "../lib/errors";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== passwordConfirm) {
      setError("A két jelszó nem egyezik.");
      return;
    }
    setIsSubmitting(true);
    try {
      await register(email, password, fullName);
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
            <p>Fiók létrehozása</p>
          </div>

          {error && (
            <div className="banner banner--error">
              <AlertIcon />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <Field label="Teljes név" htmlFor="fullName" required>
              <input id="fullName" value={fullName} onChange={(event) => setFullName(event.target.value)} required autoFocus />
            </Field>
            <Field label="E-mail cím" htmlFor="email" required>
              <input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </Field>
            <Field label="Jelszó" htmlFor="password" required>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
              />
            </Field>
            <Field label="Jelszó megerősítése" htmlFor="passwordConfirm" required>
              <input
                id="passwordConfirm"
                type="password"
                value={passwordConfirm}
                onChange={(event) => setPasswordConfirm(event.target.value)}
                required
              />
            </Field>
            <div className="hint" style={{ marginBottom: "1.1rem" }}>
              Az új fiók munkatárs (Staff) jogosultsággal jön létre.
            </div>
            <Button type="submit" disabled={isSubmitting} style={{ width: "100%" }}>
              {isSubmitting ? "Regisztráció…" : "Regisztráció"}
            </Button>
          </form>
        </Panel>
        <div className="auth-switch">
          Már van fiókja? <Link to="/login">Bejelentkezés</Link>
        </div>
      </div>
    </div>
  );
}

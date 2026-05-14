import { FormEvent, useState } from "react";
import { UserProfile } from "../../../shared/lib/mockAuth";
import { validateEmail, validateLength, validatePassword } from "../../../shared/lib/validation";
import styles from "./AuthPage.module.css";

type AuthMode = "login" | "register";

type AuthPageProps = {
  mode: AuthMode;
  onLogin: (email: string, password: string) => Promise<string | null>;
  onRegister: (profile: Pick<UserProfile, "fullName" | "email" | "company" | "role"> & { password: string }) => Promise<string | null>;
  onNavigate: (path: string) => void;
};

export function AuthPage({ mode, onLogin, onRegister, onNavigate }: AuthPageProps) {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [registerForm, setRegisterForm] = useState({
    fullName: "",
    email: "",
    company: "",
    role: "",
    password: "",
  });

  const isLogin = mode === "login";

  async function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = {
      loginEmail: validateEmail(loginEmail),
      loginPassword: validatePassword(loginPassword),
    };

    setErrors(nextErrors);

    if (Object.values(nextErrors).some(Boolean)) {
      return;
    }

    setIsSubmitting(true);
    const authError = await onLogin(loginEmail.trim(), loginPassword);
    setIsSubmitting(false);

    if (authError) {
      setErrors((current) => ({
        ...current,
        auth: authError,
      }));
    }
  }

  async function handleRegisterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = {
      fullName: validateLength(registerForm.fullName, "ФИО", 2, 80),
      email: validateEmail(registerForm.email),
      company: validateLength(registerForm.company, "Компания", 2, 80),
      role: validateLength(registerForm.role, "Роль", 2, 80),
      password: validatePassword(registerForm.password),
    };

    setErrors(nextErrors);

    if (Object.values(nextErrors).some(Boolean)) {
      return;
    }

    setIsSubmitting(true);
    const registerError = await onRegister({
      fullName: registerForm.fullName.trim(),
      email: registerForm.email.trim(),
      company: registerForm.company.trim(),
      role: registerForm.role.trim(),
      password: registerForm.password,
    });
    setIsSubmitting(false);

    if (registerError) {
      setErrors((current) => ({
        ...current,
        auth: registerError,
      }));
    }
  }

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <section className={styles.panel}>
          <div className={styles.logo}>CAD2Tech</div>

          <div className={styles.tabs}>
            <button
              type="button"
              className={isLogin ? styles.tabActive : styles.tab}
              onClick={() => onNavigate("/login")}
            >
              Вход
            </button>
            <button
              type="button"
              className={!isLogin ? styles.tabActive : styles.tab}
              onClick={() => onNavigate("/register")}
            >
              Регистрация
            </button>
          </div>

          {isLogin ? (
            <form className={styles.form} onSubmit={handleLoginSubmit}>
              <div className={styles.formIntro}>
                <h2>Вход</h2>
              </div>

              <label className={styles.field}>
                <span>Email</span>
                <input
                  value={loginEmail}
                  onChange={(event) => {
                    setLoginEmail(event.target.value);
                    setErrors((current) => ({ ...current, loginEmail: "", auth: "" }));
                  }}
                  type="email"
                  aria-invalid={Boolean(errors.loginEmail)}
                />
                {errors.loginEmail ? <span className={styles.errorText}>{errors.loginEmail}</span> : null}
              </label>

              <label className={styles.field}>
                <span>Пароль</span>
                <input
                  value={loginPassword}
                  onChange={(event) => {
                    setLoginPassword(event.target.value);
                    setErrors((current) => ({ ...current, loginPassword: "", auth: "" }));
                  }}
                  type="password"
                  aria-invalid={Boolean(errors.loginPassword)}
                />
                {errors.loginPassword ? <span className={styles.errorText}>{errors.loginPassword}</span> : null}
              </label>

              {errors.auth ? <div className={styles.formError}>{errors.auth}</div> : null}

              <button type="submit" className={styles.primaryButton} disabled={isSubmitting}>
                {isSubmitting ? "Входим..." : "Войти"}
              </button>
            </form>
          ) : (
            <form className={styles.form} onSubmit={handleRegisterSubmit}>
              <div className={styles.formIntro}>
                <h2>Регистрация</h2>
              </div>

              <label className={styles.field}>
                <span>ФИО</span>
                <input
                  value={registerForm.fullName}
                  onChange={(event) => {
                    setRegisterForm((current) => ({ ...current, fullName: event.target.value }));
                    setErrors((current) => ({ ...current, fullName: "", auth: "" }));
                  }}
                  type="text"
                  aria-invalid={Boolean(errors.fullName)}
                />
                {errors.fullName ? <span className={styles.errorText}>{errors.fullName}</span> : null}
              </label>

              <label className={styles.field}>
                <span>Email</span>
                <input
                  value={registerForm.email}
                  onChange={(event) => {
                    setRegisterForm((current) => ({ ...current, email: event.target.value }));
                    setErrors((current) => ({ ...current, email: "", auth: "" }));
                  }}
                  type="email"
                  aria-invalid={Boolean(errors.email)}
                />
                {errors.email ? <span className={styles.errorText}>{errors.email}</span> : null}
              </label>

              <div className={styles.doubleFields}>
                <label className={styles.field}>
                  <span>Компания</span>
                  <input
                    value={registerForm.company}
                    onChange={(event) => {
                      setRegisterForm((current) => ({ ...current, company: event.target.value }));
                      setErrors((current) => ({ ...current, company: "", auth: "" }));
                    }}
                    type="text"
                    aria-invalid={Boolean(errors.company)}
                  />
                  {errors.company ? <span className={styles.errorText}>{errors.company}</span> : null}
                </label>

                <label className={styles.field}>
                  <span>Роль</span>
                  <input
                    value={registerForm.role}
                    onChange={(event) => {
                      setRegisterForm((current) => ({ ...current, role: event.target.value }));
                      setErrors((current) => ({ ...current, role: "", auth: "" }));
                    }}
                    type="text"
                    aria-invalid={Boolean(errors.role)}
                  />
                  {errors.role ? <span className={styles.errorText}>{errors.role}</span> : null}
                </label>
              </div>

              <label className={styles.field}>
                <span>Пароль</span>
                <input
                  value={registerForm.password}
                  onChange={(event) => {
                    setRegisterForm((current) => ({ ...current, password: event.target.value }));
                    setErrors((current) => ({ ...current, password: "", auth: "" }));
                  }}
                  type="password"
                  aria-invalid={Boolean(errors.password)}
                />
                {errors.password ? <span className={styles.errorText}>{errors.password}</span> : null}
              </label>

              {errors.auth ? <div className={styles.formError}>{errors.auth}</div> : null}

              <button type="submit" className={styles.primaryButton} disabled={isSubmitting}>
                {isSubmitting ? "Создаем..." : "Создать профиль"}
              </button>
            </form>
          )}
        </section>
      </main>
    </div>
  );
}

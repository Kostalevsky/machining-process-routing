import { FormEvent, useState } from "react";
import { UserProfile } from "../../../shared/lib/mockAuth";
import styles from "./AuthPage.module.scss";

type AuthMode = "login" | "register";

type AuthPageProps = {
  mode: AuthMode;
  onLogin: (email: string) => void;
  onRegister: (profile: Pick<UserProfile, "fullName" | "email" | "company" | "role">) => void;
  onNavigate: (path: string) => void;
};

export function AuthPage({ mode, onLogin, onRegister, onNavigate }: AuthPageProps) {
  const [loginEmail, setLoginEmail] = useState("anna.smirnova@cad2tech.ru");
  const [loginPassword, setLoginPassword] = useState("demo12345");
  const [registerForm, setRegisterForm] = useState({
    fullName: "Анна Смирнова",
    email: "anna.smirnova@cad2tech.ru",
    company: "CAD2Tech",
    role: "Инженер-проектировщик",
    password: "demo12345",
  });

  const isLogin = mode === "login";

  function handleLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!loginEmail.trim() || !loginPassword.trim()) {
      return;
    }
    onLogin(loginEmail.trim());
  }

  function handleRegisterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!registerForm.fullName.trim() || !registerForm.email.trim()) {
      return;
    }
    onRegister({
      fullName: registerForm.fullName.trim(),
      email: registerForm.email.trim(),
      company: registerForm.company.trim(),
      role: registerForm.role.trim(),
    });
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
                <input value={loginEmail} onChange={(event) => setLoginEmail(event.target.value)} type="email" />
              </label>

              <label className={styles.field}>
                <span>Пароль</span>
                <input value={loginPassword} onChange={(event) => setLoginPassword(event.target.value)} type="password" />
              </label>

              <button type="submit" className={styles.primaryButton}>
                Войти
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
                  onChange={(event) => setRegisterForm((current) => ({ ...current, fullName: event.target.value }))}
                  type="text"
                />
              </label>

              <label className={styles.field}>
                <span>Email</span>
                <input
                  value={registerForm.email}
                  onChange={(event) => setRegisterForm((current) => ({ ...current, email: event.target.value }))}
                  type="email"
                />
              </label>

              <div className={styles.doubleFields}>
                <label className={styles.field}>
                  <span>Компания</span>
                  <input
                    value={registerForm.company}
                    onChange={(event) => setRegisterForm((current) => ({ ...current, company: event.target.value }))}
                    type="text"
                  />
                </label>

                <label className={styles.field}>
                  <span>Роль</span>
                  <input
                    value={registerForm.role}
                    onChange={(event) => setRegisterForm((current) => ({ ...current, role: event.target.value }))}
                    type="text"
                  />
                </label>
              </div>

              <label className={styles.field}>
                <span>Пароль</span>
                <input
                  value={registerForm.password}
                  onChange={(event) => setRegisterForm((current) => ({ ...current, password: event.target.value }))}
                  type="password"
                />
              </label>

              <button type="submit" className={styles.primaryButton}>
                Создать профиль
              </button>
            </form>
          )}
        </section>
      </main>
    </div>
  );
}

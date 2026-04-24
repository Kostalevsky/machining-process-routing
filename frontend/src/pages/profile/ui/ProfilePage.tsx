import { ChangeEvent, FormEvent, useState } from "react";
import { UserProfile } from "../../../shared/lib/mockAuth";
import { validateEmail, validateLength, validatePhone } from "../../../shared/lib/validation";
import { AppHeader } from "../../../widgets/app-header";
import styles from "./ProfilePage.module.scss";

type ProfilePageProps = {
  profile: UserProfile;
  currentPath: string;
  onNavigate: (path: string) => void;
  onLogout: () => void;
  onSave: (profile: UserProfile) => void;
};

export function ProfilePage({ profile, currentPath, onNavigate, onLogout, onSave }: ProfilePageProps) {
  const [form, setForm] = useState(profile);
  const [errors, setErrors] = useState<Record<keyof UserProfile, string>>({
    fullName: "",
    email: "",
    phone: "",
    company: "",
    role: "",
    about: "",
  });

  function handleChange<K extends keyof UserProfile>(key: K) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setForm((current) => ({
        ...current,
        [key]: event.target.value,
      }));
    };
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = {
      fullName: validateLength(form.fullName, "ФИО", 2, 80),
      email: validateEmail(form.email),
      phone: validatePhone(form.phone),
      company: validateLength(form.company, "Компания", 2, 80),
      role: validateLength(form.role, "Роль", 2, 80),
      about: form.about.trim().length > 300 ? "Описание должно содержать не более 300 символов" : "",
    };

    setErrors(nextErrors);

    if (Object.values(nextErrors).some(Boolean)) {
      return;
    }

    onSave(form);
  }

  return (
    <div className={styles.page}>
      <AppHeader
        currentPath={currentPath}
        profile={profile}
        onNavigate={onNavigate}
        onLogout={onLogout}
      />

      <main className={styles.main}>
        <div className={styles.layout}>
          <aside className={styles.summaryCard}>
            <div className={styles.avatar}>{profile.fullName.slice(0, 1)}</div>
            <h2>{profile.fullName}</h2>
            <span>{profile.role}</span>

            <dl className={styles.summaryList}>
              <div>
                <dt>Email</dt>
                <dd>{profile.email}</dd>
              </div>
              <div>
                <dt>Телефон</dt>
                <dd>{profile.phone}</dd>
              </div>
              <div>
                <dt>Компания</dt>
                <dd>{profile.company}</dd>
              </div>
            </dl>
          </aside>

          <section className={styles.formCard}>
            <form className={styles.form} onSubmit={handleSubmit}>
              <div className={styles.formHeader}>
                <h2>Редактирование профиля</h2>
                <button type="submit" className={styles.primaryButton}>
                  Сохранить изменения
                </button>
              </div>

              <div className={styles.grid}>
                <label className={styles.field}>
                  <span>ФИО</span>
                  <input value={form.fullName} onChange={handleChange("fullName")} aria-invalid={Boolean(errors.fullName)} />
                  {errors.fullName ? <span className={styles.errorText}>{errors.fullName}</span> : null}
                </label>

                <label className={styles.field}>
                  <span>Email</span>
                  <input type="email" value={form.email} onChange={handleChange("email")} aria-invalid={Boolean(errors.email)} />
                  {errors.email ? <span className={styles.errorText}>{errors.email}</span> : null}
                </label>

                <label className={styles.field}>
                  <span>Телефон</span>
                  <input value={form.phone} onChange={handleChange("phone")} aria-invalid={Boolean(errors.phone)} />
                  {errors.phone ? <span className={styles.errorText}>{errors.phone}</span> : null}
                </label>

                <label className={styles.field}>
                  <span>Компания</span>
                  <input value={form.company} onChange={handleChange("company")} aria-invalid={Boolean(errors.company)} />
                  {errors.company ? <span className={styles.errorText}>{errors.company}</span> : null}
                </label>

                <label className={styles.field}>
                  <span>Роль</span>
                  <input value={form.role} onChange={handleChange("role")} aria-invalid={Boolean(errors.role)} />
                  {errors.role ? <span className={styles.errorText}>{errors.role}</span> : null}
                </label>
              </div>

              <label className={styles.field}>
                <span>О себе</span>
                <textarea rows={6} value={form.about} onChange={handleChange("about")} aria-invalid={Boolean(errors.about)} />
                {errors.about ? <span className={styles.errorText}>{errors.about}</span> : null}
              </label>
            </form>
          </section>
        </div>
      </main>
    </div>
  );
}

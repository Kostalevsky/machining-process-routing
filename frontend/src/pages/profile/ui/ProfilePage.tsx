import { ChangeEvent, FormEvent, useState } from "react";
import { UserProfile } from "../../../shared/lib/mockAuth";
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
                  <input value={form.fullName} onChange={handleChange("fullName")} />
                </label>

                <label className={styles.field}>
                  <span>Email</span>
                  <input type="email" value={form.email} onChange={handleChange("email")} />
                </label>

                <label className={styles.field}>
                  <span>Телефон</span>
                  <input value={form.phone} onChange={handleChange("phone")} />
                </label>

                <label className={styles.field}>
                  <span>Компания</span>
                  <input value={form.company} onChange={handleChange("company")} />
                </label>

                <label className={styles.field}>
                  <span>Роль</span>
                  <input value={form.role} onChange={handleChange("role")} />
                </label>
              </div>

              <label className={styles.field}>
                <span>О себе</span>
                <textarea rows={6} value={form.about} onChange={handleChange("about")} />
              </label>
            </form>
          </section>
        </div>
      </main>
    </div>
  );
}

import styles from "./JsonList.module.scss";

type JsonListProps = {
  files: string[];
};

export function JsonList({ files }: JsonListProps) {
  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // noop
    }
  };

  return (
    <ul className={styles.list}>
      {files.map((href, index) => (
        <li key={href} className={styles.item}>
          <div className={styles.fileInfo}>
            <span className={styles.fileDot} />
            <a href={href} target="_blank" className={styles.link} rel="noreferrer">
              {decodeURIComponent(href.split("/").pop() || `file-${index}.json`)}
            </a>
          </div>
          <div className={styles.actions}>
            <a href={href} download className={styles.action}>
              Скачать
            </a>
            <button type="button" onClick={() => copy(href)} className={styles.action}>
              Копировать URL
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

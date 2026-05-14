import styles from "./ImageMasonry.module.scss";

type ImageMasonryProps = {
  images: string[];
};

export function ImageMasonry({ images }: ImageMasonryProps) {
  return (
    <div className={styles.grid}>
      {images.map((src, index) => (
        <a key={src} href={src} target="_blank" className={styles.item} rel="noreferrer">
          <img src={src} alt={`view-${index}`} className={styles.image} loading="lazy" />
        </a>
      ))}
    </div>
  );
}

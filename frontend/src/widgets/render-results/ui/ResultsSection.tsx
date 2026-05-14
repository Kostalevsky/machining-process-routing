import { ImageMasonry } from "./ImageMasonry";
import { JsonList } from "./JsonList";
import styles from "./ResultsSection.module.scss";

type ResultsSectionProps = {
  images: string[];
  jsons: string[];
};

export function ResultsSection({ images, jsons }: ResultsSectionProps) {
  const previewImage = images[0];

  return (
    <section className={styles.section}>
      <div className={styles.previewCard}>
        {previewImage ? (
          <img src={previewImage} alt="Предпросмотр 3D-модели" className={styles.previewImage} />
        ) : (
          <div className={styles.previewPlaceholder}>
            <span>Здесь будет доступен</span>
            <span>предпросмотр 3D модели</span>
          </div>
        )}
      </div>

      {images.length > 1 ? (
        <div className={styles.galleryCard}>
          <div className={styles.blockTitle}>Результаты рендера</div>
          <ImageMasonry images={images} />
        </div>
      ) : null}

      {jsons.length > 0 ? (
        <div className={styles.jsonCard}>
          <div className={styles.blockTitle}>JSON-описания</div>
          <JsonList files={jsons} />
        </div>
      ) : null}
    </section>
  );
}

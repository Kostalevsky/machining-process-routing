from __future__ import annotations

from hashlib import sha256
from io import BytesIO

import numpy as np
from fastapi import HTTPException, status
from PIL import Image
from sklearn.manifold import Isomap
from sqlalchemy.orm import Session

from app.infrastructure.storage import S3Storage
from app.models.artifact import Artifact
from app.models.enums import ArtifactType, RunStatus
from app.models.run import Run
from app.models.run_event import RunEvent
from app.modules.artifacts.service import build_collage_object_key, create_artifact


def generate_collages_for_run(
    db: Session,
    *,
    run: Run,
    storage: S3Storage,
    counts: list[int],
    selected_count: int | None,
) -> Run:
    render_artifacts = sorted(
        [artifact for artifact in run.artifacts if artifact.type == ArtifactType.RENDER],
        key=lambda item: item.created_at,
    )
    if len(render_artifacts) < 3:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="At least 3 render images are required to build a collage.",
        )

    normalized_counts = _normalize_counts(counts, render_artifacts_count=len(render_artifacts))
    if selected_count is not None and selected_count not in normalized_counts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_count must be one of the generated collage sizes.",
        )

    images, image_vectors = _load_render_images(storage, render_artifacts)
    n_neighbors = max(1, min(5, len(image_vectors) - 1))
    projected = Isomap(n_components=2, n_neighbors=n_neighbors).fit_transform(image_vectors)

    created_collages: dict[int, Artifact] = {}
    for count in normalized_counts:
        selected_indices = _get_farthest_indices(projected, count)
        collage_image = _build_collage_image([images[index] for index in selected_indices], count)
        collage_bytes = _image_to_png_bytes(collage_image)
        object_key = build_collage_object_key(user_id=run.user_id, run_id=run.id, count=count)
        checksum = sha256(collage_bytes).hexdigest()

        storage.upload_bytes(data=collage_bytes, object_key=object_key, content_type="image/png")
        artifact = create_artifact(
            artifact_type=ArtifactType.COLLAGE,
            bucket=storage.bucket,
            user_id=run.user_id,
            run_id=run.id,
            file_name=f"collage_{count}.png",
            content_type="image/png",
            object_key=object_key,
            size_bytes=len(collage_bytes),
            checksum=checksum,
            meta_json={
                "collage_size": count,
                "source_render_artifact_ids": [
                    render_artifacts[index].id for index in selected_indices
                ],
                "selection_strategy": "isomap_farthest_points",
            },
        )
        db.add(artifact)
        db.flush()
        created_collages[count] = artifact
        db.add(
            RunEvent(
                run_id=run.id,
                event_type="collage_created",
                payload_json={"artifact_id": artifact.id, "collage_size": count},
            )
        )

    if selected_count is None:
        selected_count = normalized_counts[0]

    run.selected_collage_artifact_id = created_collages[selected_count].id
    run.status = RunStatus.COLLAGES_READY
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def select_collage_for_run(db: Session, *, run: Run, collage_artifact_id: int) -> Run:
    collage_artifact = next(
        (
            artifact
            for artifact in run.artifacts
            if artifact.id == collage_artifact_id and artifact.type == ArtifactType.COLLAGE
        ),
        None,
    )
    if collage_artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collage artifact not found for this run.",
        )

    run.selected_collage_artifact_id = collage_artifact_id
    db.add(run)
    db.add(
        RunEvent(
            run_id=run.id,
            event_type="collage_selected",
            payload_json={"artifact_id": collage_artifact_id},
        )
    )
    db.commit()
    db.refresh(run)
    return run


def _normalize_counts(counts: list[int], *, render_artifacts_count: int) -> list[int]:
    allowed = {3, 4, 6}
    requested = counts or [3, 4, 6]
    normalized = sorted(
        {
            count
            for count in requested
            if count in allowed and count <= render_artifacts_count
        }
    )
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "counts must contain at least one of 3, 4, or 6 "
                "within the available render count."
            ),
        )
    return normalized


def _load_render_images(
    storage: S3Storage,
    render_artifacts: list[Artifact],
) -> tuple[list[Image.Image], np.ndarray]:
    images: list[Image.Image] = []
    vectors: list[np.ndarray] = []

    for artifact in render_artifacts:
        image_bytes = storage.download_bytes(artifact.object_key)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        images.append(image.copy())

        grayscale = image.convert("L").resize((64, 64))
        vectors.append(np.array(grayscale, dtype=np.float32).reshape(-1))

    return images, np.stack(vectors)


def _get_farthest_indices(points: np.ndarray, count: int) -> list[int]:
    centroid = points.mean(axis=0)
    distances_to_centroid = np.linalg.norm(points - centroid, axis=1)
    selected_indices = [int(np.argmax(distances_to_centroid))]

    while len(selected_indices) < count:
        remaining = [index for index in range(len(points)) if index not in selected_indices]
        scores = []
        for index in remaining:
            distances = [
                np.linalg.norm(points[index] - points[selected])
                for selected in selected_indices
            ]
            scores.append((min(distances), index))
        _, next_index = max(scores, key=lambda item: item[0])
        selected_indices.append(next_index)

    return selected_indices


def _build_collage_image(images: list[Image.Image], count: int) -> Image.Image:
    normalized_images = [image.convert("RGB") for image in images]
    width, height = normalized_images[0].size

    if count == 3:
        collage = Image.new("RGB", (width * 3, height))
        positions = [(0, 0), (width, 0), (width * 2, 0)]
    elif count == 4:
        collage = Image.new("RGB", (width * 2, height * 2))
        positions = [(0, 0), (width, 0), (0, height), (width, height)]
    elif count == 6:
        collage = Image.new("RGB", (width * 3, height * 2))
        positions = [
            (0, 0),
            (width, 0),
            (width * 2, 0),
            (0, height),
            (width, height),
            (width * 2, height),
        ]
    else:
        raise ValueError(f"Unsupported collage size: {count}")

    for image, position in zip(normalized_images, positions, strict=True):
        collage.paste(image.resize((width, height)), position)

    return collage


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()

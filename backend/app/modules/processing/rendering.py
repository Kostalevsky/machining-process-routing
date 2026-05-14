from __future__ import annotations

import pickle
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import BACKEND_ROOT, settings


@dataclass
class RenderedImage:
    file_name: str
    content: bytes
    render_index: int


def render_source_model(*, source_file_name: str, source_bytes: bytes) -> list[RenderedImage]:
    script_path = Path(settings.blender_render_script_path)
    if not script_path.is_absolute():
        script_path = (BACKEND_ROOT / script_path).resolve()
    if not script_path.exists():
        raise RuntimeError(f"Blender render script was not found: {script_path}")

    with tempfile.TemporaryDirectory(prefix="run-render-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = tmp_path / source_file_name
        source_path.write_bytes(source_bytes)

        object_paths_pkl = tmp_path / "object_paths.pkl"
        with object_paths_pkl.open("wb") as file:
            pickle.dump([str(source_path)], file)

        command = [
            settings.blender_binary,
            "-b",
            "-P",
            str(script_path),
            "--",
            "--object_path_pkl",
            str(object_paths_pkl),
            "--parent_dir",
            str(tmp_path),
            "--num_images",
            str(settings.render_num_images),
            "--light_mode",
            settings.render_light_mode,
            "--camera_pose",
            settings.render_camera_pose,
            "--camera_dist_min",
            str(settings.render_camera_dist_min),
            "--camera_dist_max",
            str(settings.render_camera_dist_max),
        ]
        subprocess.run(
            command,
            cwd=str(BACKEND_ROOT),
            check=True,
            timeout=settings.render_timeout_seconds,
        )

        output_dir = tmp_path / "rendered_imgs" / source_path.stem
        return _collect_rendered_images(output_dir)


def _collect_rendered_images(output_dir: Path) -> list[RenderedImage]:
    if not output_dir.exists():
        raise RuntimeError(f"Render output directory was not created: {output_dir}")

    rendered_paths = sorted(path for path in output_dir.glob("*.png") if path.stem.isdigit())
    if not rendered_paths:
        raise RuntimeError("Blender did not produce any base render images.")

    return [
        RenderedImage(
            file_name=path.name,
            content=path.read_bytes(),
            render_index=index,
        )
        for index, path in enumerate(rendered_paths, start=1)
    ]

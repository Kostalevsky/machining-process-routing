from pathlib import Path

import pytest
from app.modules.processing.rendering import _collect_rendered_images


def test_collect_rendered_images_only_uses_base_pngs(tmp_path: Path) -> None:
    (tmp_path / "00000.png").write_bytes(b"base-0")
    (tmp_path / "00001.png").write_bytes(b"base-1")
    (tmp_path / "00001_r.png").write_bytes(b"red")
    (tmp_path / "00001_depth.png").write_bytes(b"depth")
    (tmp_path / "info.json").write_text("{}", encoding="utf-8")

    rendered_images = _collect_rendered_images(tmp_path)

    assert [item.file_name for item in rendered_images] == ["00000.png", "00001.png"]
    assert [item.content for item in rendered_images] == [b"base-0", b"base-1"]
    assert [item.render_index for item in rendered_images] == [1, 2]


def test_collect_rendered_images_requires_output_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"

    with pytest.raises(RuntimeError, match="Render output directory was not created"):
        _collect_rendered_images(missing_dir)


def test_collect_rendered_images_requires_base_pngs(tmp_path: Path) -> None:
    (tmp_path / "00001_r.png").write_bytes(b"red")
    (tmp_path / "00001_depth.png").write_bytes(b"depth")

    with pytest.raises(RuntimeError, match="Blender did not produce any base render images"):
        _collect_rendered_images(tmp_path)

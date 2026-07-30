from __future__ import annotations

from pathlib import Path

from backend.services.apk_service import ApkService


APPLICATIONS_YAML = """\
phone:
  - id: phone_app
    display_name: Phone App
    filename: phone.apk
    package_name: null
    required: true
watch:
  - id: watch_app
    display_name: Watch App
    filename: watch.apk
    package_name: null
    required: true
"""


def create_catalog(project_root: Path) -> None:
    config = project_root / "config"
    config.mkdir(parents=True)
    (config / "applications.yaml").write_text(
        APPLICATIONS_YAML, encoding="utf-8"
    )
    (project_root / "apks" / "phone").mkdir(parents=True)
    (project_root / "apks" / "watch").mkdir(parents=True)


def test_all_configured_apks_are_validated(tmp_path: Path) -> None:
    create_catalog(tmp_path)
    (tmp_path / "apks" / "phone" / "phone.apk").write_bytes(b"phone")
    (tmp_path / "apks" / "watch" / "watch.apk").write_bytes(b"watch")

    result = ApkService(tmp_path).validate_all()

    assert result.valid
    assert len(result.files) == 2
    assert all(status.size_bytes > 0 for status in result.files)


def test_missing_apk_blocks_validation(tmp_path: Path) -> None:
    create_catalog(tmp_path)
    (tmp_path / "apks" / "phone" / "phone.apk").write_bytes(b"phone")

    result = ApkService(tmp_path).validate_all()

    assert not result.valid
    assert [status.application.id for status in result.missing_required] == [
        "watch_app"
    ]

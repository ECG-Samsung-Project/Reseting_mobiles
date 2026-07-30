from __future__ import annotations

from pathlib import Path

from backend.adb.adb_command import AdbCommandResult
from backend.models.setup_input import SetupInput
from backend.services.preflight_service import (
    PreflightCheckStatus,
    PreflightService,
)


class PreflightAdbClient:
    def version(self) -> AdbCommandResult:
        return AdbCommandResult(
            command=("adb", "version"),
            stdout="Android Debug Bridge version 1.0.41",
            stderr="",
            return_code=0,
            duration_seconds=0.01,
        )

    def run(self, arguments: list[str], **_kwargs: object) -> AdbCommandResult:
        assert arguments == ["devices", "-l"]
        return AdbCommandResult(
            command=("adb", "devices", "-l"),
            stdout=(
                "R5CX123 device usb:1-2 product:a56x "
                "model:SM-A566B device:a56x transport_id:4"
            ),
            stderr="",
            return_code=0,
            duration_seconds=0.01,
        )

    def get_property(
        self, property_name: str, *, device_id: str, timeout_seconds: float = 15
    ) -> str:
        del timeout_seconds
        assert device_id == "R5CX123"
        values = {
            "ro.product.manufacturer": "Samsung",
            "ro.product.model": "SM-A566B",
            "ro.product.device": "a56x",
            "ro.build.version.release": "16",
            "ro.build.version.sdk": "36",
            "ro.build.display.id": "BUILD123",
        }
        return values[property_name]


def prepare_project(project_root: Path) -> None:
    (project_root / "config").mkdir(parents=True)
    (project_root / "config" / "settings.yaml").write_text(
        """\
adb:
  executable: null
  default_timeout_seconds: 60
backup:
  minimum_free_space_bytes: 0
phone:
  expected_manufacturer: Samsung
  expected_model_hint: Galaxy A56
installation:
  allow_downgrade: false
""",
        encoding="utf-8",
    )
    (project_root / "config" / "applications.yaml").write_text(
        """\
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
""",
        encoding="utf-8",
    )
    phone_dir = project_root / "apks" / "phone"
    watch_dir = project_root / "apks" / "watch"
    phone_dir.mkdir(parents=True)
    watch_dir.mkdir(parents=True)
    (phone_dir / "phone.apk").write_bytes(b"phone")
    (watch_dir / "watch.apk").write_bytes(b"watch")


def make_setup_input() -> SetupInput:
    return SetupInput(
        participant_id="EDI-21-2196",
        kit_id="KIT-03",
        google_email="ecg_p21@uea.edu.br",
        google_password="não-persistir",
    )


def test_preflight_reports_ready_without_using_real_adb(tmp_path: Path) -> None:
    prepare_project(tmp_path)

    report = PreflightService(
        tmp_path,
        adb_client=PreflightAdbClient(),  # type: ignore[arg-type]
    ).run(make_setup_input())

    assert report.ready
    assert report.phone is not None
    assert report.phone.serial == "R5CX123"
    assert report.summary["requires_operator_confirmation"] is True
    assert "google_password" not in report.summary
    assert all(
        check.status is PreflightCheckStatus.PASSED for check in report.checks
    )


def test_missing_apk_is_reported_without_stopping_other_checks(
    tmp_path: Path,
) -> None:
    prepare_project(tmp_path)
    (tmp_path / "apks" / "watch" / "watch.apk").unlink()

    report = PreflightService(
        tmp_path,
        adb_client=PreflightAdbClient(),  # type: ignore[arg-type]
    ).run(make_setup_input())

    assert not report.ready
    apk_check = next(check for check in report.checks if check.id == "apks")
    assert apk_check.status is PreflightCheckStatus.FAILED
    assert "watch.apk" in apk_check.message
    assert any(check.id == "phone" for check in report.checks)

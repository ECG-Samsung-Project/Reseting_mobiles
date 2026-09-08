from backend.services.adb_service import run_command
from backend.config import COMMON_PERMISSIONS

def get_declared_permissions(package_name: str) -> list[str]:
    output = run_command(
        ["adb", "shell", "dumpsys", "package", package_name],
        raise_on_error=False,
    )

    permissions = []
    capture = False

    for line in output.splitlines():
        stripped = line.strip()

        if stripped.startswith("requested permissions:"):
            capture = True
            continue

        if capture:
            if not stripped:
                break

            if stripped.startswith("install permissions:"):
                break

            if stripped.startswith("User "):
                break

            if stripped.startswith("android.permission."):
                permissions.append(stripped)

    return permissions


def grant_permission(package_name: str, permission: str) -> str:
    return run_command(
        [
            "adb",
            "shell",
            "pm",
            "grant",
            package_name,
            permission,
        ],
        raise_on_error=False,
    )


def grant_common_permissions(package_name: str) -> list[str]:
    declared_permissions = get_declared_permissions(package_name)

    granted = []

    for permission in COMMON_PERMISSIONS:
        if permission not in declared_permissions:
            continue

        output = grant_permission(package_name, permission)

        if (
            "Exception" not in output
            and "not a changeable permission type" not in output
            and "Unknown permission" not in output
        ):
            granted.append(permission)

    return granted

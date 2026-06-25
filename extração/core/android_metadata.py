from core.adb_client import AdbClient


def get_android_device_metadata(
    adb: AdbClient,
    device_id: str,
    device_name: str,
    name_field: str,
) -> dict:
    return {
        name_field: device_name,
        "adb_device_id": device_id,
        "manufacturer": adb.get_property("ro.product.manufacturer"),
        "brand": adb.get_property("ro.product.brand"),
        "model": adb.get_property("ro.product.model"),
        "device": adb.get_property("ro.product.device"),
        "product_name": adb.get_property("ro.product.name"),
        "android_version": adb.get_property("ro.build.version.release"),
        "android_sdk": adb.get_property("ro.build.version.sdk"),
        "build_id": adb.get_property("ro.build.id"),
        "build_fingerprint": adb.get_property("ro.build.fingerprint"),
        "serial_number": adb.get_property("ro.serialno"),
    }
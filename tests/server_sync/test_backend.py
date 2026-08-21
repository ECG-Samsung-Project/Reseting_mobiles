import tempfile
import unittest
from pathlib import Path, PurePosixPath

from server_sync.backend import ServerSyncBackend
from server_sync.config import DEFAULT_SYNC_FOLDERS, ServerSyncConfig
from server_sync.models import RemoteInventory


class EmptyLocalScanner:
    def scan(self, _config: ServerSyncConfig):
        return ()


class EmptyRemoteScanner:
    def scan(self, config: ServerSyncConfig, client):
        client.config_seen_during_scan = config
        return RemoteInventory(files=())


class FakeClient:
    def __init__(self, config: ServerSyncConfig) -> None:
        self.config = config
        self.config_seen_during_scan = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class ServerSyncBackendTests(unittest.TestCase):
    def test_remote_status_does_not_require_local_raw_folder(self) -> None:
        config = ServerSyncConfig(
            host="example.test",
            username="collector",
            local_raw_root=Path("missing-local-raw").resolve(),
            remote_raw_root=PurePosixPath("/remote/raw"),
        )
        backend = ServerSyncBackend(
            config_loader=lambda: config,
            client_factory=FakeClient,  # type: ignore[arg-type]
            remote_scanner=EmptyRemoteScanner(),  # type: ignore[arg-type]
        )

        inventory = backend.inspect_remote()

        self.assertEqual(inventory.files, ())

    def test_requests_password_and_keeps_it_out_of_safe_summary(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()

            for folder in DEFAULT_SYNC_FOLDERS:
                (local_root / folder).mkdir()

            config = ServerSyncConfig(
                host="example.test",
                username="collector",
                local_raw_root=local_root,
                remote_raw_root=PurePosixPath("/remote/raw"),
                authentication_method="password",
            )
            clients: list[FakeClient] = []

            def client_factory(runtime_config: ServerSyncConfig):
                client = FakeClient(runtime_config)
                clients.append(client)
                return client

            prompts: list[tuple[str, str]] = []

            def password_prompt(host: str, username: str) -> str:
                prompts.append((host, username))
                return "runtime-secret"

            backend = ServerSyncBackend(
                config_loader=lambda: config,
                client_factory=client_factory,  # type: ignore[arg-type]
                local_scanner=EmptyLocalScanner(),  # type: ignore[arg-type]
                remote_scanner=EmptyRemoteScanner(),  # type: ignore[arg-type]
            )
            backend.compare_all(password_prompt=password_prompt)

        self.assertEqual(prompts, [("example.test", "collector")])
        self.assertEqual(clients[0].config.password, "runtime-secret")
        self.assertNotIn(
            "runtime-secret",
            backend.get_active_connection_summary() or "",
        )

    def test_cancelled_password_prompt_stops_before_connecting(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            local_root = Path(temporary).resolve()
            config = ServerSyncConfig(
                host="example.test",
                username="collector",
                local_raw_root=local_root,
                remote_raw_root=PurePosixPath("/remote/raw"),
                authentication_method="password",
            )
            client_calls = 0

            def client_factory(_config: ServerSyncConfig):
                nonlocal client_calls
                client_calls += 1
                return FakeClient(_config)

            backend = ServerSyncBackend(
                config_loader=lambda: config,
                client_factory=client_factory,  # type: ignore[arg-type]
                local_scanner=EmptyLocalScanner(),  # type: ignore[arg-type]
                remote_scanner=EmptyRemoteScanner(),  # type: ignore[arg-type]
            )

            with self.assertRaisesRegex(RuntimeError, "cancelada"):
                backend.compare_all(
                    password_prompt=lambda _host, _username: None
                )

        self.assertEqual(client_calls, 0)


if __name__ == "__main__":
    unittest.main()

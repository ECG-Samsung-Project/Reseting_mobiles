"""Ponto de entrada da interface e do preflight em linha de comando."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from pydantic import ValidationError

from backend.models.setup_input import SetupInput
from backend.services.preflight_service import PreflightService

PROJECT_ROOT = Path(__file__).resolve().parent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ECG Device Setup: interface desktop e diagnóstico não destrutivo."
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Executa as validações em linha de comando, sem abrir a interface.",
    )
    parser.add_argument("--participant-id")
    parser.add_argument("--kit-id")
    parser.add_argument("--google-email")
    return parser


def run_preflight(args: argparse.Namespace) -> int:
    participant_id = args.participant_id or input("Participante: ").strip()
    kit_id = args.kit_id or input("Kit: ").strip()
    google_email = args.google_email or input("E-mail Google: ").strip()
    google_password = getpass.getpass(
        "Senha Google (somente memória; não será registrada): "
    )
    try:
        setup_input = SetupInput(
            participant_id=participant_id,
            kit_id=kit_id,
            google_email=google_email,
            google_password=google_password,
        )
    except ValidationError as exc:
        first_error = str(exc.errors(include_url=False)[0]["msg"]).removeprefix(
            "Value error, "
        )
        print(f"Dados inválidos: {first_error}")
        return 2

    report = PreflightService(PROJECT_ROOT).run(setup_input)
    print("\nPré-validação")
    for check in report.checks:
        print(f"[{check.status.value.upper():7}] {check.label}: {check.message}")
    print(
        "\nResultado: "
        + (
            "pronto para confirmação do operador"
            if report.ready
            else "existem pendências que impedem o provisionamento"
        )
    )
    return 0 if report.ready else 1


def main() -> int:
    args = build_parser().parse_args()
    if args.preflight:
        return run_preflight(args)
    try:
        from frontend.app import run_app
    except ImportError as exc:
        print(
            "Não foi possível carregar o frontend PySide6. "
            "Instale as dependências com: python -m pip install -r requirements.txt"
        )
        print(f"Detalhe técnico: {exc}")
        return 3
    return run_app(PROJECT_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())

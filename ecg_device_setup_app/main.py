"""Ponto de entrada temporário da Etapa 1.

O wizard PySide6 pertence à Etapa 4. Até lá, este comando permite validar a
infraestrutura local sem executar ações destrutivas.
"""

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
        description="Diagnóstico não destrutivo do ECG Device Setup App."
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Executa as validações da Etapa 1.",
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
        first_error = exc.errors(include_url=False)[0]["msg"]
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
    print(
        "Etapa 1 instalada. Use --preflight para o diagnóstico. "
        "O frontend PySide6 será implementado na Etapa 4."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

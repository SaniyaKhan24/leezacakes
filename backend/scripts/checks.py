"""Shared fail-fast checks: no real database credentials or connections."""

import argparse
import os
import secrets

# Fixed local tool commands only, never a shell.
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label, args, env):
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([sys.executable, *args], cwd=ROOT, env=env, check=True)  # nosec B603


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-dependency-audit", action="store_true")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Python 3.12 is required.")
    env = os.environ.copy()
    # Remove ambient application configuration; fixture settings never load .env.
    for name in list(env):
        if name.startswith(("DJANGO_", "DB_", "CORS_", "CSRF_")) or name in {
            "API_DOCS_ENABLED",
            "TRUST_PROXY_SSL_HEADER",
            "HSTS_INCLUDE_SUBDOMAINS",
            "HSTS_PRELOAD",
        }:
            del env[name]
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    env["DJANGO_SECRET_KEY"] = secrets.token_urlsafe(64)
    checks = [
        ("Dependency compatibility", ["-m", "pip", "check"]),
        ("Ruff lint", ["-m", "ruff", "check", "."]),
        ("Ruff format", ["-m", "ruff", "format", "--check", "."]),
        ("Django system checks", ["manage.py", "check", "--fail-level", "WARNING"]),
        (
            "Production deployment checks (synthetic configuration)",
            [
                "manage.py",
                "check",
                "--deploy",
                "--fail-level",
                "WARNING",
                "--settings=config.settings.production_check",
            ],
        ),
        (
            "Migration consistency (no history connection)",
            [
                "manage.py",
                "makemigrations",
                "--check",
                "--dry-run",
            ],
        ),
        ("Tests and coverage", ["-m", "pytest"]),
        (
            "OpenAPI validation",
            [
                "manage.py",
                "spectacular",
                "--validate",
                "--fail-on-warn",
                "--file",
                "schema.yml",
            ],
        ),
        (
            "Bandit",
            [
                "-m",
                "bandit",
                "-r",
                "apps",
                "config",
                "core",
                "manage.py",
                "scripts",
                "-c",
                "pyproject.toml",
            ],
        ),
    ]
    for label, command in checks:
        run(label, command, env)
    if args.skip_dependency_audit:
        print(
            "SKIPPED: dependency audit explicitly requested; CI security audit remains mandatory."
        )
    else:
        # Both locks include platform-specific runtime packages (including Linux gunicorn).
        for lock in ("requirements.txt", "requirements-dev.txt", "requirements-linux.txt"):
            run(
                f"Dependency audit: {lock}",
                [
                    "-m",
                    "pip_audit",
                    "-r",
                    lock,
                    "--strict",
                    "--require-hashes",
                    "--disable-pip",
                    "--progress-spinner",
                    "off",
                ],
                env,
            )
    print("All requested checks passed.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(
            f"FAILED: command exited {exc.returncode}; remaining checks were not run.",
            file=sys.stderr,
        )
        sys.exit(exc.returncode)

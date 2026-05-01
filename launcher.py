# -*- coding: utf-8 -*-
"""Launcher fuer rinnsal -- Lightweight LLM Agent Infrastructure.

Funktioniert sowohl als normales Script als auch als PyInstaller-EXE.
Erstellt benoetigte Verzeichnisse und startet rinnsal.cli:main().
"""

import os
import sys

# --- Encoding sicherstellen (Windows cp1252 -> utf-8) ---
os.environ["PYTHONIOENCODING"] = "utf-8"

import io
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "").lower() != "utf-8":
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )


def get_base_dir():
    """Basis-Verzeichnis: neben der EXE (frozen) oder neben diesem Script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def ensure_directories():
    """Erstellt benoetigte Ordner falls fehlend."""
    base = get_base_dir()

    # chains/ neben dem Projekt
    chains_dir = os.path.join(base, "chains")
    os.makedirs(chains_dir, exist_ok=True)

    # ~/.rinnsal/ im Home-Verzeichnis
    home_dir = os.path.expanduser("~")
    rinnsal_home = os.path.join(home_dir, ".rinnsal")
    os.makedirs(rinnsal_home, exist_ok=True)

    return {"chains": chains_dir, "home": rinnsal_home}


def setup_sys_path():
    """Fuegt das Projekt-Verzeichnis zu sys.path hinzu."""
    base = get_base_dir()
    if base not in sys.path:
        sys.path.insert(0, base)


def main():
    """Einstiegspunkt."""
    dirs = ensure_directories()
    setup_sys_path()

    # Ohne Argumente: Hilfe anzeigen
    if len(sys.argv) < 2:
        print("rinnsal -- Lightweight LLM Agent Infrastructure")
        print(f"Basis:    {get_base_dir()}")
        print(f"Chains:   {dirs['chains']}")
        print(f"Home:     {dirs['home']}")
        print()
        print("Nutzung:  launcher.py <command> [optionen]")
        print("          launcher.py version")
        print("          launcher.py status")
        print("          launcher.py --help")
        print()
        # Trotzdem an CLI weiterleiten fuer --help
        sys.argv.append("--help")

    from rinnsal.cli import main as cli_main
    raise SystemExit(cli_main(sys.argv[1:]))


if __name__ == "__main__":
    main()

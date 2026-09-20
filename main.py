"""Ponto de entrada principal do Sidekick (Universal Gaming Buddy)."""

import sys
from src.app import SidekickCopilot, launch_gui_mode


def main():
    """Inicia o Sidekick com Interface Gráfica moderna por padrão (ou --cli para console)."""
    copilot = SidekickCopilot()
    use_cli = "--cli" in sys.argv or "-c" in sys.argv or "--console" in sys.argv

    if use_cli:
        copilot.start()
    else:
        launch_gui_mode(copilot)


if __name__ == "__main__":
    main()

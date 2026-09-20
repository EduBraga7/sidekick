"""Ponto de entrada dedicado para iniciar o Sidekick com Interface Gráfica moderna."""

import os
import sys

# Adiciona o diretório raiz ao PYTHONPATH se necessário
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_sidekick import SidekickCopilot, launch_gui_mode


def main():
    """Inicia a instância do Copilot com a GUI moderna."""
    print("🎮 Iniciando Sidekick com Interface Gráfica...")
    copilot = SidekickCopilot()
    launch_gui_mode(copilot)


if __name__ == "__main__":
    main()

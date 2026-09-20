"""Teste simples da GUI do Sidekick."""

import sys
import os

# Configura encoding UTF-8 para Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.main_window import SidekickGUI


def main():
    """Testa a GUI sem iniciar o Sidekick completo."""
    print("Testando GUI do Sidekick...")
    
    # Callbacks mock
    def mock_start():
        print("Mock: Start chamado")
    
    def mock_stop():
        print("Mock: Stop chamado")
    
    def mock_test():
        print("Mock: Test voice chamado")
    
    # Cria GUI
    gui = SidekickGUI(mock_start, mock_stop, mock_test)
    
    # Testa alguns métodos
    gui._log("GUI iniciada com sucesso!", 'success')
    gui._log("Status: Sistema pronto", 'info')
    gui._log("Modo Stealth: Inativo", 'warning')
    
    # Atualiza status
    gui._update_status("Estado", "Teste")
    gui._update_status("Jogo Detectado", "Dark Souls Remastered")
    
    print("GUI criada! Janela deve estar visível.")
    print("Feche a janela para encerrar o teste.")
    
    # Roda o loop
    gui.run()


if __name__ == "__main__":
    main()

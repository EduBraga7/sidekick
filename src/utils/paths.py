"""Utilitários de caminhos e diretórios para o Sidekick."""

import os
import sys


def get_base_dir() -> str:
    """
    Retorna o diretório base da aplicação de forma confiável.
    Compatível tanto com execução direta via Python quanto com binários PyInstaller (.exe).
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # 2 níveis acima de src/utils/paths.py -> raiz do projeto
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_config_path() -> str:
    """Retorna o caminho absoluto do arquivo config.json."""
    return os.path.join(get_base_dir(), "config.json")


def get_env_path() -> str:
    """Retorna o caminho absoluto do arquivo .env."""
    return os.path.join(get_base_dir(), ".env")


def get_wikis_dir() -> str:
    """Retorna o caminho absoluto da pasta de wikis táticas."""
    return os.path.join(get_base_dir(), "wikis")


def get_memory_path() -> str:
    """Retorna o caminho absoluto do arquivo de memória persistente."""
    return os.path.join(get_base_dir(), "sidekick_memory.json")

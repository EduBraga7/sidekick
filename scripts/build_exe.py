"""Script para construir o executável .exe do Sidekick com GUI."""

import os
import sys
import subprocess
import shutil

# Configura encoding UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)


def build_exe():
    """Constrói o executável usando PyInstaller."""
    
    print("=" * 60)
    print("CONSTRUINDO EXECUTAVEL DO SIDEKICK")
    print("=" * 60)
    
    # Verifica se PyInstaller está instalado
    try:
        import PyInstaller
        print(f"[OK] PyInstaller encontrado: {PyInstaller.__version__}")
    except ImportError:
        print("[ERRO] PyInstaller nao encontrado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller instalado")
    
    # Limpa builds anteriores
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"[LIMPEZA] Limpando {folder}...")
            shutil.rmtree(folder)
    
    # Comando PyInstaller (Windows usa ';' como separador no --add-data)
    sep = ";" if sys.platform.startswith("win") else ":"
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Sidekick",
        "--onefile",  # Executável único
        "--windowed",  # Sem console (já tem GUI)
        f"--add-data=src{sep}src",  # Inclui pasta src
        f"--add-data=config.json{sep}.",  # Inclui config (se existir)
        f"--add-data=.env.example{sep}.",  # Inclui .env.example
        f"--add-data=wikis{sep}wikis",  # Inclui pasta wikis
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
        "--hidden-import=sounddevice",
        "--hidden-import=PIL._tkinter_finder",
        "--collect-all=customtkinter",
    ]
    
    # Adiciona ícone se existir
    if os.path.exists("src/ui/gamepad_icon.ico"):
        pyinstaller_cmd.append("--icon=src/ui/gamepad_icon.ico")
    
    # Adiciona o script de entrada principal por último
    pyinstaller_cmd.append("main.py")
    
    print("\n[PYINSTALLER] Executando PyInstaller...")
    print("Comando:", " ".join(pyinstaller_cmd))
    
    try:
        subprocess.check_call(pyinstaller_cmd)
        print("\n[OK] Build concluido com sucesso!")
        dist_folder = "dist"
        exe_dist_path = os.path.join(dist_folder, "Sidekick.exe")
        print(f"[INFO] Executavel criado em: {exe_dist_path}")
        
        # Copia arquivos necessários para a pasta dist
        print("\n[COPIA] Copiando arquivos de configuracao...")
        
        # Copia config.json ativo para a pasta dist
        if os.path.exists("config.json"):
            shutil.copy("config.json", os.path.join(dist_folder, "config.json"))
            print("[OK] config.json ativo copiado para dist/")

        # Copia pasta de wikis para dist
        if os.path.exists("wikis"):
            dist_wikis = os.path.join(dist_folder, "wikis")
            if os.path.exists(dist_wikis):
                shutil.rmtree(dist_wikis)
            shutil.copytree("wikis", dist_wikis)
            print("[OK] Pasta wikis/ copiada para dist/")

        # Cria .env.example se não existir na dist
        if os.path.exists(".env.example"):
            shutil.copy(".env.example", os.path.join(dist_folder, ".env.example"))
            print("[OK] .env.example copiado")
        
        # Cria config.safe.example.json se não existir na dist
        if os.path.exists("config.safe.example.json"):
            shutil.copy("config.safe.example.json", os.path.join(dist_folder, "config.safe.example.json"))
            print("[OK] config.safe.example.json copiado")

        # O executável reside em dist/Sidekick.exe para manter o repositório limpo
        if os.path.exists(exe_dist_path):
            print(f"[OK] Executavel pronto em: {exe_dist_path}")
        
        # Cria README simplificado
        readme_content = """# Sidekick - Executavel

## Como Usar

1. Configure sua chave de API:
   - Copie `.env.example` para `.env`
   - Edite `.env` e adicione sua chave do Groq

2. Configure o sistema:
   - Copie `config.safe.example.json` para `config.json`
   - Edite conforme necessario

3. Execute o Sidekick:
   - De dois cliques em `Sidekick.exe`

## Arquivos Necessarios

- `.env` (crie a partir do .env.example)
- `config.json` (crie a partir do config.safe.example.json)
- `sidekick_memory.json` (criado automaticamente)

## Seguranca

AVISO: NUNCA compartilhe seus arquivos `.env` ou `config.json` com chaves reais!
"""
        with open(os.path.join(dist_folder, "README.txt"), "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("[OK] README.txt criado")
        
        print("\n" + "=" * 60)
        print("BUILD CONCLUIDO!")
        print("=" * 60)
        print(f"[INFO] Pasta de distribuicao: {os.path.abspath(dist_folder)}")
        print(f"[INFO] Executavel: {os.path.join(os.path.abspath(dist_folder), 'Sidekick.exe')}")
        print("\n[AVISO] IMPORTANTE:")
        print("   - O executavel deve estar na mesma pasta que .env e config.json")
        print("   - Distribua apenas o .exe + .env.example + config.safe.example.json")
        print("   - NUNCA distribua .env ou config.json com chaves reais!")
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERRO] Erro no build: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_exe()

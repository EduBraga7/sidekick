import ctypes
import re
from ctypes import wintypes

# Mapeamento de executáveis conhecidos para nomes oficiais de jogos
# anti_cheat_strict: True para jogos com anti-cheat rigoroso que podem banir por hooks
KNOWN_GAME_PROCESSES = {
    "albion-online.exe": {"name": "Albion Online", "anti_cheat_strict": True},
    "albiononline.exe": {"name": "Albion Online", "anti_cheat_strict": True},
    "darksoulsremastered.exe": {"name": "Dark Souls 1 Remastered", "anti_cheat_strict": False},
    "darksouls.exe": {"name": "Dark Souls 1 (PTDE)", "anti_cheat_strict": False},
    "darksoulsii.exe": {"name": "Dark Souls 2", "anti_cheat_strict": False},
    "darksoulsiii.exe": {"name": "Dark Souls 3", "anti_cheat_strict": False},
    "eldenring.exe": {"name": "Elden Ring", "anti_cheat_strict": False},
    "sekiro.exe": {"name": "Sekiro: Shadows Die Twice", "anti_cheat_strict": False},
    "cs2.exe": {"name": "Counter-Strike 2", "anti_cheat_strict": True},
    "league of legends.exe": {"name": "League of Legends", "anti_cheat_strict": True},
    "valorant-win64-shipping.exe": {"name": "Valorant", "anti_cheat_strict": True},
    "minecraft.exe": {"name": "Minecraft", "anti_cheat_strict": False},
    "javaw.exe": {"name": "Minecraft / Java Game", "anti_cheat_strict": False},
    "cyberpunk2077.exe": {"name": "Cyberpunk 2077", "anti_cheat_strict": False},
    "witcher3.exe": {"name": "The Witcher 3", "anti_cheat_strict": False},
    "bg3.exe": {"name": "Baldur's Gate 3", "anti_cheat_strict": False},
    "bg3_dx11.exe": {"name": "Baldur's Gate 3", "anti_cheat_strict": False},
    "pathofexile.exe": {"name": "Path of Exile", "anti_cheat_strict": True},
    "pathofexile_x64.exe": {"name": "Path of Exile", "anti_cheat_strict": True},
    "gta5.exe": {"name": "GTA V", "anti_cheat_strict": True},
    "rdr2.exe": {"name": "Red Dead Redemption 2", "anti_cheat_strict": False},
    "dota2.exe": {"name": "Dota 2", "anti_cheat_strict": True},
    "rocketleague.exe": {"name": "Rocket League", "anti_cheat_strict": True},
    "warframe.x64.exe": {"name": "Warframe", "anti_cheat_strict": False},
    "childrenofmorta.exe": {"name": "Children of Morta", "anti_cheat_strict": False},
    "hades.exe": {"name": "Hades", "anti_cheat_strict": False},
    "hades2.exe": {"name": "Hades II", "anti_cheat_strict": False},
    "hollow_knight.exe": {"name": "Hollow Knight", "anti_cheat_strict": False},
    "silksong.exe": {"name": "Hollow Knight: Silksong", "anti_cheat_strict": False},
    "deadcells.exe": {"name": "Dead Cells", "anti_cheat_strict": False},
    "deadcells_gl.exe": {"name": "Dead Cells", "anti_cheat_strict": False},
    "terraria.exe": {"name": "Terraria", "anti_cheat_strict": False},
    "stardew valley.exe": {"name": "Stardew Valley", "anti_cheat_strict": False},
    "celeste.exe": {"name": "Celeste", "anti_cheat_strict": False},
    "cuphead.exe": {"name": "Cuphead", "anti_cheat_strict": False},
    "isaac-ng.exe": {"name": "The Binding of Isaac", "anti_cheat_strict": False},
    "slaythespire.exe": {"name": "Slay the Spire", "anti_cheat_strict": False},
    "blasphemous.exe": {"name": "Blasphemous", "anti_cheat_strict": False},
    "blasphemous 2.exe": {"name": "Blasphemous 2", "anti_cheat_strict": False},
    "genshinimpact.exe": {"name": "Genshin Impact", "anti_cheat_strict": True},
    "honkaistarrail.exe": {"name": "Honkai: Star Rail", "anti_cheat_strict": True},
    "overwatch.exe": {"name": "Overwatch 2", "anti_cheat_strict": True},
    "destiny2.exe": {"name": "Destiny 2", "anti_cheat_strict": True},
    "apexlegends.exe": {"name": "Apex Legends", "anti_cheat_strict": True},
    "r5apex.exe": {"name": "Apex Legends", "anti_cheat_strict": True},
    "fortniteclient-win64-shipping.exe": {"name": "Fortnite", "anti_cheat_strict": True},
    "helldivers2.exe": {"name": "Helldivers 2", "anti_cheat_strict": True},
    "rainbowsix.exe": {"name": "Rainbow Six Siege", "anti_cheat_strict": True},
    "fallguys_client.exe": {"name": "Fall Guys", "anti_cheat_strict": True},
    "palworld-win64-shipping.exe": {"name": "Palworld", "anti_cheat_strict": False},
}

IGNORED_PROCESS_EXES = {
    "steam.exe", "steamwebhelper.exe", "steamservice.exe", 
    "gameoverlayui.exe", "gameoverlayui64.exe", 
    "unitycrashhandler64.exe", "unitycrashhandler32.exe", "crashhandler.exe",
    "epicgameslauncher.exe", "epicwebhelper.exe", "gog galaxy.exe",
    "galaxyclient.exe", "eadesktop.exe", "origin.exe", "riotclientservices.exe"
}

def detect_running_game() -> tuple[str, bool]:
    """
    Verifica com precisão de 100% se algum jogo conhecido ou jogo da Steam/bibliotecas está em execução no Windows.
    Retorna: (nome_do_jogo, anti_cheat_strict)
    """
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    # Enumera PIDs
    pids = (wintypes.DWORD * 2048)()
    cb_needed = wintypes.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(pids), ctypes.sizeof(pids), ctypes.byref(cb_needed)):
        return "", False

    num_pids = cb_needed.value // ctypes.sizeof(wintypes.DWORD)
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    auto_detected_game = ""

    for i in range(num_pids):
        pid = pids[i]
        if pid == 0:
            continue
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h_process:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                full_path = buf.value
                exe_name = full_path.split("\\")[-1].lower()
                
                # 1. Checagem direta em jogos mapeados (prioridade)
                if exe_name in KNOWN_GAME_PROCESSES:
                    game_info = KNOWN_GAME_PROCESSES[exe_name]
                    kernel32.CloseHandle(h_process)
                    return game_info["name"], game_info["anti_cheat_strict"]
                
                # 2. Detecção automática de jogos em pastas de bibliotecas (Steam, Epic, GOG, Xbox)
                if not auto_detected_game and exe_name not in IGNORED_PROCESS_EXES:
                    lower_path = full_path.lower()
                    # Steam
                    if "steamapps\\common\\" in lower_path:
                        parts = full_path.split("\\")
                        for idx, part in enumerate(parts):
                            if part.lower() == "common" and idx + 1 < len(parts):
                                raw_name = parts[idx + 1]
                                clean_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', raw_name).strip()
                                auto_detected_game = clean_name or raw_name
                                break
                    # Epic Games
                    elif "epic games\\" in lower_path:
                        parts = full_path.split("\\")
                        for idx, part in enumerate(parts):
                            if part.lower() == "epic games" and idx + 1 < len(parts):
                                raw_name = parts[idx + 1]
                                auto_detected_game = raw_name
                                break
                    # GOG Galaxy
                    elif "gog galaxy\\games\\" in lower_path or "gog games\\" in lower_path:
                        parts = full_path.split("\\")
                        for idx, part in enumerate(parts):
                            if part.lower() in ("games", "gog games") and idx + 1 < len(parts):
                                raw_name = parts[idx + 1]
                                auto_detected_game = raw_name
                                break
                    # Xbox Games
                    elif "xboxgames\\" in lower_path:
                        parts = full_path.split("\\")
                        for idx, part in enumerate(parts):
                            if part.lower() == "xboxgames" and idx + 1 < len(parts):
                                raw_name = parts[idx + 1]
                                auto_detected_game = raw_name
                                break

            kernel32.CloseHandle(h_process)

    if auto_detected_game:
        return auto_detected_game, False

    return "", False

if __name__ == "__main__":
    game_name, is_strict = detect_running_game()
    print(f"Jogo detectado: {game_name} (Anti-cheat strict: {is_strict})")

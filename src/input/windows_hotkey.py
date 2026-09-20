"""Input via Windows API Hotkey - Alternativa mais segura ao pynput para evitar detecção de anti-cheat.

Usa RegisterHotKey do Windows que é menos suspeito que hooks globais de teclado/mouse.
Limitação: Apenas uma tecla de atalho por vez (sem modificadores complexos).
"""

import ctypes
import threading
import time
from ctypes import wintypes

# Constantes do Windows
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# Mapeamento de nomes de teclas para códigos virtuais do Windows
KEY_MAP = {
    "caps_lock": 0x14,
    "scroll_lock": 0x91,
    "num_lock": 0x90,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    # Teclas alfanuméricas
    **{chr(i): 0x30 + (i - 48) for i in range(48, 58)},  # 0-9
    **{chr(i): 0x41 + (i - 65) for i in range(65, 91)},  # A-Z
}


class WindowsHotkeyListener:
    """Listener de hotkey usando Windows API (mais seguro que pynput)."""
    
    def __init__(self, key_name: str, on_press=None, on_release=None):
        """
        Args:
            key_name: Nome da tecla (ex: "caps_lock", "f1", "a")
            on_press: Callback quando tecla é pressionada
            on_release: Callback quando tecla é solta
        """
        self.key_name = key_name.lower()
        self.on_press = on_press
        self.on_release = on_release
        self._running = False
        self._thread = None
        self._hwnd = None
        self._is_pressed = False
        
        # Obtém código virtual da tecla
        self.vk_code = KEY_MAP.get(self.key_name)
        if not self.vk_code:
            raise ValueError(f"Tecla '{key_name}' não suportada. Use: caps_lock, f1-f12, 0-9, a-z")
        
        # Configurações da janela invisível para receber mensagens
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
    def _message_loop(self):
        """Loop de mensagens do Windows para receber hotkeys."""
        # Cria classe de janela
        wnd_class = wintypes.WNDCLASS()
        wnd_class.lpfnWndProc = self._wnd_proc
        wnd_class.lpszClassName = "SidekickHotkeyClass"
        
        # Registra classe
        class_atom = self.user32.RegisterClassW(ctypes.byref(wnd_class))
        if not class_atom:
            print("[Hotkey]: Erro ao registrar classe de janela")
            return
        
        # Cria janela invisível
        self._hwnd = self.user32.CreateWindowExW(
            0, class_atom, "SidekickHotkey",
            0, 0, 0, 0, 0,
            None, None, None, None
        )
        
        if not self._hwnd:
            print("[Hotkey]: Erro ao criar janela")
            return
        
        # Registra hotkey (ID=1, sem modificadores)
        if not self.user32.RegisterHotKey(self._hwnd, 1, 0, self.vk_code):
            print(f"[Hotkey]: Erro ao registrar hotkey para {self.key_name}")
            self.user32.DestroyWindow(self._hwnd)
            return
        
        print(f"[Hotkey]: Hotkey '{self.key_name}' registrado com sucesso via Windows API")
        
        # Loop de mensagens
        msg = wintypes.MSG()
        while self._running:
            ret = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            
            if msg.message == WM_HOTKEY:
                # Hotkey ativado
                if not self._is_pressed:
                    self._is_pressed = True
                    if self.on_press:
                        self.on_press()
                else:
                    self._is_pressed = False
                    if self.on_release:
                        self.on_release()
            
            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageW(ctypes.byref(msg))
        
        # Cleanup
        self.user32.UnregisterHotKey(self._hwnd, 1)
        self.user32.DestroyWindow(self._hwnd)
        self.user32.UnregisterClassW("SidekickHotkeyClass", None)
    
    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        """Window procedure callback."""
        return self.user32.DefWindowProcW(hwnd, msg, wparam, lparam)
    
    def start(self):
        """Inicia o listener de hotkey."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Para o listener de hotkey."""
        self._running = False
        if self._hwnd:
            # Envia mensagem de quit para o loop
            self.user32.PostQuitMessage(0)
        
        if self._thread:
            self._thread.join(timeout=2)


def is_hotkey_supported(key_name: str) -> bool:
    """Verifica se uma tecla é suportada pelo hotkey do Windows."""
    return key_name.lower() in KEY_MAP


def get_supported_keys() -> list:
    """Retorna lista de teclas suportadas."""
    return list(KEY_MAP.keys())

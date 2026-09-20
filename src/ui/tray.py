"""Ícone e menu na bandeja do sistema (System Tray) para o Sidekick."""

import os
import threading
from PIL import Image, ImageDraw
import pystray


def create_gamepad_icon(size=64, stealth_mode=False):
    """Gera o ícone de controle gamer moderno programaticamente com Pillow.
    
    Args:
        size: Tamanho do ícone em pixels
        stealth_mode: Se True, usa cores de alerta (laranja/vermelho) para indicar modo stealth
    """
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Cores baseadas no modo
    if stealth_mode:
        # Cores de alerta para modo stealth
        outline_color = (255, 100, 0, 255)  # Laranja
        neon_color = (255, 140, 0, 255)  # Laranja mais claro
        fill_color = (45, 25, 15, 255)  # Marrom escuro
    else:
        # Cores normais (ciano/neon)
        outline_color = (0, 230, 200, 255)
        neon_color = (0, 230, 200, 255)
        fill_color = (35, 38, 48, 255)

    # Corpo do controle gamer (estilo moderno arredondado)
    margin_x = int(size * 0.12)
    margin_y = int(size * 0.22)
    bottom_y = int(size * 0.78)

    # Base do controle
    draw.rounded_rectangle(
        [margin_x, margin_y, size - margin_x, bottom_y],
        radius=14,
        fill=fill_color,
        outline=outline_color,
        width=2
    )

    # D-Pad na esquerda (cruz)
    dpad_cx = int(size * 0.32)
    dpad_cy = int(size * 0.50)
    dpad_w = 4
    dpad_l = 8
    draw.rectangle([dpad_cx - dpad_w, dpad_cy - dpad_l, dpad_cx + dpad_w, dpad_cy + dpad_l], fill=neon_color)
    draw.rectangle([dpad_cx - dpad_l, dpad_cy - dpad_w, dpad_cx + dpad_l, dpad_cy + dpad_w], fill=neon_color)

    # Botões de Ação na direita (estilo ABXY)
    btn_cx = int(size * 0.68)
    btn_cy = int(size * 0.50)
    btn_r = 3
    # Topo (Y)
    draw.ellipse([btn_cx - btn_r, btn_cy - 7 - btn_r, btn_cx + btn_r, btn_cy - 7 + btn_r], fill=(255, 204, 0, 255))
    # Direita (B)
    draw.ellipse([btn_cx + 7 - btn_r, btn_cy - btn_r, btn_cx + 7 + btn_r, btn_cy + btn_r], fill=(255, 68, 68, 255))
    # Baixo (A)
    draw.ellipse([btn_cx - btn_r, btn_cy + 7 - btn_r, btn_cx + btn_r, btn_cy + 7 + btn_r], fill=(51, 204, 51, 255))
    # Esquerda (X)
    draw.ellipse([btn_cx - 7 - btn_r, btn_cy - btn_r, btn_cx - 7 + btn_r, btn_cy + btn_r], fill=(51, 153, 255, 255))

    # Adiciona indicador de stealth (triângulo de alerta no centro)
    if stealth_mode:
        tri_cx = int(size * 0.50)
        tri_cy = int(size * 0.65)
        tri_size = 6
        draw.polygon([
            (tri_cx, tri_cy - tri_size),
            (tri_cx - tri_size, tri_cy + tri_size),
            (tri_cx + tri_size, tri_cy + tri_size)
        ], fill=(255, 0, 0, 255))

    return image


class TrayApp:
    def __init__(self, key_name: str, on_test_voice=None, on_toggle_sentinel=None, sentinel_enabled=True, on_quit=None):
        self.key_name = key_name
        self.on_test_voice = on_test_voice
        self.on_toggle_sentinel = on_toggle_sentinel
        self.sentinel_enabled = sentinel_enabled
        self.on_quit = on_quit
        self._icon = None
        self._thread = None
        self.stealth_mode = False

    def _open_folder(self):
        try:
            cwd = os.path.abspath(os.getcwd())
            os.startfile(cwd)
        except Exception as e:
            print(f"[Tray]: Erro ao abrir pasta: {e}")

    def _handle_test(self, icon, item):
        if self.on_test_voice:
            threading.Thread(target=self.on_test_voice, daemon=True).start()

    def _handle_toggle_sentinel(self, icon, item):
        if self.on_toggle_sentinel:
            self.sentinel_enabled = self.on_toggle_sentinel()
            if self._icon:
                self._icon.update_menu()

    def set_stealth_mode(self, enabled: bool):
        """Atualiza o ícone para indicar modo stealth ativo/inativo."""
        self.stealth_mode = enabled
        if self._icon:
            self._icon.icon = create_gamepad_icon(stealth_mode=self.stealth_mode)

    def _handle_open_folder(self, icon, item):
        self._open_folder()

    def _handle_quit(self, icon, item):
        if self.on_quit:
            self.on_quit()
        if self._icon:
            self._icon.stop()

    def run(self):
        """Inicia o ícone do System Tray."""
        menu = pystray.Menu(
            pystray.MenuItem("🎮 Sidekick — Gaming Buddy", None, enabled=False),
            pystray.MenuItem(f"Atalho Push-to-Talk: [{self.key_name.upper()}]", None, enabled=False),
            pystray.MenuItem(
                lambda item: f"Modo Stealth: {'[ATIVO]' if self.stealth_mode else '[INATIVO]'}",
                None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda item: f"Modo Sentinela: {'[LIGADO]' if self.sentinel_enabled else '[DESLIGADO]'}",
                self._handle_toggle_sentinel
            ),
            pystray.MenuItem("Testar Voz da Sidekick", self._handle_test),
            pystray.MenuItem("Abrir Pasta do Projeto / Config", self._handle_open_folder),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", self._handle_quit)
        )

        self._icon = pystray.Icon(
            name="SidekickCopilot",
            icon=create_gamepad_icon(stealth_mode=self.stealth_mode),
            title="Sidekick — Seu Copiloto Gamer",
            menu=menu
        )

        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._icon:
            self._icon.stop()

"""Overlay Flutuante dentro do Jogo (In-Game HUD) transparente e click-through."""

import ctypes
import os
import queue
import sys
import threading
import time
from typing import Optional
import tkinter as tk


class GameOverlay:
    """Overlay transparente, topmost e click-through para exibir legendas e status dentro de qualquer jogo."""

    def __init__(self, enabled: bool = True, position: str = "top_right"):
        self.enabled = enabled
        self.position = position
        self._q = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._hide_timer_id = None

        if self.enabled:
            self._start_thread()

    def _start_thread(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_gui, daemon=True)
        self._thread.start()

    def _run_gui(self):
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            self.root.attributes('-topmost', True)
            self.root.attributes('-alpha', 0.0)  # Inicia invisível
            self.root.configure(bg='#0b0e17')

            # Container com borda moderna
            self.frame = tk.Frame(
                self.root,
                bg='#121624',
                highlightbackground='#2563eb',
                highlightthickness=1,
                padx=16,
                pady=12
            )
            self.frame.pack(fill='both', expand=True)

            # Cabeçalho do Overlay
            self.title_lbl = tk.Label(
                self.frame,
                text="🎮 SIDEKICK",
                font=('Segoe UI', 10, 'bold'),
                fg='#38bdf8',
                bg='#121624'
            )
            self.title_lbl.pack(anchor='w')

            # Texto Principal / Legenda
            self.text_lbl = tk.Label(
                self.frame,
                text="",
                font=('Segoe UI', 11),
                fg='#f8fafc',
                bg='#121624',
                wraplength=400,
                justify='left'
            )
            self.text_lbl.pack(anchor='w', pady=(4, 0))

            # Torna a janela click-through via Win32 API (cliques passam direto para o jogo)
            self.root.update_idletasks()
            self._apply_click_through()
            self._reposition()

            self._poll_queue()
            self.root.mainloop()
        except Exception as e:
            print(f"[Overlay]: Erro na thread gráfica: {e}")

    def _apply_click_through(self):
        """Aplica estilos do Windows para garantir que o mouse atravesse o overlay."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # GWL_EXSTYLE = -20
            # WS_EX_LAYERED = 0x80000 | WS_EX_TRANSPARENT = 0x20 | WS_EX_TOOLWINDOW = 0x80
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            style = style | 0x80000 | 0x20 | 0x80
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        except Exception as e:
            print(f"[Overlay]: Aviso ao aplicar click-through: {e}")

    def _reposition(self):
        """Calcula e posiciona a janela na tela."""
        try:
            self.root.update_idletasks()
            w = self.root.winfo_reqwidth()
            h = self.root.winfo_reqheight()

            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()

            if self.position == "bottom_center":
                x = (screen_w - w) // 2
                y = screen_h - h - 70
            else:  # top_right
                x = screen_w - w - 25
                y = 25

            self.root.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _poll_queue(self):
        """Processa mensagens enviadas das outras threads para a thread do Tkinter."""
        try:
            while not self._q.empty():
                cmd, data = self._q.get_nowait()
                if cmd == "show":
                    self._handle_show(data)
                elif cmd == "hide":
                    self._handle_hide()
                elif cmd == "stop":
                    self.root.destroy()
                    return
        except Exception:
            pass

        if hasattr(self, 'root') and self.root:
            self.root.after(80, self._poll_queue)

    def _handle_show(self, data):
        """Renderiza mensagem e torna visível."""
        title = data.get("title", "🎮 SIDEKICK")
        text = data.get("text", "")
        duration = data.get("duration", 5.0)
        is_alert = data.get("is_alert", False)

        # Cores de alerta vs padrão
        border_col = '#ef4444' if is_alert else '#38bdf8'
        title_col = '#f87171' if is_alert else '#38bdf8'

        self.frame.configure(highlightbackground=border_col)
        self.title_lbl.configure(text=title, fg=title_col)
        self.text_lbl.configure(text=text)

        self._reposition()
        self.root.attributes('-alpha', 0.90)  # Torna translúcido visível

        # Cancela timer anterior se houver
        if self._hide_timer_id:
            self.root.after_cancel(self._hide_timer_id)

        if duration > 0:
            self._hide_timer_id = self.root.after(int(duration * 1000), self._handle_hide)

    def _handle_hide(self):
        """Oculta o overlay com fade out suave."""
        try:
            self.root.attributes('-alpha', 0.0)
        except Exception:
            pass

    # --- Métodos Públicos Thread-Safe ---

    def show_listening(self):
        """Exibe feedback de escuta enquanto você fala."""
        if not self.enabled:
            return
        self._q.put(("show", {
            "title": "🎙️ OUVINDO...",
            "text": "Fale sua dúvida ou comando enquanto segura a tecla.",
            "duration": 8.0,
            "is_alert": False
        }))

    def show_thinking(self, game_name: str = ""):
        """Exibe feedback enquanto a IA raciocina."""
        if not self.enabled:
            return
        tag = f" — {game_name}" if game_name else ""
        self._q.put(("show", {
            "title": f"🧠 ANALISANDO{tag}...",
            "text": "Consultando visão da tela e guia tático do jogo.",
            "duration": 6.0,
            "is_alert": False
        }))

    def show_message(self, text: str, title: str = "🎮 SIDEKICK", duration: float = 5.5, is_alert: bool = False):
        """Exibe legenda ou alerta falado pelo Sidekick."""
        if not self.enabled:
            return
        self._q.put(("show", {
            "title": title,
            "text": text,
            "duration": duration,
            "is_alert": is_alert
        }))

    def hide(self):
        """Oculta imediatamente."""
        if not self.enabled:
            return
        self._q.put(("hide", None))

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if not enabled:
            self.hide()
        elif not self._running:
            self._start_thread()

    def set_position(self, position: str):
        self.position = position

    def stop(self):
        """Encerra a thread do overlay."""
        if self._running:
            self._running = False
            self._q.put(("stop", None))

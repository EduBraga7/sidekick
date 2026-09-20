"""Módulo de reprodução de voz de alto desempenho e interrupção instantânea."""

import ctypes
import os
import threading
import time


class AudioPlayer:
    def __init__(self):
        self._mci = ctypes.windll.winmm.mciSendStringW
        self._is_playing = False
        self._lock = threading.Lock()
        self._alias_counter = 0

    def stop(self):
        """Interrompe qualquer fala em andamento imediatamente."""
        with self._lock:
            if self._is_playing:
                try:
                    self._mci("stop sidekick_voice", None, 0, 0)
                    self._mci("close sidekick_voice", None, 0, 0)
                except Exception:
                    pass
                self._is_playing = False

    def play_file(self, filepath: str, block: bool = False):
        """Reproduz um arquivo de áudio (MP3 ou WAV) de forma assíncrona ou síncrona."""
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            return

        self.stop()

        def _worker():
            with self._lock:
                self._is_playing = True
                # Abrir com alias único
                self._mci(f'open "{abs_path}" type mpegvideo alias sidekick_voice', None, 0, 0)
                self._mci("play sidekick_voice wait", None, 0, 0)
                self._mci("close sidekick_voice", None, 0, 0)
                self._is_playing = False

        if block:
            _worker()
        else:
            t = threading.Thread(target=_worker, daemon=True)
            t.start()

    @property
    def is_playing(self):
        return self._is_playing

"""Gerador e reprodutor de bipes sutis para feedback auditivo em tempo real."""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100


def _generate_tone(freqs, duration_ms=100, volume=0.15):
    """Gera um sinal estéreo/mono suave com envelope anti-clique (fade in / fade out)."""
    samples = int(SAMPLE_RATE * (duration_ms / 1000.0))
    t = np.linspace(0, duration_ms / 1000.0, samples, False)

    signal = np.zeros(samples)
    for freq in freqs:
        signal += np.sin(2 * np.pi * freq * t)
    signal /= len(freqs)

    # Envelope Hann / Fade para evitar estalos (clicks)
    fade_len = min(int(samples * 0.2), 200)
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)

    signal[:fade_len] *= fade_in
    signal[-fade_len:] *= fade_out

    return (signal * volume).astype(np.float32)


class ChimePlayer:
    def __init__(self, volume=0.15, enabled=True):
        self.volume = volume
        self.enabled = enabled
        self._start_chime = _generate_tone([523.25, 659.25], duration_ms=90, volume=self.volume)   # Dó + Mi (agradável)
        self._done_chime = _generate_tone([659.25, 523.25], duration_ms=90, volume=self.volume)    # Mi + Dó
        self._error_chime = _generate_tone([350.0, 260.0], duration_ms=150, volume=self.volume)    # Tom baixo

    def play_start(self):
        """Tocado quando o jogador pressiona o atalho para falar."""
        if self.enabled:
            try:
                sd.play(self._start_chime, SAMPLE_RATE)
            except Exception:
                pass

    def play_done(self):
        """Tocado quando o jogador solta o atalho e o áudio é enviado para a IA."""
        if self.enabled:
            try:
                sd.play(self._done_chime, SAMPLE_RATE)
            except Exception:
                pass

    def play_error(self):
        """Tocado se houver erro de conexão ou configuração."""
        if self.enabled:
            try:
                sd.play(self._error_chime, SAMPLE_RATE)
            except Exception:
                pass

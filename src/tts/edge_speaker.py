"""Módulo de síntese de voz neural em português brasileiro usando Edge-TTS."""

import asyncio
import os
import re
import tempfile
import edge_tts
from src.audio.player import AudioPlayer

DEFAULT_VOICE = "pt-BR-ThalitaMultilingualNeural"


def clean_text_for_speech(text: str) -> str:
    """Remove caracteres especiais de markdown, emojis e formatações para leitura natural."""
    # Normaliza hífens, aspas e espaços especiais do unicode
    text = text.replace("\u202f", " ").replace("\u00a0", " ")
    text = text.replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    # Remove marcações em negrito/itálico (*, _)
    cleaned = re.sub(r"[\*_~`#]", "", text)
    # Remove referências de links [texto](url)
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove múltiplos espaços ou quebras de linha excessivas
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class EdgeSpeaker:
    def __init__(self, voice=DEFAULT_VOICE, rate="+5%", pitch="+0Hz", player=None):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.player = player or AudioPlayer()
        self._temp_dir = tempfile.mkdtemp(prefix="sidekick_tts_")

    def _cleanup_old_temp_files(self, max_files: int = 5):
        """Remove arquivos de áudio temporários antigos para não consumir espaço em disco."""
        try:
            files = [
                os.path.join(self._temp_dir, f)
                for f in os.listdir(self._temp_dir)
                if f.endswith(".mp3")
            ]
            if len(files) > max_files:
                # Ordena por data de modificação e remove os mais antigos
                files.sort(key=os.path.getmtime)
                for old_file in files[:-max_files]:
                    try:
                        os.remove(old_file)
                    except OSError:
                        pass
        except Exception:
            pass

    async def _synthesize(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(
            text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch
        )
        await communicate.save(output_path)

    def speak(self, text: str, block: bool = False):
        """Sintetiza e reproduz a fala do Sidekick."""
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return

        self._cleanup_old_temp_files()
        temp_audio_file = os.path.join(self._temp_dir, f"speech_{os.getpid()}_{hash(clean_text) & 0xFFFFFF}.mp3")

        try:
            asyncio.run(self._synthesize(clean_text, temp_audio_file))
            self.player.play_file(temp_audio_file, block=block)
        except Exception as e:
            print(f"[EdgeSpeaker Error]: {e}")

    def stop(self):
        """Interrompe a fala atual."""
        self.player.stop()

    def cleanup(self):
        """Remove a pasta temporária na finalização do serviço."""
        try:
            import shutil
            if os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass

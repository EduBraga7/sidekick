"""Módulo de detecção de palavra de ativação (Wake Word — "Ei Sidekick") em segundo plano."""

import io
import re
import threading
import time
import wave
from typing import Callable, Optional
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024  # ~64ms por bloco a 16kHz

WAKE_PATTERNS = [
    r"\bei sidekick\b",
    r"\boi sidekick\b",
    r"\bhey sidekick\b",
    r"\bolá sidekick\b",
    r"\bola sidekick\b",
    r"\bok sidekick\b",
    r"\bsidekick\b",
    r"\bei saidkick\b",
    r"\bhey saidkick\b",
    r"\bsaidkick\b",
    r"\bei side kick\b",
]

SENSITIVITY_MAP = {
    "alta": 1.6,   # Dispara com som mais baixo (ideal para microfone distante)
    "media": 2.4,  # Padrão balanceado
    "baixa": 3.4   # Exige fala mais alta e clara (ideal para teclados mecânicos barulhentos)
}


class WakeWordDetector:
    """Monitor de microfone de baixo consumo de CPU com detecção VAD e Wake Word."""

    def __init__(
        self,
        transcriber,
        on_wake_detected: Optional[Callable[[str, str], None]] = None,
        enabled: bool = False,
        sensitivity: str = "media"
    ):
        self.transcriber = transcriber
        self.on_wake_detected = on_wake_detected
        self.enabled = enabled
        self.sensitivity = sensitivity
        self.sample_rate = SAMPLE_RATE

        self._running = False
        self._stream = None
        self._thread = None
        self._lock = threading.Lock()

        # VAD & Calibração
        self._noise_floor = 300.0  # RMS padrão inicial
        self._threshold = 800.0
        self._update_threshold()

        self._is_speaking = False
        self._speech_frames = []
        self._silence_start_time = 0.0
        self._speech_start_time = 0.0
        self._min_speech_duration = 0.6   # Mínimo de 600ms de fala
        self._max_speech_duration = 10.0  # Máximo de 10s por comando
        self._silence_cutoff = 0.65       # 650ms de silêncio encerra a fala
        self._is_paused = False           # Pausa quando o Sidekick estiver falando para não ouvir a si mesmo
        self._follow_up_until = 0.0       # Janela aberta quando usuário diz só 'Ei Sidekick'

    def _update_threshold(self):
        mult = SENSITIVITY_MAP.get(self.sensitivity.lower(), 2.4)
        self._threshold = max(450.0, self._noise_floor * mult)

    def set_sensitivity(self, sensitivity: str):
        self.sensitivity = sensitivity
        self._update_threshold()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        if enabled and not self._running:
            self.start()
        elif not enabled and self._running:
            self.stop()

    def pause_listening(self):
        """Pausa temporariamente a detecção (ex: enquanto a IA fala pelo alto-falante)."""
        self._is_paused = True

    def resume_listening(self):
        """Retoma a detecção após a resposta ser concluída."""
        self._is_paused = False
        self._speech_frames = []
        self._is_speaking = False

    def enable_follow_up_mode(self, duration: float = 7.0):
        """Abre janela de escuta direta (sem precisar repetir a palavra de ativação)."""
        self._follow_up_until = time.time() + duration

    def start(self):
        """Inicia o loop contínuo de monitoramento de microfone."""
        if self._running or not self.enabled:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_detector, daemon=True)
        self._thread.start()

    def stop(self):
        """Interrompe o monitoramento."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Processamento em tempo real dos blocos de áudio."""
        if not self._running or self._is_paused:
            return

        # Calcula energia RMS do bloco
        audio_chunk = indata[:, 0].astype(np.float32)
        rms = float(np.sqrt(np.mean(audio_chunk ** 2)))
        now = time.time()

        # Atualização lenta do piso de ruído quando em silêncio absoluto
        if not self._is_speaking and rms < self._threshold * 0.7:
            self._noise_floor = (self._noise_floor * 0.95) + (rms * 0.05)
            self._update_threshold()

        # Fala detectada
        if rms >= self._threshold:
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_start_time = now
                self._speech_frames = [indata.copy()]
            else:
                self._speech_frames.append(indata.copy())
            self._silence_start_time = 0.0

            # Limite máximo de fala
            if now - self._speech_start_time > self._max_speech_duration:
                self._finalize_speech_segment()
        else:
            # Silêncio momentâneo
            if self._is_speaking:
                self._speech_frames.append(indata.copy())
                if self._silence_start_time == 0.0:
                    self._silence_start_time = now
                elif (now - self._silence_start_time) >= self._silence_cutoff:
                    self._finalize_speech_segment()

    def _finalize_speech_segment(self):
        """Segmento de fala concluído: empacota e envia para transcrição e verificação."""
        self._is_speaking = False
        self._silence_start_time = 0.0
        frames_to_eval = list(self._speech_frames)
        self._speech_frames = []

        if not frames_to_eval:
            return

        audio_arr = np.concatenate(frames_to_eval, axis=0)
        duration = len(audio_arr) / self.sample_rate

        # Descarta ruídos muito curtos
        if duration < self._min_speech_duration:
            return

        # Processa transcrição e gatilho em thread separada para não travar o stream
        threading.Thread(
            target=self._process_candidate_audio,
            args=(audio_arr,),
            daemon=True
        ).start()

    def _process_candidate_audio(self, audio_data: np.ndarray):
        """Transcreve o áudio e verifica se contém a palavra de ativação."""
        try:
            # Converte para buffer WAV
            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)  # int16
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            buffer.seek(0)

            if not self.transcriber:
                return

            text = self.transcriber.transcribe(buffer)
            if not text:
                return

            clean_text = text.strip()
            lower_text = clean_text.lower()
            now = time.time()

            # Caso 1: Janela de follow-up ativa (usuário acabou de chamar 'Ei Sidekick')
            if now < self._follow_up_until:
                self._follow_up_until = 0.0
                print(f"\n🎙️ [Mãos Livres - Pergunta]: \"{clean_text}\"")
                if self.on_wake_detected:
                    self.on_wake_detected(clean_text, clean_text)
                return

            # Caso 2: Procura gatilho de wake word no início/corpo da fala
            matched, command_text = self._extract_wake_command(lower_text, clean_text)
            if matched:
                print(f"\n🎙️ [Wake Word Detectada]: \"{clean_text}\"")
                if self.on_wake_detected:
                    self.on_wake_detected(command_text, clean_text)

        except Exception as e:
            print(f"[WakeWord Error]: {e}")

    @staticmethod
    def _extract_wake_command(lower_text: str, original_text: str) -> tuple[bool, str]:
        """Verifica se há gatilho de wake word e extrai o comando restante se houver."""
        for pattern in WAKE_PATTERNS:
            match = re.search(pattern, lower_text)
            if match:
                # Remove o gatilho e pontuações iniciais
                end_pos = match.end()
                command = original_text[end_pos:].strip()
                command = re.sub(r"^[,.:;?! \-]+", "", command).strip()
                return True, command

        return False, ""

    def _run_detector(self):
        """Loop da thread que mantém o stream de áudio ativo."""
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype="int16",
                blocksize=BLOCK_SIZE,
                callback=self._audio_callback
            ) as stream:
                self._stream = stream
                while self._running and self.enabled:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[WakeWord Stream Error]: {e}")
        finally:
            self._running = False

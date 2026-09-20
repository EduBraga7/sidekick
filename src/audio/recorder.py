"""Módulo de gravação de microfone para Push-to-Talk."""

import io
import threading
import wave
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1


class AudioRecorder:
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.is_recording = False
        self._frames = []
        self._lock = threading.Lock()
        self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback chamado pelo sounddevice em background para cada bloco gravado."""
        if self.is_recording:
            with self._lock:
                self._frames.append(indata.copy())

    def start_recording(self):
        """Inicia a gravação do microfone."""
        with self._lock:
            self._frames = []
            self.is_recording = True

        if self._stream is None:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype="int16",
                callback=self._audio_callback
            )
            self._stream.start()

    def stop_recording(self):
        """Finaliza a gravação e retorna os dados de áudio em formato WAV (bytes)."""
        with self._lock:
            self.is_recording = False
            frames_to_process = list(self._frames)
            self._frames = []

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if not frames_to_process:
            return None

        audio_data = np.concatenate(frames_to_process, axis=0)

        # Se for menor que 0.35s (ex: clique acidental na tecla), ignorar
        duration = len(audio_data) / self.sample_rate
        if duration < 0.35:
            return None

        # Salvar para buffer WAV em memória
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit (int16)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        buffer.seek(0)
        return buffer

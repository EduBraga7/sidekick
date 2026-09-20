"""Módulo de transcrição de voz (Speech-to-Text)."""

import io
from typing import Optional


class WhisperTranscriber:
    def __init__(self, groq_client=None, gemini_client=None):
        self.groq_client = groq_client
        self.gemini_client = gemini_client

    def transcribe(self, audio_wav_buffer: io.BytesIO) -> Optional[str]:
        """Transcreve os bytes de áudio WAV para texto em português."""
        if audio_wav_buffer is None:
            return None

        audio_bytes = audio_wav_buffer.getvalue()
        if len(audio_bytes) < 1000:
            return None

        # Tentativa 1: Groq Whisper (ultrarrápido, ~200ms)
        if self.groq_client:
            try:
                audio_file = ("speech.wav", audio_bytes, "audio/wav")
                transcription = self.groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    language="pt",
                    response_format="json"
                )
                text = transcription.text.strip()
                if text:
                    return text
            except Exception as e:
                print(f"[Whisper Groq Error]: {e}")

        # Tentativa 2: Gemini via google-genai
        if self.gemini_client:
            try:
                # Gemini pode transcrever passando o arquivo de áudio diretamente
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        "Transcreva exatamente o que foi dito neste áudio em português brasileiro. Retorne apenas o texto transcrito, sem aspas e sem explicações.",
                        {"mime_type": "audio/wav", "data": audio_bytes}
                    ]
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[Whisper Gemini Error]: {e}")

        # Se nenhuma chave configurada, aviso no console
        print("[Aviso]: Nenhuma chave de API (Groq ou Gemini) configurada para transcrição.")
        return None

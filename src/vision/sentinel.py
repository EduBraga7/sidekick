"""Modo Sentinela: Monitoramento autônomo periódico da tela com filtro de silêncio estrito."""

import time
import threading
from typing import Optional
from src.vision.screengrab import capture_screen_base64
from src.vision.game_detector import detect_running_game

SENTINEL_PROMPT = """Você é a Sentinela do Sidekick. Você está vigiando a tela do jogo em segundo plano.

REGRA ABSOLUTA: SILÊNCIO POR PADRÃO.
Se a situação for normal (jogador andando, explorando, farmando, ou em luta controlada), responda EXATAMENTE:
SILENCE

SÓ FALE SE DETECTAR UM DESSES 4 EVENTOS CRÍTICOS:
1. VIDA CRÍTICA: A barra de HP do jogador está no vermelho/abaixo de 25% em perigo.
2. MORTE: Tela de "YOU DIED", "Você Morreu" ou derrota evidente.
3. EMBOSCADA: Inimigo perigoso vindo diretamente pelas costas ou escondido no teto/canto.
4. ITEM RARO OU BAÚ OCULTO: Um baú ou loot raro visível que o jogador pode não ter notado.

REGRAS DE FALA:
- Se for falar, fale em APENAS UMA ÚNICA FRASE CURTA e direta (máximo 15 palavras).
- Sem asteriscos, sem markdown, sem emojis (será lido no fone).
- Se não for nenhuma dessas 4 situações críticas, responda APENAS:
SILENCE
"""


class SentinelWatcher:
    def __init__(self, brain, speaker, groq_client=None, interval_seconds: int = 25, enabled: bool = True, tray_app=None, anti_cheat_protection: bool = False, overlay=None):
        self.brain = brain
        self.speaker = speaker
        self.groq_client = groq_client
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.anti_cheat_protection = anti_cheat_protection
        self.overlay = overlay
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_alert_time = 0.0
        self._alert_cooldown = 35.0  # Mínimo de 35 segundos entre alertas automáticos para não ser chata
        self.tray_app = tray_app

    def start(self):
        """Inicia o loop da Sentinela em thread separada."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Interrompe a Sentinela."""
        self._running = False

    def toggle(self) -> bool:
        """Alterna entre ligado e desligado."""
        self.enabled = not self.enabled
        return self.enabled

    def _loop(self):
        """Loop de monitoramento que roda a cada intervalo definido."""
        while self._running:
            time.sleep(self.interval_seconds)

            if not self.enabled or not self.groq_client:
                continue

            # Se o jogador estiver falando no push-to-talk ou ouvindo resposta, espera a próxima rodada
            if getattr(self.speaker, "is_playing", False):
                continue

            # Respeita o cooldown entre alertas falados
            if (time.time() - self._last_alert_time) < self._alert_cooldown:
                continue

            if time.time() < getattr(self, "_backoff_until", 0.0):
                continue

            self._check_screen()

    def _check_screen(self):
        """Captura o frame e envia para a checagem da Sentinela."""
        try:
            image_data = capture_screen_base64(max_width=1024, quality=65)
            if not image_data:
                return

            # Injeta regras ativas do jogador para respeitar proibições
            memory_rules = ""
            if hasattr(self.brain, "memory"):
                rules = self.brain.memory.data.get("custom_rules", [])
                if rules:
                    memory_rules = f"\nREGRAS DO JOGADOR A RESPEITAR:\n" + "\n".join([f"- {r}" for r in rules])

            active_game, anti_cheat_strict = detect_running_game()
            
            # Modo Stealth: Desativa verificação autônoma APENAS se explicitamente configurado pelo usuário
            if anti_cheat_strict and self.anti_cheat_protection:
                if self.tray_app:
                    self.tray_app.set_stealth_mode(True)
                return  # Pula esta verificação para evitar falso-positivo em jogos restritos
            elif self.tray_app:
                self.tray_app.set_stealth_mode(False)
            
            game_hint = f" [O jogador está jogando '{active_game}']" if active_game else ""
            full_prompt = SENTINEL_PROMPT + game_hint + memory_rules

            messages = [
                {"role": "system", "content": full_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Verifique a tela atual do jogo.{game_hint}"},
                        {"type": "image_url", "image_url": {"url": image_data}}
                    ]
                }
            ]

            completion = self.groq_client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=messages,
                temperature=0.2,
                max_tokens=60,
            )

            response = completion.choices[0].message.content.strip()

            # Filtro de Silêncio
            if "SILENCE" in response.upper():
                # Nada crítico: mantém silêncio absoluto
                return

            # Evento crítico detectado!
            alert_text = response.replace("SILENCE", "").strip()
            if alert_text:
                self._last_alert_time = time.time()
                print(f"\n🚨 [Sentinela]: \"{alert_text}\"")
                self.speaker.speak(alert_text)
                if hasattr(self, "overlay") and self.overlay:
                    title = f"⚠️ PERIGO — {active_game}" if active_game else "⚠️ ALERTA DA SENTINELA"
                    self.overlay.show_message(alert_text, title=title, duration=5.0, is_alert=True)

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate_limit" in err_str:
                # Pausa por 3 minutos para não esgotar tokens da cota gratuita
                self._backoff_until = time.time() + 180.0

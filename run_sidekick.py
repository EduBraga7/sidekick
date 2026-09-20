"""Ponto de entrada principal do Sidekick (Universal Gaming Buddy)."""

import json
import os
import sys
import threading
import time

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv
from pynput import keyboard, mouse

try:
    from src.input.windows_hotkey import WindowsHotkeyListener, is_hotkey_supported
    WINDOWS_HOTKEY_AVAILABLE = True
except ImportError:
    WINDOWS_HOTKEY_AVAILABLE = False

from src.audio.chimes import ChimePlayer
from src.audio.player import AudioPlayer
from src.audio.recorder import AudioRecorder
from src.tts.edge_speaker import EdgeSpeaker
from src.stt.whisper_client import WhisperTranscriber
from src.ai.brain import SidekickBrain
from src.ui.tray import TrayApp
from src.ui.overlay import GameOverlay
from src.audio.wake_word import WakeWordDetector
from src.vision.screengrab import capture_screen_base64
from src.vision.sentinel import SentinelWatcher
from src.vision.game_detector import detect_running_game


from src.utils.paths import get_base_dir, get_config_path, get_env_path


def load_configuration():
    """Carrega as configurações do config.json e variáveis de ambiente."""
    env_path = get_env_path()
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()

    config_path = get_config_path()
    config = {
        "push_to_talk_key": "caps_lock",
        "preferred_provider": "groq",
        "groq_api_key": "",
        "gemini_api_key": "",
        "voice": "pt-BR-ThalitaMultilingualNeural",
        "voice_rate": "+5%",
        "voice_pitch": "+0Hz",
        "play_chimes": True,
        "chime_volume": 0.2,
        "game_profile": "universal",
        "enable_screen_vision": True,
        "sentinel_mode_enabled": True,
        "sentinel_interval_seconds": 25,
        "anti_cheat_protection": False,
        "input_method": "pynput",  # Opções: "pynput" (padrão) ou "windows_hotkey" (mais seguro)
        "enable_overlay": True,
        "overlay_position": "top_right",
        "enable_wake_word": False,
        "wake_word_sensitivity": "media",
        "personality": "parceira",
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print(f"[Config]: Erro ao ler {config_path}: {e}")

    # Prioridade: .env > config.json (segurança: chaves no .env não são commitadas)
    env_groq_key = os.getenv("GROQ_API_KEY", "").strip()
    env_gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    if env_groq_key:
        config["groq_api_key"] = env_groq_key
    if env_gemini_key:
        config["gemini_api_key"] = env_gemini_key

    return config


class SidekickCopilot:
    def __init__(self):
        self.config = load_configuration()
        self.is_running = True

        # Pipeline de áudio
        self.chimes = ChimePlayer(
            volume=self.config.get("chime_volume", 0.2),
            enabled=self.config.get("play_chimes", True)
        )
        self.player = AudioPlayer()
        self.recorder = AudioRecorder()
        self.speaker = EdgeSpeaker(
            voice=self.config.get("voice", "pt-BR-ThalitaMultilingualNeural"),
            rate=self.config.get("voice_rate", "+5%"),
            pitch=self.config.get("voice_pitch", "+0Hz"),
            player=self.player
        )

        # Clientes de IA
        self.groq_client = None
        self.gemini_client = None
        self._init_ai_clients()

        self.transcriber = WhisperTranscriber(
            groq_client=self.groq_client,
            gemini_client=self.gemini_client
        )
        self.brain = SidekickBrain(
            groq_client=self.groq_client,
            gemini_client=self.gemini_client,
            personality=self.config.get("personality", "parceira")
        )

        # Configuração do gatilho Push-to-Talk e Visão
        self.target_key = self.config.get("push_to_talk_key", "caps_lock").lower()
        self.enable_vision = self.config.get("enable_screen_vision", True)
        self.is_pressed = False
        self._is_processing = False
        
        # Escolhe método de input (pynput vs windows_hotkey)
        self.input_method = self.config.get("input_method", "pynput").lower()
        self.use_windows_hotkey = (
            self.input_method == "windows_hotkey" and 
            WINDOWS_HOTKEY_AVAILABLE and 
            is_hotkey_supported(self.target_key)
        )
        
        # HUD Overlay dentro do Jogo
        self.overlay = GameOverlay(
            enabled=self.config.get("enable_overlay", True),
            position=self.config.get("overlay_position", "top_right")
        )

        # Interface System Tray (precisa ser criada antes do Sentinel)
        self.tray = TrayApp(
            key_name=self.target_key,
            on_test_voice=self._test_voice,
            on_toggle_sentinel=None,  # Será definido depois
            sentinel_enabled=self.config.get("sentinel_mode_enabled", True),
            on_quit=self.stop
        )
        
        # Modo Sentinela (Monitoramento autônomo com silêncio inteligente)
        self.sentinel = SentinelWatcher(
            brain=self.brain,
            speaker=self.speaker,
            groq_client=self.groq_client,
            interval_seconds=self.config.get("sentinel_interval_seconds", 25),
            enabled=self.config.get("sentinel_mode_enabled", True),
            tray_app=self.tray,
            anti_cheat_protection=self.config.get("anti_cheat_protection", False),
            overlay=self.overlay
        )
        
        # Atualiza o callback do tray com o toggle do sentinel
        self.tray.on_toggle_sentinel = self.sentinel.toggle

        # Modo Mãos Livres (Wake Word — "Ei Sidekick")
        self.wake_detector = WakeWordDetector(
            transcriber=self.transcriber,
            on_wake_detected=self._on_wake_detected,
            enabled=self.config.get("enable_wake_word", False),
            sensitivity=self.config.get("wake_word_sensitivity", "media")
        )

    def _init_ai_clients(self):
        """Inicializa clientes Groq ou Gemini com as chaves disponíveis."""
        groq_key = self.config.get("groq_api_key", "").strip()
        if groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_key)
                print("[IA]: Cliente Groq pronto (Qwen Multimodal + Whisper)!")
            except Exception as e:
                print(f"[IA]: Erro ao inicializar Groq: {e}")

        gemini_key = self.config.get("gemini_api_key", "").strip()
        if gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_key)
                print("[IA]: Cliente Gemini pronto (2.5 Flash Multimodal)!")
            except Exception as e:
                print(f"[IA]: Erro ao inicializar Gemini: {e}")

    def reload_config(self):
        """Recarrega o config.json em tempo de execução sem precisar reiniciar o processo."""
        self.config = load_configuration()
        self.target_key = self.config.get("push_to_talk_key", "caps_lock").lower()
        self.enable_vision = self.config.get("enable_screen_vision", True)
        
        # Atualiza áudio
        self.speaker.voice = self.config.get("voice", "pt-BR-ThalitaMultilingualNeural")
        self.speaker.rate = self.config.get("voice_rate", "+5%")
        self.speaker.pitch = self.config.get("voice_pitch", "+0Hz")
        self.chimes.enabled = self.config.get("play_chimes", True)
        self.chimes.volume = self.config.get("chime_volume", 0.2)
        
        # Atualiza IA
        self._init_ai_clients()
        self.transcriber.groq_client = self.groq_client
        self.transcriber.gemini_client = self.gemini_client
        self.brain.groq_client = self.groq_client
        self.brain.gemini_client = self.gemini_client
        self.brain.personality = self.config.get("personality", "parceira")
        if hasattr(self.brain, "wiki_manager"):
            self.brain.wiki_manager.groq_client = self.groq_client
            
        # Atualiza Sentinela
        self.sentinel.interval_seconds = self.config.get("sentinel_interval_seconds", 25)
        self.sentinel.enabled = self.config.get("sentinel_mode_enabled", True)
        self.sentinel.groq_client = self.groq_client
        
        # Atualiza Overlay
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.set_enabled(self.config.get("enable_overlay", True))
            self.overlay.set_position(self.config.get("overlay_position", "top_right"))

        # Atualiza Wake Word (Mãos Livres)
        if hasattr(self, 'wake_detector') and self.wake_detector:
            self.wake_detector.transcriber = self.transcriber
            self.wake_detector.set_sensitivity(self.config.get("wake_word_sensitivity", "media"))
            self.wake_detector.set_enabled(self.config.get("enable_wake_word", False))

        print("[Config]: Configurações recarregadas e aplicadas com sucesso!")

    def _test_voice(self):
        """Dispara uma saudação de teste para confirmar o funcionamento do áudio."""
        saudacao = (
            "E aí! Tô conectada aqui no seu Discord! "
            "Pode segurar o atalho a qualquer momento enquanto joga pra gente trocar ideia sobre o jogo."
        )
        print(f"\n[Sidekick]: {saudacao}")
        self.speaker.speak(saudacao)

    def _start_interaction(self):
        """Inicia a gravação de áudio e captura a tela do jogo se a visão estiver habilitada."""
        if not self.is_pressed:
            self.is_pressed = True
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.show_listening()
            self.player.stop()
            self.chimes.play_start()
            self._current_screenshot = None
            self._capture_event = threading.Event()
            if self.enable_vision:
                threading.Thread(target=self._capture_screen_worker, daemon=True).start()
            self.recorder.start_recording()

    def _capture_screen_worker(self):
        try:
            self._current_screenshot = capture_screen_base64(max_width=768, quality=60)
        except Exception:
            self._current_screenshot = None
        finally:
            if hasattr(self, "_capture_event") and self._capture_event:
                self._capture_event.set()

    def _finish_interaction(self):
        """Finaliza a gravação e envia áudio + tela para a Sidekick."""
        if self.is_pressed:
            self.is_pressed = False
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.show_thinking()
            self.chimes.play_done()
            audio_buffer = self.recorder.stop_recording()

            # Aguarda até 350ms para garantir que a captura da tela terminou
            if self.enable_vision and hasattr(self, "_capture_event") and not self._capture_event.is_set():
                self._capture_event.wait(timeout=0.35)

            screenshot = self._current_screenshot
            self._current_screenshot = None

            if audio_buffer and not self._is_processing:
                threading.Thread(
                    target=self._process_voice_query,
                    args=(audio_buffer, screenshot),
                    daemon=True
                ).start()
            elif not audio_buffer:
                if hasattr(self, 'overlay') and self.overlay:
                    self.overlay.hide()

    def _match_mouse_button(self, button):
        """Compara o botão de mouse pressionado com o atalho configurado."""
        try:
            btn_str = str(button).lower().replace("button.", "")
            if self.target_key in [btn_str, f"mouse_{btn_str}", f"xbutton{btn_str[-1:] if btn_str.startswith('x') else ''}"]:
                return True
        except Exception:
            pass
        return False

    def on_mouse_click(self, x, y, button, pressed):
        if not self._match_mouse_button(button):
            return

        if pressed:
            self._start_interaction()
        else:
            self._finish_interaction()

    def _match_key(self, key):
        """Compara a tecla pressionada com o atalho configurado."""
        try:
            if hasattr(key, "name") and key.name:
                return key.name.lower() == self.target_key
            if hasattr(key, "char") and key.char:
                return key.char.lower() == self.target_key
        except Exception:
            pass
        return False

    def on_press(self, key):
        if self._match_key(key):
            self._start_interaction()

    def on_release(self, key):
        if self._match_key(key):
            self._finish_interaction()

    def _on_wake_detected(self, command_text: str, full_text: str):
        """Callback disparado quando o jogador fala 'Ei Sidekick' no microfone."""
        if self._is_processing or not self.is_running:
            return

        if command_text:
            # Pergunta falada junto com a ativação ("Ei Sidekick, onde dropa ferro?")
            self.chimes.play_start()
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.show_thinking()

            screenshot = None
            if self.enable_vision:
                try:
                    screenshot = capture_screen_base64(max_width=768, quality=60)
                except Exception:
                    screenshot = None

            self._execute_query(command_text, screenshot=screenshot)
        else:
            # Apenas a chamada ("Ei Sidekick!")
            self.chimes.play_start()
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.show_message("Tô ouvindo! Pode falar...", title="🎙️ SIDEKICK (MÃOS LIVRES)", duration=5.0)
            if hasattr(self, 'wake_detector') and self.wake_detector:
                self.wake_detector.enable_follow_up_mode(duration=7.0)

    def _execute_query(self, text: str, screenshot=None):
        """Pipeline unificado de raciocínio da IA, HUD overlay e fala."""
        self._is_processing = True
        if hasattr(self, 'wake_detector') and self.wake_detector:
            self.wake_detector.pause_listening()
        try:
            print(f"\n[Você]: \"{text}\"")
            if screenshot:
                print("📸 [Olhos]: Tela do jogo capturada e analisada!")

            # Detecção de Jogo Ativo no Windows
            detected_game, anti_cheat_strict = detect_running_game()
            if detected_game:
                print(f"🎮 [Jogo Detectado]: {detected_game} (Anti-cheat strict: {anti_cheat_strict})")
                if hasattr(self.brain, "wiki_manager"):
                    self.brain.wiki_manager.ensure_game_wiki_async(detected_game)

            # Raciocínio Multimodal Ancorado no Jogo Real
            anti_cheat_protection = self.config.get("anti_cheat_protection", False)
            is_stealth = anti_cheat_strict and anti_cheat_protection
            final_screenshot = screenshot if self.enable_vision and not is_stealth else None
            
            if is_stealth and screenshot:
                print("⚠️ [Modo Stealth]: Visão desativada por configuração anti-cheat")
                self.tray.set_stealth_mode(True)
            else:
                self.tray.set_stealth_mode(False)
            
            response = self.brain.think_and_respond(text, image_data=final_screenshot, detected_game=detected_game, anti_cheat_strict=anti_cheat_strict)
            print(f"[Sidekick]: \"{response}\"")

            # Exibe mensagem no HUD Overlay dentro do jogo
            if hasattr(self, 'overlay') and self.overlay:
                overlay_title = f"🎮 {detected_game}" if detected_game else "Sidekick"
                self.overlay.show_message(response, title=overlay_title, duration=6.0)

            # Fala
            self.speaker.speak(response)

        except Exception as e:
            print(f"[Erro no processamento]: {e}")
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.hide()
            self.chimes.play_error()
        finally:
            self._is_processing = False
            if hasattr(self, 'wake_detector') and self.wake_detector:
                self.wake_detector.resume_listening()

    def _process_voice_query(self, audio_buffer, screenshot=None):
        """Pipeline do Push-to-Talk: Áudio -> Transcrição -> _execute_query."""
        try:
            # Transcrição
            text = self.transcriber.transcribe(audio_buffer)
            if not text:
                if hasattr(self, 'overlay') and self.overlay:
                    self.overlay.hide()
                if not self.groq_client and not self.gemini_client:
                    msg = (
                        "Opa, não consegui te ouvir! Lembre-se de colocar sua chave gratuita "
                        "do Groq ou Gemini no config.json pra gente começar."
                    )
                    print(f"[Sidekick]: {msg}")
                    self.speaker.speak(msg)
                return

            self._execute_query(text, screenshot=screenshot)

        except Exception as e:
            print(f"[Erro no processamento]: {e}")
            if hasattr(self, 'overlay') and self.overlay:
                self.overlay.hide()
            self.chimes.play_error()

    def start(self):
        """Inicia todos os serviços da Sidekick."""
        self.is_running = True
        print("=" * 60)
        print("🎮  SIDEKICK — SEU COPILOTO GAMER UNIVERSAL")
        print("=" * 60)
        print(f"-> Tecla Push-to-Talk: [{self.target_key.upper()}]")
        print(f"-> Personalidade: {self.brain.personality.capitalize()}")
        print(f"-> Voz: {self.config.get('voice')}")
        print(f"-> Modo Sentinela (Auto-Vigiar): {'ATIVADO (intervalo: ' + str(self.sentinel.interval_seconds) + 's)' if self.sentinel.enabled else 'DESATIVADO'}")
        print(f"-> Modo Mãos Livres (Wake Word): {'ATIVADO (\"Ei Sidekick\")' if hasattr(self, 'wake_detector') and self.wake_detector.enabled else 'DESATIVADO'}")
        print(f"-> Proteção Anti-Cheat: {'ATIVADO' if self.config.get('anti_cheat_protection', False) else 'DESATIVADO'}")
        print(f"-> Método de Input: {'Windows Hotkey (Mais Seguro)' if self.use_windows_hotkey else 'Pynput (Padrão)'}")
        print("-> Ícone de Gamepad adicionado à bandeja do Windows (System Tray).")
        print("-> Pressione a tecla de atalho enquanto joga para trocar ideia.")
        print("-> Pressione Ctrl+C nesta janela ou clique em 'Sair' no ícone para encerrar.")
        print("=" * 60)

        self.tray.run()
        self.sentinel.start()
        if hasattr(self, 'wake_detector') and self.wake_detector and self.wake_detector.enabled:
            self.wake_detector.start()

        # Escolhe método de input baseado na configuração
        if self.use_windows_hotkey:
            # Usa Windows API Hotkey (mais seguro para anti-cheat)
            print(f"[Input]: Usando Windows Hotkey para '{self.target_key}' (mais seguro)")
            hotkey_listener = WindowsHotkeyListener(
                key_name=self.target_key,
                on_press=self._start_interaction,
                on_release=self._finish_interaction
            )
            hotkey_listener.start()
            self._hotkey_listener = hotkey_listener
        else:
            # Usa pynput (padrão, mais flexível mas pode ser detectado)
            print(f"[Input]: Usando Pynput para '{self.target_key}' (padrão)")
            # Ouvinte global de teclado
            kb_listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            kb_listener.daemon = True
            kb_listener.start()
            self._kb_listener = kb_listener

            # Ouvinte global de mouse
            mouse_listener = mouse.Listener(
                on_click=self.on_mouse_click
            )
            mouse_listener.daemon = True
            mouse_listener.start()
            self._mouse_listener = mouse_listener

        try:
            while self.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self, exit_process: bool = True):
        """Encerra a Sidekick."""
        print("\n[Sidekick]: Falou parceiro, até a próxima gameplay!")
        self.is_running = False
        self.sentinel.stop()
        if hasattr(self, 'wake_detector') and self.wake_detector:
            self.wake_detector.stop()
        self.tray.stop()
        self.player.stop()
        if hasattr(self, 'speaker') and self.speaker:
            self.speaker.cleanup()
        if hasattr(self, 'overlay') and self.overlay:
            self.overlay.stop()
        
        # Para listeners se estiverem em uso
        if hasattr(self, '_hotkey_listener') and self._hotkey_listener:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None

        if hasattr(self, '_kb_listener') and self._kb_listener:
            try:
                self._kb_listener.stop()
            except Exception:
                pass
            self._kb_listener = None

        if hasattr(self, '_mouse_listener') and self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None
        
        if exit_process:
            sys.exit(0)


def launch_gui_mode(copilot: SidekickCopilot):
    """Inicializa a interface gráfica moderna conectada à instância do Sidekick."""
    from src.ui.main_window import create_gui

    gui = create_gui(
        start_callback=copilot.start,
        stop_callback=lambda: copilot.stop(exit_process=False),
        test_voice_callback=copilot._test_voice,
        reload_config_callback=copilot.reload_config
    )

    # Atualiza GUI com informações iniciais
    gui.update_input_method("Windows Hotkey" if copilot.use_windows_hotkey else "Pynput")

    # Override do stop para atualizar GUI
    original_stop = copilot.stop
    def gui_stop():
        gui.set_running(False)
        original_stop(exit_process=False)
    copilot.stop = gui_stop

    # Override do start para atualizar GUI
    original_start = copilot.start
    def gui_start():
        gui.set_running(True)
        original_start()
    copilot.start = gui_start

    # Inicia a GUI
    gui.run()


if __name__ == "__main__":
    # Verifica se deve usar GUI ou modo console
    use_gui = "--gui" in sys.argv or "-g" in sys.argv
    copilot = SidekickCopilot()

    if use_gui:
        launch_gui_mode(copilot)
    else:
        copilot.start()

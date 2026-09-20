"""Testes unitários automatizados para o sistema Sidekick."""

import os
import unittest
from src.audio.chimes import ChimePlayer
from src.audio.recorder import AudioRecorder
from src.tts.edge_speaker import clean_text_for_speech
from src.ai.brain import SidekickBrain
from src.ai.sidekick_prompt import SIDEKICK_SYSTEM_PROMPT
from run_sidekick import load_configuration


class TestSidekickSuite(unittest.TestCase):
    def test_01_config_loader(self):
        """Verifica se o config.json carrega as configurações da Sidekick."""
        config = load_configuration()
        self.assertIn("push_to_talk_key", config)
        self.assertEqual(config.get("voice"), "pt-BR-ThalitaMultilingualNeural")
        self.assertEqual(config.get("game_profile"), "universal")
        print("[OK] Configuração da Sidekick validada com sucesso.")

    def test_02_chimes(self):
        """Verifica se o gerador de bipes opera sem erro."""
        player = ChimePlayer(volume=0.05, enabled=True)
        player.play_start()
        player.play_done()
        print("[OK] Bipes sonoros funcionando.")

    def test_03_text_cleaning(self):
        """Verifica se emojis e caracteres especiais do unicode são limpos."""
        raw = "E aí **parceiro**! Cuidado com o boss \u2011 usa parry agora!"
        cleaned = clean_text_for_speech(raw)
        self.assertEqual(cleaned, "E aí parceiro! Cuidado com o boss - usa parry agora!")
        print("[OK] Limpeza e normalização de texto funcionando perfeitamente.")

    def test_04_sidekick_prompt(self):
        """Verifica se o prompt é universal e proíbe bordões repetitivos."""
        self.assertIn("Sidekick", SIDEKICK_SYSTEM_PROMPT)
        self.assertIn("PROIBIDO USAR BORDÕES REPETITIVOS", SIDEKICK_SYSTEM_PROMPT)
        self.assertIn("Albion Online", SIDEKICK_SYSTEM_PROMPT)
        self.assertIn("Dark Souls", SIDEKICK_SYSTEM_PROMPT)
        print("[OK] Prompt universal de games e proibição de bordões validado.")

    def test_05_brain_fallback(self):
        """Verifica a resposta de fallback amigável da Sidekick."""
        brain = SidekickBrain(groq_client=None, gemini_client=None)
        resp = brain.think_and_respond("Qual arma eu uso?", anti_cheat_strict=False)
        self.assertIn("config.json", resp)
        print(f"[OK] Resposta de fallback: '{resp[:45]}...'")

    def test_06_recorder(self):
        """Verifica inicialização do gravador."""
        rec = AudioRecorder()
        self.assertEqual(rec.sample_rate, 16000)
        print("[OK] Gravador de áudio pronto.")

    def test_07_memory_persistence_and_limits(self):
        """Verifica salvamento, carregamento e limites da memória de longo prazo."""
        import tempfile
        from src.ai.memory import LongTermMemory, MAX_REMINDERS
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            mem = LongTermMemory(filepath=tmp_path)
            mem.update_game("dark_souls_1", weapon="Zweihander +5", new_boss="Gargoyles", progress="Sino tocado")
            
            # Testa limite de lembretes
            for i in range(15):
                mem.add_reminder(f"Lembrete {i}")

            # Recarrega do arquivo
            mem_reloaded = LongTermMemory(filepath=tmp_path)
            self.assertEqual(len(mem_reloaded.data["reminders"]), MAX_REMINDERS)
            self.assertEqual(mem_reloaded.data["games"]["dark_souls_1"]["current_weapon"], "Zweihander +5")
            self.assertIn("Gargoyles", mem_reloaded.data["games"]["dark_souls_1"]["defeated_bosses"])
            print("[OK] Memória persistida e limite rígido de 10 lembretes respeitado.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_08_memory_context_prompt(self):
        """Verifica se o contexto da memória é formatado adequadamente."""
        import tempfile
        from src.ai.memory import LongTermMemory
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            mem = LongTermMemory(filepath=tmp_path)
            mem.update_game("albion_online", weapon="Espada Larga T6", progress="Foco em Thetford")
            context = mem.get_context_for_prompt()
            self.assertIn("Albion Online", context)
            self.assertIn("Espada Larga T6", context)
            print("[OK] Injeção de contexto de memória para o prompt validada.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


    def test_09_rules_learning(self):
        """Verifica se regras do jogador são salvas e injetadas no prompt."""
        import tempfile
        from src.ai.memory import LongTermMemory
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            mem = LongTermMemory(filepath=tmp_path)
            mem.add_rule("Nunca me avise sobre barra de vida")
            mem.add_rule("Sempre avise quando vir um baú escondido")
            
            reloaded = LongTermMemory(filepath=tmp_path)
            self.assertIn("Nunca me avise sobre barra de vida", reloaded.data["custom_rules"])
            self.assertIn("Sempre avise quando vir um baú escondido", reloaded.data["custom_rules"])

            context = reloaded.get_context_for_prompt()
            self.assertIn("REGRAS E ORDENS MANDATÓRIAS", context)
            self.assertIn("Nunca me avise sobre barra de vida", context)
            print("[OK] Sistema de aprendizado e obediência a regras do jogador validado.")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_10_sentinel_init_and_toggle(self):
        """Verifica a inicialização e alternância do Modo Sentinela."""
        from src.vision.sentinel import SentinelWatcher
        
        sentinel = SentinelWatcher(brain=None, speaker=None, interval_seconds=20, enabled=True)
        self.assertTrue(sentinel.enabled)
        self.assertEqual(sentinel.interval_seconds, 20)
        
        # Testa toggle
        state = sentinel.toggle()
        self.assertFalse(state)
        self.assertFalse(sentinel.enabled)
        print("[OK] Modo Sentinela inicializado e toggle verificado.")

    def test_11_tray_stealth_mode(self):
        """Verifica se o ícone do tray muda corretamente no modo stealth."""
        from src.ui.tray import TrayApp, create_gamepad_icon
        
        # Cria ícones normal e stealth
        normal_icon = create_gamepad_icon(stealth_mode=False)
        stealth_icon = create_gamepad_icon(stealth_mode=True)
        
        # Verifica que são imagens válidas
        self.assertIsNotNone(normal_icon)
        self.assertIsNotNone(stealth_icon)
        
        # Verifica que têm o mesmo tamanho
        self.assertEqual(normal_icon.size, stealth_icon.size)
        
        print("[OK] Ícones normal e stealth gerados corretamente.")

    def test_12_windows_hotkey_available(self):
        """Verifica se o Windows Hotkey está disponível e funciona."""
        try:
            from src.input.windows_hotkey import WindowsHotkeyListener, is_hotkey_supported, get_supported_keys
            
            # Verifica teclas suportadas
            supported = get_supported_keys()
            self.assertIn("caps_lock", supported)
            self.assertIn("f1", supported)
            
            # Verifica detecção de suporte
            self.assertTrue(is_hotkey_supported("caps_lock"))
            self.assertTrue(is_hotkey_supported("f1"))
            self.assertFalse(is_hotkey_supported("tecla_inexistente"))
            
            print(f"[OK] Windows Hotkey disponível com {len(supported)} teclas suportadas")
        except ImportError:
            print("[SKIP] Windows Hotkey não disponível (requer Windows)")

    def test_13_gui_creation(self):
        """Verifica se a GUI pode ser criada sem erros."""
        try:
            from src.ui.main_window import SidekickGUI
            
            # Cria callbacks mock
            def mock_start(): pass
            def mock_stop(): pass
            def mock_test(): pass
            
            # Tenta criar a GUI (sem rodar o loop)
            # Usa withdraw para não mostrar a janela
            import tkinter as tk
            try:
                gui = SidekickGUI(mock_start, mock_stop, mock_test)
                gui.root.withdraw()  # Esconde a janela
                
                # Verifica que foi criada
                self.assertIsNotNone(gui.root)
                self.assertIsNotNone(gui.status_labels)
                
                # Verifica métodos principais
                self.assertTrue(hasattr(gui, '_start_sidekick'))
                self.assertTrue(hasattr(gui, '_log'))
                self.assertTrue(hasattr(gui, '_update_status'))
                
                # Fecha a janela
                gui.root.destroy()
                
                print("[OK] GUI criada com sucesso")
            except tk.TclError:
                print("[SKIP] GUI não disponível (sem display)")
        except ImportError:
            print("[SKIP] GUI não disponível (tkinter não instalado)")

    def test_14_wiki_knowledge(self):
        """Verifica o gerenciamento, carregamento e injeção das Wikis dos jogos."""
        from src.ai.wiki_knowledge import WikiKnowledgeManager
        wm = WikiKnowledgeManager(groq_client=None)
        
        # Verifica se as wikis pré-semeadas existem
        self.assertTrue(wm.has_wiki("Children of Morta"))
        self.assertTrue(wm.has_wiki("Albion Online"))
        self.assertTrue(wm.has_wiki("Dark Souls 1"))
        
        # Verifica carregamento dos dados
        morta_wiki = wm.get_game_wiki("Children of Morta")
        self.assertIsNotNone(morta_wiki)
        self.assertEqual(morta_wiki["game_name"], "Children of Morta")
        self.assertTrue(len(morta_wiki["characters"]) > 0)
        
        # Verifica injeção de contexto de prompt
        context = wm.get_prompt_context("Children of Morta", "Como jogo com John?")
        self.assertIn("Children of Morta", context)
        self.assertIn("John", context)
        print("[OK] Motor de Wikis e injeção de conhecimento tático validado.")

    def test_15_game_overlay(self):
        """Verifica o componente de HUD overlay in-game transparente."""
        from src.ui.overlay import GameOverlay
        try:
            overlay = GameOverlay(enabled=True, position="top_right")
            self.assertTrue(overlay.enabled)
            self.assertEqual(overlay.position, "top_right")
            
            # Testa métodos de fila
            overlay.show_listening()
            overlay.show_thinking("Albion Online")
            overlay.show_message("Teste de legenda", title="Sidekick", duration=1.0)
            overlay.set_position("bottom_center")
            self.assertEqual(overlay.position, "bottom_center")
            
            overlay.hide()
            overlay.stop()
            print("[OK] HUD Overlay testado com sucesso.")
        except Exception as e:
            self.fail(f"Erro ao testar GameOverlay: {e}")

    def test_16_wake_word_detector(self):
        """Verifica o componente de Modo Mãos Livres e detecção de wake word."""
        from src.audio.wake_word import WakeWordDetector
        
        # 1. Validação de expressões regulares de wake word
        match1, cmd1 = WakeWordDetector._extract_wake_command(
            "ei sidekick, onde dropa ferro?",
            "Ei Sidekick, onde dropa ferro?"
        )
        self.assertTrue(match1)
        self.assertEqual(cmd1, "onde dropa ferro?")

        match2, cmd2 = WakeWordDetector._extract_wake_command(
            "ei sidekick!",
            "Ei Sidekick!"
        )
        self.assertTrue(match2)
        self.assertEqual(cmd2, "")

        match3, cmd3 = WakeWordDetector._extract_wake_command(
            "boa noite galera",
            "Boa noite galera"
        )
        self.assertFalse(match3)

        # 2. Ciclo de vida e sensibilidade do detector
        detector = WakeWordDetector(
            transcriber=None,
            on_wake_detected=None,
            enabled=False,
            sensitivity="media"
        )
        self.assertEqual(detector.sensitivity, "media")
        detector.set_sensitivity("alta")
        self.assertEqual(detector.sensitivity, "alta")
        
        detector.enable_follow_up_mode(duration=5.0)
        self.assertTrue(detector._follow_up_until > 0)
        
        detector.pause_listening()
        self.assertTrue(detector._is_paused)
        detector.resume_listening()
        self.assertFalse(detector._is_paused)
        detector.stop()
        print("[OK] Detector de Wake Word ('Ei Sidekick') e VAD validados com sucesso.")

    def test_17_personalities(self):
        """Verifica a geração e alternância dos 5 arquétipos de personalidade do copiloto."""
        from src.ai.personality import PERSONALITY_PRESETS, build_personality_prompt, get_personality_meta
        from src.ai.brain import SidekickBrain

        expected_presets = ["parceira", "coach", "zoeiro", "zen", "narrador"]
        for key in expected_presets:
            self.assertIn(key, PERSONALITY_PRESETS)
            meta = get_personality_meta(key)
            self.assertTrue(len(meta["name"]) > 0)
            self.assertTrue(len(meta["description"]) > 0)
            self.assertTrue(len(meta["recommended_voice"]) > 0)

            prompt = build_personality_prompt(key)
            self.assertIn("Você é o Sidekick", prompt)
            self.assertIn("REGRAS DE OURO", prompt)
            self.assertIn("Albion Online", prompt)

        # Verifica integração com o SidekickBrain
        brain_coach = SidekickBrain(personality="coach")
        self.assertEqual(brain_coach.personality, "coach")

        brain_zen = SidekickBrain(personality="zen")
        self.assertEqual(brain_zen.personality, "zen")
        print("[OK] 5 Personalidades do Copiloto (Amiga, Coach, Troll, Zen, Narrador) validadas.")


if __name__ == "__main__":
    unittest.main(verbosity=2)

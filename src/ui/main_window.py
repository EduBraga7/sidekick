"""Interface Gráfica Moderna do Sidekick usando CustomTkinter com Sistema de Abas (Painel + Configurações)."""

import json
import os
import sys
import time
import threading
from typing import Callable, Optional, Dict, Any
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

# Compatibilidade para código legado ou testes que chamam .config() em vez de .configure()
ctk.CTkLabel.config = ctk.CTkLabel.configure
ctk.CTkButton.config = ctk.CTkButton.configure
ctk.CTkFrame.config = ctk.CTkFrame.configure


from src.utils.paths import get_base_dir


from src.ai.personality import PERSONALITY_PRESETS, get_personality_meta

PERSONALITY_OPTIONS = {
    v["name"]: k for k, v in PERSONALITY_PRESETS.items()
}
PERSONALITY_MAP_REV = {
    k: v["name"] for k, v in PERSONALITY_PRESETS.items()
}

VOICE_OPTIONS = {
    "Thalita (Feminina Expressiva)": "pt-BR-ThalitaMultilingualNeural",
    "Antonio (Masculino Gamer)": "pt-BR-AntonioNeural",
    "Francisca (Feminina Calma)": "pt-BR-FranciscaNeural",
    "Manuela (Feminina Neutra)": "pt-BR-ManuelaNeural",
    "Nicolau (Masculino Maduro)": "pt-BR-NicolauNeural",
    "Jenny (Inglês US - Feminina)": "en-US-JennyNeural",
    "Guy (Inglês US - Masculino)": "en-US-GuyNeural"
}
VOICE_MAP_REV = {v: k for k, v in VOICE_OPTIONS.items()}

KEY_OPTIONS = [
    "caps_lock", "scroll_lock", "num_lock",
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "mouse_x1", "mouse_x2", "mouse_middle"
]


class SidekickGUI:
    """Janela moderna do Sidekick com Painel em Tempo Real e Aba de Configurações."""

    def __init__(
        self,
        start_callback: Callable,
        stop_callback: Callable,
        test_voice_callback: Callable,
        reload_config_callback: Optional[Callable] = None
    ):
        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.test_voice_callback = test_voice_callback
        self.reload_config_callback = reload_config_callback

        self.is_running = False
        self.stealth_mode = False
        self.sentinel_enabled = True
        self.current_game = "Nenhum"

        # Carrega configuração atual do disco
        self.config_data = self._load_current_config()

        # Configuração de aparência do CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("🎮 Sidekick — Copiloto Gamer")
        self.root.geometry("650x680")
        self.root.minsize(620, 620)
        self.root.configure(fg_color="#0b0d14")

        # Tenta aplicar ícone se existir
        icon_path = os.path.join(os.path.dirname(__file__), "gamepad_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.status_labels = {}

        # Estrutura Principal de Abas
        self._build_header()
        self._build_tabs()

        # Intercepta fechamento da janela para saída limpa
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _load_current_config(self) -> Dict[str, Any]:
        """Lê config.json local para alimentar a tela de configurações."""
        config_path = os.path.join(get_base_dir(), "config.json")
        default_cfg = {
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
            "input_method": "pynput",
            "enable_overlay": True,
            "overlay_position": "top_right",
            "enable_wake_word": False,
            "wake_word_sensitivity": "media",
            "personality": "parceira"
        }
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    default_cfg.update(user_cfg)
            except Exception as e:
                print(f"[GUI Config Load Error]: {e}")
        return default_cfg

    def _build_header(self):
        """Cabeçalho superior comum."""
        header_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(16, 6))

        title_sub_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_sub_frame.pack(side="left")

        title_lbl = ctk.CTkLabel(
            title_sub_frame,
            text="🎮 SIDEKICK",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#38bdf8"
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            title_sub_frame,
            text="Seu Copiloto Gamer Universal com IA Multimodal",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        subtitle_lbl.pack(anchor="w")

        # Badge pill superior direito
        self.live_badge = ctk.CTkLabel(
            header_frame,
            text="⚪ OFFLINE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8",
            fg_color="#181e2e",
            corner_radius=12,
            padx=12,
            pady=4
        )
        self.live_badge.pack(side="right", pady=4)

    def _build_tabs(self):
        """Constrói as abas: 🎮 Painel e ⚙️ Configurações."""
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color="#0f111a",
            segmented_button_fg_color="#161b2a",
            segmented_button_selected_color="#2563eb",
            segmented_button_selected_hover_color="#1d4ed8",
            segmented_button_unselected_hover_color="#1e2538",
            corner_radius=10
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(6, 12))

        self.tab_dashboard = self.tabview.add("🎮 Painel Principal")
        self.tab_settings = self.tabview.add("⚙️ Configurações")

        self._build_dashboard_tab()
        self._build_settings_tab()

    def _build_dashboard_tab(self):
        """Aba 1: Dashboard com status, controles e console."""
        # 1. STATUS CARD
        status_card = ctk.CTkFrame(
            self.tab_dashboard,
            fg_color="#141824",
            border_color="#21283d",
            border_width=1,
            corner_radius=12
        )
        status_card.pack(fill="x", padx=12, pady=(8, 6))

        status_header = ctk.CTkLabel(
            status_card,
            text="📊 STATUS DO SISTEMA",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#64748b"
        )
        status_header.pack(anchor="w", padx=16, pady=(10, 6))

        grid_frame = ctk.CTkFrame(status_card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=16, pady=(0, 12))
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)

        pers_curr = self.config_data.get("personality", "parceira")
        pers_short = PERSONALITY_PRESETS.get(pers_curr, {}).get("name", "Amiga Gamer").split(" (")[0]

        items_col1 = [
            ("Estado", "Parado"),
            ("Jogo Detectado", "Nenhum"),
            ("Personalidade", pers_short),
            ("Input Method", "Pynput")
        ]
        items_col2 = [
            ("Modo Sentinela", "Ativo"),
            ("HUD Overlay", "Ativo"),
            ("Mãos Livres", "Ativo" if self.config_data.get("enable_wake_word", False) else "Inativo"),
            ("Modo Stealth", "Inativo")
        ]

        def add_status_row(parent, row_idx, label_name, default_val):
            row_frame = ctk.CTkFrame(parent, fg_color="transparent")
            row_frame.grid(row=row_idx, column=0, sticky="ew", pady=3, padx=4)

            name_lbl = ctk.CTkLabel(
                row_frame,
                text=f"{label_name}:",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#94a3b8"
            )
            name_lbl.pack(side="left")

            val_badge = ctk.CTkLabel(
                row_frame,
                text=default_val,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color="#38bdf8",
                fg_color="#1c2336",
                corner_radius=6,
                padx=8,
                pady=2
            )
            val_badge.pack(side="right")
            self.status_labels[label_name] = val_badge

        left_col = ctk.CTkFrame(grid_frame, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        for i, (name, val) in enumerate(items_col1):
            add_status_row(left_col, i, name, val)

        right_col = ctk.CTkFrame(grid_frame, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        for i, (name, val) in enumerate(items_col2):
            add_status_row(right_col, i, name, val)

        # 2. CONTROLES CARD
        ctrl_card = ctk.CTkFrame(
            self.tab_dashboard,
            fg_color="#141824",
            border_color="#21283d",
            border_width=1,
            corner_radius=12
        )
        ctrl_card.pack(fill="x", padx=12, pady=6)

        ctrl_header = ctk.CTkLabel(
            ctrl_card,
            text="🎛️ CONTROLES",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#64748b"
        )
        ctrl_header.pack(anchor="w", padx=16, pady=(10, 6))

        # Botão Principal (Iniciar / Parar)
        self.main_btn = ctk.CTkButton(
            ctrl_card,
            text="▶  INICIAR SIDEKICK",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=40,
            corner_radius=8,
            command=self._toggle_run
        )
        self.main_btn.pack(fill="x", padx=16, pady=(0, 8))

        # Botões Secundários
        btn_row = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 8))
        btn_row.grid_columnconfigure(0, weight=1)
        btn_row.grid_columnconfigure(1, weight=1)

        self.voice_btn = ctk.CTkButton(
            btn_row,
            text="🔊 Testar Voz",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=34,
            corner_radius=8,
            command=self._test_voice
        )
        self.voice_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.sentinel_btn = ctk.CTkButton(
            btn_row,
            text="🔄 Toggle Sentinela",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#22293d",
            hover_color="#303b57",
            height=34,
            corner_radius=8,
            command=self._toggle_sentinel
        )
        self.sentinel_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Botão de Sincronização de Wiki
        self.wiki_btn = ctk.CTkButton(
            ctrl_card,
            text="📖 Baixar / Atualizar Wiki do Jogo",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c2336",
            hover_color="#2b3652",
            height=32,
            corner_radius=8,
            command=self._refresh_wiki
        )
        self.wiki_btn.pack(fill="x", padx=16, pady=(0, 8))

        # Checkbox/Switch para modo stealth
        self.stealth_var = tk.BooleanVar(value=False)
        self.stealth_switch = ctk.CTkSwitch(
            ctrl_card,
            text="Forçar Modo Stealth (Desativa telas)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8",
            variable=self.stealth_var,
            command=self._toggle_stealth,
            progress_color="#f59e0b"
        )
        self.stealth_switch.pack(anchor="w", padx=16, pady=(0, 10))

        # 3. LOGS CARD
        log_card = ctk.CTkFrame(
            self.tab_dashboard,
            fg_color="#141824",
            border_color="#21283d",
            border_width=1,
            corner_radius=12
        )
        log_card.pack(fill="both", expand=True, padx=12, pady=6)

        log_header = ctk.CTkLabel(
            log_card,
            text="📋 CONSOLE DE ATIVIDADE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#64748b"
        )
        log_header.pack(anchor="w", padx=16, pady=(8, 4))

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            fg_color="#0a0c12",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            wrap="word",
            border_color="#1c2234",
            border_width=1
        )
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.log_textbox.configure(state="disabled")

        # 4. FOOTER / STATUS BAR
        footer_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        footer_frame.pack(fill="x", padx=16, pady=(4, 6))

        self.status_bar = ctk.CTkLabel(
            footer_frame,
            text="Pronto para iniciar • Segure seu atalho no jogo para conversar",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        )
        self.status_bar.pack(side="left")

        version_lbl = ctk.CTkLabel(
            footer_frame,
            text="v2.2 • Sidekick",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#475569"
        )
        version_lbl.pack(side="right")

    def _build_settings_tab(self):
        """Aba 2: Formulário interativo para salvar configurações."""
        scroll_settings = ctk.CTkScrollableFrame(
            self.tab_settings,
            fg_color="transparent"
        )
        scroll_settings.pack(fill="both", expand=True, padx=12, pady=6)

        cfg = self.config_data

        # --- SEÇÃO 1: ATALHOS & ENTRADA ---
        s1 = ctk.CTkFrame(scroll_settings, fg_color="#141824", border_color="#21283d", border_width=1, corner_radius=10)
        s1.pack(fill="x", pady=6)
        ctk.CTkLabel(s1, text="⌨️ ATALHOS E ENTRADA", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(10, 6))

        row_k = ctk.CTkFrame(s1, fg_color="transparent")
        row_k.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_k, text="Tecla Push-to-Talk:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        current_key = cfg.get("push_to_talk_key", "caps_lock")
        self.key_combo = ctk.CTkComboBox(
            row_k,
            values=KEY_OPTIONS,
            width=180,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.key_combo.set(current_key)
        self.key_combo.pack(side="right")

        row_m = ctk.CTkFrame(s1, fg_color="transparent")
        row_m.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(row_m, text="Método de Entrada:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        self.method_combo = ctk.CTkComboBox(
            row_m,
            values=["pynput", "windows_hotkey"],
            width=180,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.method_combo.set(cfg.get("input_method", "pynput"))
        self.method_combo.pack(side="right")

        # --- SEÇÃO 2: VOZ E PERSONALIDADE ---
        s2 = ctk.CTkFrame(scroll_settings, fg_color="#141824", border_color="#21283d", border_width=1, corner_radius=10)
        s2.pack(fill="x", pady=6)
        ctk.CTkLabel(s2, text="🎭 PERSONALIDADE E VOZ", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(10, 6))

        # Personalidade do Copiloto
        row_pers = ctk.CTkFrame(s2, fg_color="transparent")
        row_pers.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_pers, text="Personalidade do Copiloto:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        curr_pers_key = cfg.get("personality", "parceira")
        curr_pers_name = PERSONALITY_MAP_REV.get(curr_pers_key, list(PERSONALITY_OPTIONS.keys())[0])

        self.pers_combo = ctk.CTkComboBox(
            row_pers,
            values=list(PERSONALITY_OPTIONS.keys()),
            width=230,
            fg_color="#1c2336",
            border_color="#2a3550",
            command=self._on_personality_selected
        )
        self.pers_combo.set(curr_pers_name)
        self.pers_combo.pack(side="right")

        # Descrição dinâmica da Personalidade Selecionada
        self.pers_desc_lbl = ctk.CTkLabel(
            s2,
            text=PERSONALITY_PRESETS.get(curr_pers_key, {}).get("description", ""),
            font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"),
            text_color="#94a3b8",
            wraplength=480,
            justify="left"
        )
        self.pers_desc_lbl.pack(anchor="w", padx=16, pady=(0, 6))

        row_v = ctk.CTkFrame(s2, fg_color="transparent")
        row_v.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_v, text="Voz da IA (Neural):", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        curr_voice = cfg.get("voice", "pt-BR-ThalitaMultilingualNeural")
        curr_voice_name = VOICE_MAP_REV.get(curr_voice, list(VOICE_OPTIONS.keys())[0])

        self.voice_combo = ctk.CTkComboBox(
            row_v,
            values=list(VOICE_OPTIONS.keys()),
            width=220,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.voice_combo.set(curr_voice_name)
        self.voice_combo.pack(side="right")

        row_r = ctk.CTkFrame(s2, fg_color="transparent")
        row_r.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_r, text="Velocidade da Fala:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        self.rate_combo = ctk.CTkComboBox(
            row_r,
            values=["-10%", "+0%", "+5%", "+10%", "+15%", "+20%", "+30%"],
            width=180,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.rate_combo.set(cfg.get("voice_rate", "+5%"))
        self.rate_combo.pack(side="right")

        row_ch = ctk.CTkFrame(s2, fg_color="transparent")
        row_ch.pack(fill="x", padx=16, pady=4)
        self.chimes_var = tk.BooleanVar(value=cfg.get("play_chimes", True))
        self.chimes_switch = ctk.CTkSwitch(row_ch, text="Bipes Sonoros ao Ativar Atalho", variable=self.chimes_var)
        self.chimes_switch.pack(side="left")

        row_vol = ctk.CTkFrame(s2, fg_color="transparent")
        row_vol.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(row_vol, text="Volume dos Bipes:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        self.vol_slider = ctk.CTkSlider(row_vol, from_=0.05, to=1.0, width=180)
        self.vol_slider.set(float(cfg.get("chime_volume", 0.2)))
        self.vol_slider.pack(side="right")

        # --- SEÇÃO 3: MODO SENTINELA ---
        s3 = ctk.CTkFrame(scroll_settings, fg_color="#141824", border_color="#21283d", border_width=1, corner_radius=10)
        s3.pack(fill="x", pady=6)
        ctk.CTkLabel(s3, text="🛡️ MODO SENTINELA (AUTO-VIGIAR)", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(10, 6))

        row_s_on = ctk.CTkFrame(s3, fg_color="transparent")
        row_s_on.pack(fill="x", padx=16, pady=4)
        self.sentinel_cfg_var = tk.BooleanVar(value=cfg.get("sentinel_mode_enabled", True))
        self.sentinel_cfg_switch = ctk.CTkSwitch(row_s_on, text="Sentinela Ativado por Padrão", variable=self.sentinel_cfg_var)
        self.sentinel_cfg_switch.pack(side="left")

        row_s_int = ctk.CTkFrame(s3, fg_color="transparent")
        row_s_int.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(row_s_int, text="Intervalo de Monitoramento (segundos):", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        self.interval_combo = ctk.CTkComboBox(
            row_s_int,
            values=["15", "20", "25", "30", "45", "60"],
            width=100,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.interval_combo.set(str(cfg.get("sentinel_interval_seconds", 25)))
        self.interval_combo.pack(side="right")

        # --- SEÇÃO 4: HUD OVERLAY IN-GAME ---
        s_overlay = ctk.CTkFrame(scroll_settings, fg_color="#141824", border_color="#21283d", border_width=1, corner_radius=10)
        s_overlay.pack(fill="x", pady=6)
        ctk.CTkLabel(s_overlay, text="🖥️ HUD OVERLAY NO JOGO (TRANSLÚCIDO / CLICK-THROUGH)", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(10, 6))

        # Switch Ativar Overlay
        row_ov = ctk.CTkFrame(s_overlay, fg_color="transparent")
        row_ov.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_ov, text="Ativar HUD Flutuante no Jogo:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")
        self.overlay_var = tk.BooleanVar(value=cfg.get("enable_overlay", True))
        self.overlay_switch = ctk.CTkSwitch(
            row_ov,
            text="Ativado",
            variable=self.overlay_var,
            onvalue=True,
            offvalue=False,
            progress_color="#38bdf8"
        )
        self.overlay_switch.pack(side="right")

        # Posição do Overlay
        row_ov_pos = ctk.CTkFrame(s_overlay, fg_color="transparent")
        row_ov_pos.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_ov_pos, text="Posição do HUD na Tela:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        self.overlay_pos_combo = ctk.CTkComboBox(
            row_ov_pos,
            values=["top_right", "bottom_center"],
            width=160,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.overlay_pos_combo.set(cfg.get("overlay_position", "top_right"))
        self.overlay_pos_combo.pack(side="right")

        # Botão Testar Overlay
        row_ov_btn = ctk.CTkFrame(s_overlay, fg_color="transparent")
        row_ov_btn.pack(fill="x", padx=16, pady=(6, 10))

        self.test_overlay_btn = ctk.CTkButton(
            row_ov_btn,
            text="✨ Testar Mini-HUD Flutuante Agora",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            border_color="#38bdf8",
            border_width=1,
            height=32,
            command=self._test_overlay_hud
        )
        self.test_overlay_btn.pack(fill="x")

        # --- SEÇÃO 5: MODO MÃOS LIVRES (WAKE WORD) ---
        s_wake = ctk.CTkFrame(scroll_settings, fg_color="#141824", border_color="#21283d", border_width=1, corner_radius=10)
        s_wake.pack(fill="x", pady=6)
        ctk.CTkLabel(s_wake, text="🎙️ MODO MÃOS LIVRES (WAKE WORD — \"EI SIDEKICK\")", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(10, 6))

        # Switch Ativar Wake Word
        row_w = ctk.CTkFrame(s_wake, fg_color="transparent")
        row_w.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_w, text="Ativar Detecção por Voz (\"Ei Sidekick\"): ", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")
        self.wake_var = tk.BooleanVar(value=cfg.get("enable_wake_word", False))
        self.wake_switch = ctk.CTkSwitch(
            row_w,
            text="Ativado",
            variable=self.wake_var,
            onvalue=True,
            offvalue=False,
            progress_color="#38bdf8"
        )
        self.wake_switch.pack(side="right")

        # Sensibilidade
        row_w_sens = ctk.CTkFrame(s_wake, fg_color="transparent")
        row_w_sens.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_w_sens, text="Sensibilidade do Microfone:", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(side="left")

        self.wake_sens_combo = ctk.CTkComboBox(
            row_w_sens,
            values=["alta", "media", "baixa"],
            width=140,
            fg_color="#1c2336",
            border_color="#2a3550"
        )
        self.wake_sens_combo.set(cfg.get("wake_word_sensitivity", "media"))
        self.wake_sens_combo.pack(side="right")

        # Botão Testar Reconhecimento
        row_w_btn = ctk.CTkFrame(s_wake, fg_color="transparent")
        row_w_btn.pack(fill="x", padx=16, pady=(6, 10))

        self.test_wake_btn = ctk.CTkButton(
            row_w_btn,
            text="🎙️ Testar Frase de Ativação (\"Ei Sidekick\")",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            border_color="#38bdf8",
            border_width=1,
            height=32,
            command=self._test_wake_phrase
        )
        self.test_wake_btn.pack(fill="x")

        # --- SEÇÃO 6: CHAVES DE API ---
        s4 = ctk.CTkFrame(scroll_settings, fg_color="#141824", border_color="#21283d", border_width=1, corner_radius=10)
        s4.pack(fill="x", pady=6)
        ctk.CTkLabel(s4, text="🔑 CHAVES DE API", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=16, pady=(10, 6))

        # Groq Key
        row_g = ctk.CTkFrame(s4, fg_color="transparent")
        row_g.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_g, text="Groq API Key (Grátis):", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(anchor="w")

        groq_box = ctk.CTkFrame(s4, fg_color="transparent")
        groq_box.pack(fill="x", padx=16, pady=(2, 6))

        self.groq_entry = ctk.CTkEntry(
            groq_box,
            show="*",
            placeholder_text="gsk_...",
            fg_color="#0a0c12",
            border_color="#1c2234"
        )
        self.groq_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.groq_entry.insert(0, cfg.get("groq_api_key", ""))

        self.groq_show = False
        def _toggle_groq_eye():
            self.groq_show = not self.groq_show
            self.groq_entry.configure(show="" if self.groq_show else "*")

        ctk.CTkButton(groq_box, text="👁️", width=36, fg_color="#1c2336", hover_color="#2b3652", command=_toggle_groq_eye).pack(side="right")

        # Gemini Key
        row_gem = ctk.CTkFrame(s4, fg_color="transparent")
        row_gem.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_gem, text="Gemini API Key (Opcional):", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#cbd5e1").pack(anchor="w")

        gem_box = ctk.CTkFrame(s4, fg_color="transparent")
        gem_box.pack(fill="x", padx=16, pady=(2, 10))

        self.gemini_entry = ctk.CTkEntry(
            gem_box,
            show="*",
            placeholder_text="AIza...",
            fg_color="#0a0c12",
            border_color="#1c2234"
        )
        self.gemini_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.gemini_entry.insert(0, cfg.get("gemini_api_key", ""))

        self.gem_show = False
        def _toggle_gem_eye():
            self.gem_show = not self.gem_show
            self.gemini_entry.configure(show="" if self.gem_show else "*")

        ctk.CTkButton(gem_box, text="👁️", width=36, fg_color="#1c2336", hover_color="#2b3652", command=_toggle_gem_eye).pack(side="right")

        # --- BOTÃO SALVAR ---
        save_btn = ctk.CTkButton(
            scroll_settings,
            text="💾  SALVAR E APLICAR CONFIGURAÇÕES",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=44,
            corner_radius=8,
            command=self._save_settings
        )
        save_btn.pack(fill="x", pady=(10, 14))

    def _test_overlay_hud(self):
        """Dispara uma exibição de teste do HUD overlay."""
        try:
            from src.ui.overlay import GameOverlay
            pos = self.overlay_pos_combo.get().strip()
            if not hasattr(self, '_test_overlay_instance') or not self._test_overlay_instance:
                self._test_overlay_instance = GameOverlay(enabled=True, position=pos)
            else:
                self._test_overlay_instance.set_position(pos)
                self._test_overlay_instance.set_enabled(True)
            self._test_overlay_instance.show_message(
                "E aí gamer! O HUD translúcido do Sidekick tá funcionando perfeitamente em cima da gameplay!",
                title="🎮 TESTE DE HUD OVERLAY",
                duration=5.0
            )
            self._log("✨ Exibindo mensagem de teste no HUD Overlay flutuante!", "info")
        except Exception as e:
            self._log(f"Erro ao testar HUD Overlay: {e}", "error")

    def _test_wake_phrase(self):
        """Dispara simulação da detecção da palavra de ativação."""
        self._log("🎙️ Testando reconhecimento de mãos livres: 'Ei Sidekick!'", "info")
        if self.test_voice_callback:
            self.test_voice_callback()
        if hasattr(self, '_test_overlay_instance') and self._test_overlay_instance:
            self._test_overlay_instance.show_message(
                "Palavra de ativação 'Ei Sidekick' funcionando! Pode falar normalmente durante o jogo.",
                title="🎙️ WAKE WORD ATIVADA",
                duration=4.5
            )
        messagebox.showinfo(
            "Modo Mãos Livres (Wake Word)",
            "Modo Mãos Livres pronto!\n\nQuando estiver jogando, basta dizer perto do microfone:\n• 'Ei Sidekick, onde eu acho ferro?'\n• ou 'Ei Sidekick!' e aguardar o bipe para falar."
        )

    def _on_personality_selected(self, selected_name: str):
        """Atualiza a descrição dinâmica e sugere a voz recomendada da personalidade."""
        pers_key = PERSONALITY_OPTIONS.get(selected_name, "parceira")
        meta = get_personality_meta(pers_key)
        if hasattr(self, 'pers_desc_lbl'):
            self.pers_desc_lbl.configure(text=meta.get("description", ""))

        # Sugere a voz correspondente
        rec_voice_code = meta.get("recommended_voice")
        if rec_voice_code in VOICE_MAP_REV and hasattr(self, 'voice_combo'):
            self.voice_combo.set(VOICE_MAP_REV[rec_voice_code])

    def _save_settings(self):
        """Coleta os dados da tela, grava no config.json e aplica em tempo real."""
        new_voice_key = self.voice_combo.get()
        new_voice = VOICE_OPTIONS.get(new_voice_key, "pt-BR-ThalitaMultilingualNeural")

        selected_pers_name = self.pers_combo.get()
        pers_key = PERSONALITY_OPTIONS.get(selected_pers_name, "parceira")

        try:
            interval = int(self.interval_combo.get())
        except ValueError:
            interval = 25

        new_config = {
            "push_to_talk_key": self.key_combo.get().strip().lower(),
            "input_method": self.method_combo.get().strip().lower(),
            "personality": pers_key,
            "voice": new_voice,
            "voice_rate": self.rate_combo.get().strip(),
            "voice_pitch": "+0Hz",
            "play_chimes": bool(self.chimes_var.get()),
            "chime_volume": round(float(self.vol_slider.get()), 2),
            "sentinel_mode_enabled": bool(self.sentinel_cfg_var.get()),
            "sentinel_interval_seconds": interval,
            "enable_overlay": bool(self.overlay_var.get()),
            "overlay_position": self.overlay_pos_combo.get().strip().lower(),
            "enable_wake_word": bool(self.wake_var.get()),
            "wake_word_sensitivity": self.wake_sens_combo.get().strip().lower(),
            "groq_api_key": self.groq_entry.get().strip(),
            "gemini_api_key": self.gemini_entry.get().strip(),
            "preferred_provider": "groq",
            "game_profile": "universal",
            "enable_screen_vision": True,
            "anti_cheat_protection": False
        }

        # Atualiza config local
        config_path = os.path.join(get_base_dir(), "config.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, ensure_ascii=False, indent=2)
            self.config_data = new_config
            self._log("💾 Configurações gravadas com sucesso no config.json!", "success")

            # Aplica no copiloto em execução se callback estiver disponível
            if self.reload_config_callback:
                self.reload_config_callback()
                self._log("⚡ Mudanças aplicadas ao Sidekick em tempo real!", "success")

            self.update_input_method("Windows Hotkey" if new_config["input_method"] == "windows_hotkey" else "Pynput")
            if "Personalidade" in self.status_labels:
                pers_short = PERSONALITY_PRESETS.get(pers_key, {}).get("name", "Amiga Gamer").split(" (")[0]
                self.status_labels["Personalidade"].configure(text=pers_short)
            if "Mãos Livres" in self.status_labels:
                self.status_labels["Mãos Livres"].configure(
                    text="Ativo" if new_config["enable_wake_word"] else "Inativo",
                    text_color="#34d399" if new_config["enable_wake_word"] else "#94a3b8"
                )
            messagebox.showinfo("Configurações Salvas", "Configurações salvas e aplicadas com sucesso!")
        except Exception as e:
            self._log(f"Erro ao salvar configurações: {e}", "error")
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{e}")

    def _toggle_run(self):
        """Alterna entre Iniciar e Parar."""
        if not self.is_running:
            self._start_sidekick()
        else:
            self._stop_sidekick()

    def _start_sidekick(self):
        """Inicia o Sidekick em background thread."""
        if self.is_running:
            return

        self.is_running = True
        self.main_btn.configure(
            text="⏹  PARAR SIDEKICK",
            fg_color="#ef4444",
            hover_color="#dc2626"
        )
        self.live_badge.configure(
            text="🟢 ONLINE",
            text_color="#34d399",
            fg_color="#064e3b"
        )
        self._update_status("Estado", "Rodando")
        self._log("🚀 Sidekick iniciado! Segure seu atalho no jogo para falar.", "info")
        self.status_bar.configure(text="Sidekick rodando em segundo plano • Ouvindo atalho")

        threading.Thread(target=self._run_sidekick_thread, daemon=True).start()

    def _run_sidekick_thread(self):
        """Thread que roda o Sidekick."""
        try:
            self.start_callback()
        except Exception as e:
            self._log(f"❌ Erro na execução: {e}", "error")
            self._on_sidekick_stopped()

    def _stop_sidekick(self):
        """Para o Sidekick de forma segura."""
        if not self.is_running:
            return

        self._log("⏹ Interrompendo escuta e tarefas de fundo...", "warning")
        try:
            self.stop_callback()
        except Exception as e:
            self._log(f"Aviso ao parar: {e}", "warning")
        self._on_sidekick_stopped()

    def _on_sidekick_stopped(self):
        """Atualiza a interface para estado Parado."""
        self.is_running = False
        self.main_btn.configure(
            text="▶  INICIAR SIDEKICK",
            fg_color="#10b981",
            hover_color="#059669"
        )
        self.live_badge.configure(
            text="⚪ OFFLINE",
            text_color="#94a3b8",
            fg_color="#181e2e"
        )
        self._update_status("Estado", "Parado")
        self.status_bar.configure(text="Sidekick em pausa • Pronto para iniciar")
        self._log("💤 Sidekick pausado com sucesso.", "info")

    def _test_voice(self):
        """Executa teste de voz em thread separada."""
        self._log("🔊 Testando síntese de voz...", "info")
        threading.Thread(target=self.test_voice_callback, daemon=True).start()

    def _toggle_sentinel(self):
        """Alterna modo sentinela."""
        self.sentinel_enabled = not self.sentinel_enabled
        status = "Ativo" if self.sentinel_enabled else "Inativo"
        self._update_status("Modo Sentinela", status)
        self._log(f"🔄 Modo Sentinela alterado para: {status}", "info")

    def _toggle_stealth(self):
        """Força modo stealth."""
        self.stealth_mode = self.stealth_var.get()
        status = "Ativo" if self.stealth_mode else "Inativo"
        self._update_status("Modo Stealth", status)
        self._log(f"🕵️ Modo Stealth: {status}", "warning" if self.stealth_mode else "info")

    def _refresh_wiki(self):
        """Dispara a sincronização manual da wiki para o jogo atual."""
        if not self.current_game or self.current_game == "Nenhum":
            self._log("Abra um jogo primeiro para baixar sua wiki específica.", "warning")
            return

        self._update_status("Wiki do Jogo", "Baixando...")
        self._log(f"📚 Buscando e compilando wiki para '{self.current_game}'...", "info")

        try:
            from src.ai.wiki_knowledge import WikiKnowledgeManager
            groq_c = self._get_ai_client("groq")
            gem_c = self._get_ai_client("gemini")
            wm = WikiKnowledgeManager(groq_client=groq_c, gemini_client=gem_c)

            def on_done(game, success):
                def _ui_cb():
                    status = "Carregada" if success else "Pendente"
                    self._update_status("Wiki do Jogo", status)
                    if success:
                        self._log(f"✅ Wiki de '{game}' pronta e atualizada!", "success")
                    else:
                        self._log(f"⚠️ Não foi possível compilar a wiki de '{game}'.", "warning")
                self.root.after(0, _ui_cb)

            wm.ensure_game_wiki_async(self.current_game, on_complete=on_done)
        except Exception as e:
            self._log(f"Erro ao acessar gerenciador de wiki: {e}", "error")

    def _update_status(self, key: str, value: str):
        """Atualiza badge e cores de status."""
        if key in self.status_labels:
            badge = self.status_labels[key]
            badge.configure(text=value)

            if value in ("Ativo", "Rodando", "Carregada"):
                badge.configure(text_color="#34d399", fg_color="#064e3b")
            elif value in ("Inativo", "Parado"):
                badge.configure(text_color="#94a3b8", fg_color="#1c2336")
            elif key == "Modo Stealth" and value == "Ativo":
                badge.configure(text_color="#f59e0b", fg_color="#451a03")
            elif key == "Jogo Detectado" and value != "Nenhum":
                badge.configure(text_color="#38bdf8", fg_color="#082f49")
            else:
                badge.configure(text_color="#38bdf8", fg_color="#1c2336")

    def _log(self, message: str, level: str = "info"):
        """Adiciona mensagens com timestamp ao console."""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }.get(level, "•")

        entry = f"[{timestamp}] {prefix} {message}\n"

        def _append():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", entry)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")

        if threading.current_thread() is threading.main_thread():
            _append()
        else:
            self.root.after(0, _append)

    def _schedule_game_check(self):
        """Verifica periodicamente em segundo plano se há algum jogo em execução."""
        def _check():
            try:
                from src.vision.game_detector import detect_running_game
                game, strict = detect_running_game()
                current = self.current_game if self.current_game != "Nenhum" else ""
                if game != current:
                    if threading.current_thread() is threading.main_thread():
                        self.update_game_detected(game, strict)
                    else:
                        self.root.after(0, lambda: self.update_game_detected(game, strict))
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(3500, self._schedule_game_check)
        except Exception:
            pass

    def _on_closing(self):
        """Encerra a aplicação de forma limpa e imediata."""
        if self.is_running:
            try:
                self._stop_sidekick()
            except Exception:
                pass
        self.root.destroy()
        os._exit(0)

    def _get_ai_client(self, provider: str = "groq"):
        """Instancia cliente Groq ou Gemini a partir das configurações ou variáveis de ambiente."""
        key = self.config_data.get(f"{provider}_api_key", "").strip() or os.getenv(f"{provider.upper()}_API_KEY", "").strip()
        if not key:
            return None
        try:
            if provider == "groq":
                from groq import Groq
                return Groq(api_key=key)
            elif provider == "gemini":
                from google import genai
                return genai.Client(api_key=key)
        except Exception:
            pass
        return None

    def update_game_detected(self, game_name: str, anti_cheat_strict: bool):
        """Atualiza detecção de jogo na UI."""
        self.current_game = game_name if game_name else "Nenhum"
        self._update_status("Jogo Detectado", self.current_game)
        if game_name:
            self._log(f"🎮 Jogo detectado: {game_name}", "info")
            try:
                from src.ai.wiki_knowledge import WikiKnowledgeManager
                groq_c = self._get_ai_client("groq")
                gem_c = self._get_ai_client("gemini")
                wm = WikiKnowledgeManager(groq_client=groq_c, gemini_client=gem_c)
                if wm.has_wiki(game_name):
                    self._update_status("Wiki do Jogo", "Carregada")
                    self._log(f"📚 Conhecimento da Wiki de '{game_name}' carregado!", "success")
                else:
                    self._update_status("Wiki do Jogo", "Baixando...")
                    self._log(f"📚 Baixando e compilando guia tático de '{game_name}' pela primeira vez...", "info")

                    def on_done(g, success):
                        def _ui_update():
                            if success:
                                self._update_status("Wiki do Jogo", "Carregada")
                                self._log(f"✅ Wiki de '{g}' baixada e salva em wikis/!", "success")
                            else:
                                self._update_status("Wiki do Jogo", "Pendente")
                                self._log(f"⚠️ Não foi possível compilar a wiki de '{g}'.", "warning")
                        self.root.after(0, _ui_update)

                    wm.ensure_game_wiki_async(game_name, on_complete=on_done)
            except Exception as e:
                self._log(f"Erro no gerenciador de wiki: {e}", "error")
        else:
            self._update_status("Wiki do Jogo", "Pronta")

    def update_input_method(self, method: str):
        """Atualiza método de input."""
        self._update_status("Input Method", method)

    def set_running(self, running: bool):
        """Define estado externamente."""
        if running:
            self._start_sidekick()
        else:
            self._on_sidekick_stopped()

    def run(self):
        """Inicia o loop principal do CustomTkinter."""
        self._log("Bem-vindo ao Sidekick! Clique em 'Iniciar' para começar.", "info")
        self._schedule_game_check()
        self.root.mainloop()


def create_gui(
    start_callback,
    stop_callback,
    test_voice_callback,
    reload_config_callback: Optional[Callable] = None
) -> SidekickGUI:
    """Factory function para criar a GUI moderna com suporte a abas e reload de configurações."""
    return SidekickGUI(start_callback, stop_callback, test_voice_callback, reload_config_callback)

"""Gerenciador de Memória de Longo Prazo do Sidekick com limites inteligentes de tokens."""

import json
import os
import re
import sys
import threading
from typing import Dict, Any, List

from src.utils.paths import get_memory_path

MEMORY_FILE_PATH = get_memory_path()
MAX_REMINDERS = 10
MAX_DEFEATED_BOSSES = 50
MAX_RULES = 15


DEFAULT_MEMORY: Dict[str, Any] = {
    "player_profile": {
        "playstyle": "Prefere combate dinâmico e direto",
        "notes": ""
    },
    "games": {
        "dark_souls_1": {
            "current_weapon": "",
            "defeated_bosses": [],
            "last_progress": ""
        },
        "albion_online": {
            "home_city": "",
            "build_focus": "",
            "last_progress": ""
        }
    },
    "reminders": [],
    "custom_rules": []
}


class LongTermMemory:
    def __init__(self, filepath: str = MEMORY_FILE_PATH):
        self.filepath = filepath
        self._lock = threading.Lock()
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Carrega a memória persistente do disco ou cria a padrão."""
        if os.path.exists(self.filepath) and os.path.getsize(self.filepath) > 0:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Mescla garantindo que chaves padrão existam
                    result = json.loads(json.dumps(DEFAULT_MEMORY))
                    result.update(loaded)
                    return result
            except Exception as e:
                print(f"[Memória]: Erro ao ler {self.filepath}, usando padrão: {e}")
        return json.loads(json.dumps(DEFAULT_MEMORY))

    def save(self):
        """Salva a memória no disco de forma segura."""
        with self._lock:
            try:
                # Aplica limites rígidos antes de salvar
                if len(self.data.get("reminders", [])) > MAX_REMINDERS:
                    self.data["reminders"] = self.data["reminders"][-MAX_REMINDERS:]

                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[Memória]: Erro ao salvar {self.filepath}: {e}")

    def get_context_for_prompt(self) -> str:
        """Gera um bloco de texto compacto para injetar no System Prompt."""
        with self._lock:
            lines = ["MEMÓRIA DE LONGO PRAZO DO SEU PARCEIRO (O QUE VOCÊ JÁ SABE SOBRE ELE):"]

            # Perfil do jogador
            profile = self.data.get("player_profile", {})
            if profile.get("playstyle"):
                lines.append(f"- Estilo do Jogador: {profile['playstyle']}")
            if profile.get("notes"):
                lines.append(f"- Preferências: {profile['notes']}")

            # Jogos
            games = self.data.get("games", {})
            for game_name, info in games.items():
                game_summary = []
                if info.get("current_weapon"):
                    game_summary.append(f"Arma: {info['current_weapon']}")
                if info.get("defeated_bosses"):
                    bosses = ", ".join(info["defeated_bosses"][-6:])
                    game_summary.append(f"Últimos chefes mortos: {bosses}")
                if info.get("last_progress"):
                    game_summary.append(f"Progresso recente: {info['last_progress']}")

                if game_summary:
                    lines.append(f"- {game_name.replace('_', ' ').title()}: {'; '.join(game_summary)}")

            # Lembretes
            reminders = self.data.get("reminders", [])
            if reminders:
                lines.append(f"- Lembretes Ativos: {'; '.join(reminders[-MAX_REMINDERS:])}")

            # Regras e Ordens do Jogador
            rules = self.data.get("custom_rules", [])
            if rules:
                lines.append("\nREGRAS E ORDENS MANDATÓRIAS DO JOGADOR (OBEDEÇA ESTRITAMENTE):")
                for r in rules[-MAX_RULES:]:
                    lines.append(f"- {r}")

            return "\n".join(lines)

    def add_reminder(self, text: str):
        """Adiciona um lembrete com rotação automática."""
        with self._lock:
            reminders = self.data.setdefault("reminders", [])
            reminders.append(text.strip())
            if len(reminders) > MAX_REMINDERS:
                self.data["reminders"] = reminders[-MAX_REMINDERS:]
        self.save()

    def add_rule(self, rule_text: str):
        """Adiciona uma regra ou ordem de comportamento com limite máximo."""
        with self._lock:
            rules = self.data.setdefault("custom_rules", [])
            clean_rule = rule_text.strip()
            if clean_rule and clean_rule not in rules:
                rules.append(clean_rule)
                if len(rules) > MAX_RULES:
                    self.data["custom_rules"] = rules[-MAX_RULES:]
        self.save()

    def update_game(self, game_id: str, weapon: str = None, new_boss: str = None, progress: str = None):
        """Atualiza o estado de um jogo específico."""
        with self._lock:
            games = self.data.setdefault("games", {})
            game = games.setdefault(game_id, {
                "current_weapon": "",
                "defeated_bosses": [],
                "last_progress": ""
            })

            if weapon:
                game["current_weapon"] = weapon
            if new_boss and new_boss not in game.get("defeated_bosses", []):
                bosses = game.setdefault("defeated_bosses", [])
                bosses.append(new_boss)
                if len(bosses) > MAX_DEFEATED_BOSSES:
                    game["defeated_bosses"] = bosses[-MAX_DEFEATED_BOSSES:]
            if progress:
                game["last_progress"] = progress

        self.save()

    def update_profile(self, playstyle: str = None, notes: str = None):
        """Atualiza as preferências do jogador."""
        with self._lock:
            prof = self.data.setdefault("player_profile", {})
            if playstyle:
                prof["playstyle"] = playstyle
            if notes:
                prof["notes"] = notes
        self.save()


def _normalize_game_id(game_name: str) -> str:
    if not game_name:
        return "geral"
    g = str(game_name).lower().strip()
    if "dark" in g or "souls" in g:
        return "dark_souls_1"
    if "albion" in g:
        return "albion_online"
    if "elden" in g:
        return "elden_ring"
    return re.sub(r"[^a-z0-9_]+", "_", g)


def background_memory_extractor(groq_client, memory: LongTermMemory, user_text: str, assistant_text: str):
    """Executado em segundo plano para extrair conquistas, armas e lembretes da conversa."""
    if not groq_client or not user_text:
        return

    prompt = f"""Analise este diálogo gamer:
Jogador: "{user_text}"
Copiloto: "{assistant_text}"

Se o diálogo mencionar:
- Um chefe/boss derrotado (ex: Gargoyles, Capra Demon)
- Uma arma nova equipada ou usada (ex: Zweihander, Espada Larga)
- Um lembrete explícito pedido pelo jogador ("anota aí", "lembra de")
- Uma ordem, comando ou regra de comportamento ("não faça X", "não fale de Y", "sempre me avisa quando Z")
- O progresso do jogo

Retorne APENAS um objeto JSON válido (sem texto adicional):
{{
  "game": "dark_souls_1" ou "albion_online" ou null,
  "defeated_boss": "nome do chefe" ou null,
  "current_weapon": "nome da arma" ou null,
  "progress_summary": "resumo do progresso" ou null,
  "new_reminder": "lembrete" ou null,
  "new_rule": "regra de comportamento ordenada pelo jogador" ou null
}}
Se não houver nada importante, retorne: {{"game": null}}
"""
    try:
        completion = groq_client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": "Você é um assistente que extrai fatos de jogos e responde APENAS JSON puro, sem blocos de texto ao redor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=180,
        )
        raw_resp = completion.choices[0].message.content.strip()

        # Extrai JSON por regex
        match = re.search(r"\{.*\}", raw_resp, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            raw_game = data.get("game")
            if raw_game and raw_game != "null":
                game_id = _normalize_game_id(raw_game)
                memory.update_game(
                    game_id=game_id,
                    weapon=data.get("current_weapon"),
                    new_boss=data.get("defeated_boss"),
                    progress=data.get("progress_summary")
                )
            if data.get("new_reminder"):
                memory.add_reminder(data["new_reminder"])
            if data.get("new_rule"):
                memory.add_rule(data["new_rule"])

    except Exception:
        pass

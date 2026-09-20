"""Motor de Conhecimento e Guias Táticos (Wiki Packs) para jogos."""

import json
import os
import re
import sys
import threading
from typing import Dict, Any, Optional


try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


from src.utils.paths import get_wikis_dir

WIKIS_DIR = get_wikis_dir()


def slugify(text: str) -> str:
    """Converte nome do jogo para formato de arquivo seguro."""
    text = text.lower().strip()
    text = re.sub(r'[\s\-]+', '_', text)
    text = re.sub(r'[^a-z0-9_]', '', text)
    return text or "game"


# Base inicial pré-instalada de alta precisão para jogos comuns
SEEDED_WIKIS: Dict[str, Dict[str, Any]] = {
    "children_of_morta": {
        "game_name": "Children of Morta",
        "genre": "Action RPG / Roguelite",
        "overview": (
            "RPG de ação com foco na família Bergson combatendo a Corrupção. "
            "A chave de progressão é alternar entre todos os personagens para desbloquear "
            "traços de família passivos que fortalecem todos os membros simultaneamente."
        ),
        "characters": [
            "John (Pai): Escudo e espada, tanque corpo a corpo. Use o escudo para bloquear dano e refletir projéteis.",
            "Linda (Filha): Arqueira de longo alcance. Pode atirar andando com habilidade e manter distância segura.",
            "Kevin (Filho mais novo): Adagas gêmeas, furtividade e extrema velocidade de ataque. Excelente DPS contra alvos únicos.",
            "Mark (Filho mais velho): Monge lutador corpo a corpo. Usa garras para puxar inimigos e combate em área.",
            "Lucy (Filha mais jovem): Maga de fogo. Causa imenso dano parada, usando engodos e tornados.",
            "Joey (Primo): Marreta colossal de duas mãos. Causa dano em área massivo e atordoa grupos inteiros."
        ],
        "tactical_tips": [
            "Oficina do Tio Ben: Priorize upar Dano de Ataque e Vida Máxima primeiro.",
            "Livro de Rea: Aumente Ganho de Ouro (Morv) e Chance de Esquiva assim que disponível.",
            "Relíquias Divinas: Guarde relíquias ativas com dano em área para ondas de inimigos grandes.",
            "Fadiga de Corrupção: Quando um personagem ficar corrompido (vida reduzida), jogue com outro para que ele se cure na mansão.",
            "Boss Spider Queen (Cavernas da Seda): Mantenha distância, desvie das teias no chão e elimine as aranhas menores imediatamente."
        ]
    },
    "albion_online": {
        "game_name": "Albion Online",
        "genre": "MMORPG Sandbox",
        "overview": (
            "MMO sandbox sem classes fixas onde 'você é o que você veste'. "
            "A economia é 100% movida a jogadores com zonas seguras (Azul/Amarela) "
            "e zonas de Full Loot PvP (Vermelha/Preta)."
        ),
        "mechanics": [
            "Destiny Board (Painel do Destino): Foque em especializar 1 arma e 1 armadura até nível 100 para ganhar bônus imenso de IP (Item Power).",
            "Cidades e Biomas: Fort Sterling (Neve/Minério), Thetford (Pântano/Fibra), Lymhurst (Floresta/Madeira), Bridgewatch (Deserto/Pele), Martlock (Montanha/Pedra).",
            "Armaduras: Tecido dá mais dano bônus (+50%), Couro dá dano balanceado e defesa (+25%), Placas dá máxima defesa e controle de grupo."
        ],
        "tactical_tips": [
            "Build Solos Fáceis: Machado de Batalha (Battleaxe) + Casaco de Mercenário (Mercenary Jacket) + Tocha para sustento infinito de vida.",
            "Build PvP de Fuga: Botas de Andarilho ou Soldado, Capuz de Caçador (Hunter Hood), Capa de Fort Sterling para purgar atordoamentos.",
            "Zonas Pretas: Sempre tenha montaria por perto (mantenha-se dentro do círculo verde dela para não perder tempo subindo de volta se atacado)."
        ]
    },
    "dark_souls_1": {
        "game_name": "Dark Souls 1",
        "genre": "Action RPG / Soulslike",
        "overview": "Clássico Soulslike de Lordran focado em posicionamento, gerenciamento de estamina e esquiva.",
        "tactical_tips": [
            "Softcaps de atributos: 40 de Vitalidade, 40 de Fortitude, 40 de Força e 40 de Destreza.",
            "Aparar (Parry): Crucial contra Cavaleiros Negros, Homens-Serpente e o Lorde Gwyn.",
            "Corte de Caudas: Gargoyles (Machado da Cauda), Gaping Dragon (Machado Dragão), Seath (Espada da Luz da Lua).",
            "Ornstein e Smough: Mate primeiro Ornstein para facilitar a segunda fase com Smough gigante usando os pilares."
        ]
    },
    "elden_ring": {
        "game_name": "Elden Ring",
        "genre": "Open World Action RPG",
        "overview": "RPG de mundo aberto nas Terras Intermédias com mecânica de pulo, montaria e Cinzas de Invocação.",
        "tactical_tips": [
            "Vigor é prioridade: Suba Vigor para pelo menos 40 até o meio do jogo e 60 no fim do jogo.",
            "Quebra de Postura: Ataques pesados pulando (Jump Heavy Attacks) quebram a postura da maioria dos chefes para crítico.",
            "Margit: Use a Algema de Margit (comprada do Patches) para imobilizá-lo duas vezes na fase 1.",
            "Malenia: Fraca a Sangramento e Congelamento. O ataque Dança das Aves d'Água (Waterfowl) pode ser esquivado correndo da 1ª saraivada e rolando para frente na 2ª e 3ª."
        ]
    },
    "hollow_knight": {
        "game_name": "Hollow Knight",
        "genre": "Metroidvania / Action Adventure",
        "overview": (
            "Aclamado metroidvania 2D pelas ruínas do reino esquecido de Hallownest. "
            "Combate fluido com o Ferrão (Nail), saltos precisos, feitiços de Alma e Amuletos."
        ),
        "mechanics": [
            "Pogo Jump: Golpear para baixo com o Ferrão em cima de espinhos, serras e carapaças ressalta você no ar, essencial para alcançar áreas secretas.",
            "Foco de Alma: Mantenha pressionado o botão de feitiço quando estiver em local seguro para curar 1 máscara consumindo alma.",
            "Amuletos (Charms): Equipados nos bancos. Atenção: equipar além do limite causa Sobrecarregado (Overcharmed), dobrando todo dano recebido."
        ],
        "tactical_tips": [
            "Aprimoramento do Ferrão: Colete Minério Pálido (Pale Ore) na Bacia Antiga, Pico de Cristal e Coliseu para forjar Ferrão Aguçado com o Ferreiro em Cidade das Lágrimas.",
            "Build Meta de Amuletos: Marca do Orgulho (Mark of Pride para maior alcance), Força Inquebrável (+50% dano), Pedra do Xamã (Shaman Stone - magias colossais).",
            "Hornet (Verdejante): Não seja guloso; ataque 1 ou 2 vezes após os ataques dela e recue. Salte por cima do arremesso da agulha.",
            "Recuperar Sombra: Após morrer, derrote sua Sombra no local da morte para recuperar todo seu Geo e consertar o vaso de Alma rachado."
        ]
    },
    "dead_cells": {
        "game_name": "Dead Cells",
        "genre": "Roguelite / Metroidvania (Roguevania)",
        "overview": (
            "Roguevania frenético em uma ilha amaldiçoada em constante mutação. "
            "Combate veloz com esquiva por rolamento (I-frames), parry com escudos e "
            "coleta de Células para desbloquear armas e mutações permanentes."
        ),
        "mechanics": [
            "Rolamento e I-frames: A esquiva concede invulnerabilidade temporária, atravessando inimigos e ataques terrestres.",
            "Parry de Escudo: Bloquear golpes no último segundo atordoa o atacante e devolve projéteis inimigos com dano ampliado.",
            "Monocolor em Pergaminhos (Brutalidade, Tática ou Sobrevivência): Concentre TODOS os pergaminhos possíveis em uma única cor para escalonamento exponencial de DPS.",
            "Portas Temporizadas e Sem Hit: Eliminar 30/60 inimigos sem levar dano em cada bioma abre portas com itens e células valiosas."
        ],
        "tactical_tips": [
            "Restauração de Vida (Rally): Ao tomar dano, atacar imediatamente recupera parte da vida perdida da barra alaranjada.",
            "Build Brutalidade de Sangramento/Veneno: Espada com bônus de dano a inimigos sangrando combinada com Kunai ou Armadilhas sinérgicas.",
            "Mão do Rei (Hand of the King): Pule nas pequenas plataformas móveis quando ele for disparar o golpe sísmico de tela inteira.",
            "Células do Chefe: Ao zerar, equipe a Boss Cell no tubo do primeiro salão para acessar novos caminhos e portas de biomas."
        ]
    }
}


class WikiKnowledgeManager:
    """Gerencia guias locais e busca em tempo real para qualquer jogo."""

    def __init__(self, groq_client=None, gemini_client=None):
        self.groq_client = groq_client
        self.gemini_client = gemini_client
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._init_storage()

    def _init_storage(self):
        """Cria pasta de wikis e grava os packs iniciais pré-configurados."""
        os.makedirs(WIKIS_DIR, exist_ok=True)
        for slug, data in SEEDED_WIKIS.items():
            filepath = os.path.join(WIKIS_DIR, f"{slug}.json")
            if not os.path.exists(filepath):
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"[Wiki]: Erro ao gravar wiki inicial de {slug}: {e}")

    def get_game_wiki(self, game_name: str) -> Optional[Dict[str, Any]]:
        """Recupera a wiki local do jogo especificado."""
        if not game_name or game_name.strip() == "" or game_name.lower() == "nenhum":
            return None

        slug = slugify(game_name)
        with self._lock:
            if slug in self.cache:
                return self.cache[slug]

            filepath = os.path.join(WIKIS_DIR, f"{slug}.json")
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.cache[slug] = data
                        return data
                except Exception as e:
                    print(f"[Wiki]: Erro ao ler wiki {filepath}: {e}")

        return None

    def has_wiki(self, game_name: str) -> bool:
        """Verifica se já existe wiki compilada para o jogo."""
        if not game_name:
            return False
        slug = slugify(game_name)
        filepath = os.path.join(WIKIS_DIR, f"{slug}.json")
        return os.path.exists(filepath) or slug in self.cache

    def ensure_game_wiki_async(self, game_name: str, on_complete: Optional[callable] = None):
        """Garante que a wiki do jogo exista, gerando automaticamente em background se necessário."""
        if not game_name or self.has_wiki(game_name):
            if on_complete:
                on_complete(game_name, True)
            return

        def _worker():
            success = self._fetch_or_generate_wiki(game_name)
            if on_complete:
                on_complete(game_name, success)

        threading.Thread(target=_worker, daemon=True).start()

    def _fetch_or_generate_wiki(self, game_name: str) -> bool:
        """Gera um pacote de conhecimento estruturado para o jogo via IA e salva no disco."""
        slug = slugify(game_name)
        filepath = os.path.join(WIKIS_DIR, f"{slug}.json")

        if not self.groq_client and not self.gemini_client:
            return False

        try:
            print(f"[Wiki]: Baixando e compilando guia tatico para '{game_name}' em segundo plano...")
        except Exception:
            pass

        system_prompt = (
            "Você é um especialista enciclopédico de videogames. "
            "Gere uma ficha tática completa, densa e precisa em formato JSON válido sobre o jogo solicitado. "
            "O JSON deve ter EXATAMENTE esta estrutura:\n"
            "{\n"
            '  "game_name": "Nome Oficial",\n'
            '  "genre": "Gênero do jogo",\n'
            '  "overview": "Visão geral das mecânicas centrais e objetivos (máximo 3 frases)",\n'
            '  "tactical_tips": ["dica tática essencial 1", "dica 2", "dica 3", "dica 4", "dica 5"],\n'
            '  "bosses_and_secrets": ["segredo ou tática de boss 1", "tática 2", "tática 3"],\n'
            '  "meta_builds": ["melhor combinação de habilidades/armas 1", "combinação 2"]\n'
            "}\n"
            "Retorne APENAS o JSON válido sem texto adicional antes ou depois."
        )

        raw_text = None
        # Opção 1: Groq com JSON mode e max_tokens expandido
        if self.groq_client:
            models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
            for model_id in models_to_try:
                try:
                    kwargs = {
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Gere o guia tático de alta precisão para o jogo: '{game_name}'"}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2500,
                    }
                    # Ativa modo JSON estruturado
                    try:
                        kwargs["response_format"] = {"type": "json_object"}
                    except Exception:
                        pass

                    completion = self.groq_client.chat.completions.create(**kwargs)
                    raw_text = completion.choices[0].message.content.strip()
                    if raw_text:
                        break
                except Exception as err:
                    try:
                        print(f"[Wiki]: Falha no modelo {model_id} para {game_name}: {err}")
                    except Exception:
                        pass
                    continue

        # Opção 2: Gemini
        if not raw_text and self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[f"{system_prompt}\n\nJogo solicitado: '{game_name}'"]
                )
                if response and response.text:
                    raw_text = response.text.strip()
            except Exception as gem_err:
                try:
                    print(f"[Wiki]: Falha no Gemini para {game_name}: {gem_err}")
                except Exception:
                    pass

        if not raw_text:
            return False

        try:
            # Limpeza robusta de fences e extração do bloco JSON
            clean_json = raw_text.strip()
            if "```" in clean_json:
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json, flags=re.MULTILINE)
                clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE)

            # Localiza o objeto JSON mais externo
            json_match = re.search(r"(\{.*\})", clean_json, re.DOTALL)
            if json_match:
                clean_json = json_match.group(1)

            # Corrige vírgulas sobrando antes de fechamento de chaves ou colchetes
            clean_json = re.sub(r",\s*([\}\]])", r"\1", clean_json)

            data = json.loads(clean_json)

            os.makedirs(WIKIS_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            with self._lock:
                self.cache[slug] = data

            try:
                print(f"[Wiki]: Guia de '{game_name}' gerado e salvo com sucesso em {filepath}!")
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                print(f"[Wiki]: Erro ao gravar JSON de {game_name}: {e}")
            except Exception:
                pass
            return False

    def get_prompt_context(self, game_name: str, user_query: str = "") -> str:
        """Formata o conhecimento da wiki de forma cirúrgica para injeção no prompt do Sidekick."""
        wiki = self.get_game_wiki(game_name)
        if not wiki:
            return ""

        parts = [f"CONHECIMENTO ENCICLOPÉDICO DO JOGO ({wiki.get('game_name', game_name)}):"]
        if "overview" in wiki:
            parts.append(f"• Resumo: {wiki['overview']}")

        if "characters" in wiki and wiki["characters"]:
            parts.append("• Personagens e Habilidades:\n  " + "\n  ".join([f"- {c}" for c in wiki["characters"][:6]]))

        if "mechanics" in wiki and wiki["mechanics"]:
            parts.append("• Mecânicas Centrais:\n  " + "\n  ".join([f"- {m}" for m in wiki["mechanics"][:5]]))

        if "tactical_tips" in wiki and wiki["tactical_tips"]:
            parts.append("• Dicas Táticas Essenciais:\n  " + "\n  ".join([f"- {t}" for t in wiki["tactical_tips"][:5]]))

        if "bosses_and_secrets" in wiki and wiki["bosses_and_secrets"]:
            parts.append("• Chefes e Segredos:\n  " + "\n  ".join([f"- {b}" for b in wiki["bosses_and_secrets"][:4]]))

        if "meta_builds" in wiki and wiki["meta_builds"]:
            parts.append("• Builds e Equipamentos Meta:\n  " + "\n  ".join([f"- {m}" for m in wiki["meta_builds"][:4]]))

        return "\n".join(parts)

"""Cérebro do Sidekick: raciocínio e geração de respostas para qualquer jogo."""

import os
import threading
from typing import List, Dict
from src.ai.personality import build_personality_prompt
from src.ai.memory import LongTermMemory, background_memory_extractor
from src.ai.wiki_knowledge import WikiKnowledgeManager


class SidekickBrain:
    def __init__(self, groq_client=None, gemini_client=None, memory: LongTermMemory = None, wiki_manager: WikiKnowledgeManager = None, max_history=6, personality: str = "parceira"):
        self.groq_client = groq_client
        self.gemini_client = gemini_client
        self.memory = memory or LongTermMemory()
        self.wiki_manager = wiki_manager or WikiKnowledgeManager(groq_client=self.groq_client, gemini_client=self.gemini_client)
        self.max_history = max_history
        self.personality = personality or "parceira"
        self.history: List[Dict[str, str]] = []

    def clear_history(self):
        self.history = []

    def think_and_respond(self, user_question: str, image_data: str = None, detected_game: str = None, anti_cheat_strict: bool = False) -> str:
        """Processa a dúvida do jogador (e imagem da tela, se houver) e retorna a resposta da Sidekick em texto falado."""
        if not user_question or not user_question.strip():
            return "Opa, não deu pra te ouvir direito, fala de novo aí!"

        # Se não houver cliente configurado
        if not self.groq_client and not self.gemini_client:
            return (
                "E aí! Tô aqui na escuta, mas lembra de colocar sua chave gratuita "
                "do Groq ou Gemini no arquivo config.json pra gente começar a jogar junto!"
            )

        # Monta o prompt do sistema enriquecido com a personalidade, memória de longo prazo e wiki do jogo
        base_prompt = build_personality_prompt(self.personality)
        memory_context = self.memory.get_context_for_prompt()
        wiki_context = ""
        if detected_game and self.wiki_manager:
            wiki_context = self.wiki_manager.get_prompt_context(detected_game, user_question)
            if wiki_context:
                wiki_context = f"\n\n{wiki_context}"

        system_prompt_with_memory = f"{base_prompt}\n\n{memory_context}{wiki_context}"

        # Contexto do jogo ativo detectado pelo executável
        game_hint = f" [Atenção: O executável do jogo em execução no PC do jogador é '{detected_game}']" if detected_game else ""
        text_content = f"{user_question}\n{game_hint}" if game_hint else user_question

        # FASE 1: TENTATIVA COM VISÃO (se houver captura de tela)
        if image_data:
            vision_user_content = [
                {"type": "text", "text": f"O jogador fez a seguinte pergunta enquanto olha para a tela:{game_hint}\n'{user_question}'"},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]

            # 1.1: Groq Vision (Qwen)
            if self.groq_client:
                try:
                    messages = [{"role": "system", "content": system_prompt_with_memory}] + self.history + [{"role": "user", "content": vision_user_content}]
                    completion = self.groq_client.chat.completions.create(
                        model="qwen/qwen3.8-27b",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=300,
                    )
                    answer = completion.choices[0].message.content.strip()
                    if answer:
                        self._record_and_extract_memory(user_question, answer)
                        return answer
                except Exception:
                    # Falha de visão (ex: 429 rate limit ou timeout) -> prossegue para fallback
                    pass

            # 1.2: Gemini Vision
            if self.gemini_client:
                try:
                    import base64
                    raw_b64 = image_data.split(",", 1)[1] if "," in image_data else image_data
                    img_bytes = base64.b64decode(raw_b64)
                    contents = [system_prompt_with_memory]
                    for msg in self.history:
                        contents.append(f"{msg['role']}: {msg['content']}")
                    contents.append(f"user: {user_question}")
                    contents.append({"mime_type": "image/jpeg", "data": img_bytes})

                    response = self.gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                    )
                    if response and response.text and response.text.strip():
                        answer = response.text.strip()
                        self._record_and_extract_memory(user_question, answer)
                        return answer
                except Exception:
                    pass

        # FASE 2: RESPOSTA EM MODO TEXTO (Fallback garantido e ultra-rápido)
        # Se a visão falhar, tiver limite de taxa ou não houver imagem, responde via texto com o contexto do jogo
        if self.groq_client:
            text_models = [
                ("groq/compound-mini", 350),
                ("groq/compound", 350),
                ("openai/gpt-oss-120b", 1200),
                ("openai/gpt-oss-20b", 1200),
                ("qwen/qwen3.8-27b", 350),
            ]
            for model_id, max_tok in text_models:
                try:
                    messages = [{"role": "system", "content": system_prompt_with_memory}] + self.history + [{"role": "user", "content": text_content}]
                    completion = self.groq_client.chat.completions.create(
                        model=model_id,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=max_tok,
                    )
                    answer = completion.choices[0].message.content.strip()
                    if answer:
                        self._record_and_extract_memory(user_question, answer)
                        return answer
                except Exception:
                    continue

        if self.gemini_client:
            try:
                contents = [system_prompt_with_memory]
                for msg in self.history:
                    contents.append(f"{msg['role']}: {msg['content']}")
                contents.append(f"user: {text_content}")

                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                )
                if response and response.text and response.text.strip():
                    answer = response.text.strip()
                    self._record_and_extract_memory(user_question, answer)
                    return answer
            except Exception:
                pass

        return "Opa, deu um lag na minha conexão aqui! Tenta perguntar de novo em alguns segundos!"

    def _record_and_extract_memory(self, user_question: str, answer: str):
        """Salva a conversa no histórico e dispara a extração assíncrona de memória."""
        self.history.append({"role": "user", "content": user_question})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        if self.groq_client and hasattr(self, "memory") and self.memory:
            threading.Thread(
                target=background_memory_extractor,
                args=(self.groq_client, self.memory, user_question, answer),
                daemon=True
            ).start()

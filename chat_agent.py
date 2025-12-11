# chat_agent.py

# -*- coding: utf-8 -*-
from groq import Groq
from dotenv import load_dotenv
import os
import base64
import json
import random 
from enum import Enum 

# --- Importations des définitions de jeu ---
from enums_and_roles import Camp, NightAction, Role 

# --- Dépendance de Player (mockée pour éviter la boucle d'importation) ---
class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.is_human = is_human
        self.role = None
        self.is_alive = True
        self.has_kill_potion = False 
        self.has_life_potion = False 
    def assign_role(self, role):
        self.role = role

# --------------------------------------------------------

class ChatAgent(Player):
    """
    Représente un joueur IA. Gère l'historique isolé, la personnalité et l'API LLM.
    """
    
    VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct" 
    
    def __init__(self, name, personality_context_path, is_human=False):
        
        super().__init__(name, is_human)
        
        if "GROQ_KEY" not in os.environ:
             raise EnvironmentError("GROQ_KEY non trouvée. Assurez-vous d'avoir un fichier .env.")
             
        self.client = Groq(api_key=os.environ["GROQ_KEY"])
        self.personality_context_path = personality_context_path
        self.history = [] 
        self.large_language_model = "llama-3.3-70b-versatile" 
        self.initiate_history()

    # --- SETUP & UTILITAIRES ---

    def initiate_history(self):
        """Initialise/réinitialise l'historique avec le contexte de personnalité."""
        personality_context = self._read_file(self.personality_context_path)
        self.history = [{"role": "system", "content": personality_context}]

    @staticmethod
    def _read_file(file_path):
        """Lit un fichier avec encodage UTF-8."""
        try:
            with open(file_path , "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
             return "You are a helpful and friendly assistant."
             
    @staticmethod
    def format_streamlit_image_to_base64(streamlit_file_object):
        # Méthode pour la vision (omis pour la concision)
        pass 

    @staticmethod
    def _create_vision_message(user_interaction, image_b64):
        # Méthode pour la vision (omis pour la concision)
        pass

    # --- GESTION DE L'HISTORIQUE ---

    def _update_history(self, role, content):
         """Ajoute une interaction à l'historique isolé."""
         self.history.append(
                {
                    "role": role,
                    "content": content,
                })
                
    def _normalize_history(self, history_to_normalize):
        """Convertit les anciens messages multimodaux (listes) en messages texte (chaînes)."""
        normalized_history = []
        for message in history_to_normalize:
            normalized_message = message.copy()
            content = normalized_message["content"]

            if normalized_message["role"] == "user" and isinstance(content, list):
                text_content = next((item['text'] for item in content if item.get('type') == 'text'), 
                                    f"Message précédent de {self.name} (image)")
                normalized_message["content"] = text_content
            
            normalized_history.append(normalized_message)
            
        return normalized_history

    # --- MÉTHODES LLM / VISION ---

    def ask_llm(self, user_interaction):
        """Mode Texte Simple : Envoie l'interaction LLM et met à jour l'historique."""
        self._update_history(role="user", content=user_interaction)
        normalized_history = self._normalize_history(self.history)

        response = self.client.chat.completions.create(
            messages=normalized_history,
            model=self.large_language_model 
        ).choices[0].message.content
        
        self._update_history(role="assistant", content=response)
        return response


    def ask_vision_model(self, user_interaction, image_b64):
        """Mode Vision (non utilisé ici)"""
        pass 

    # --- INTERFACE DE JEU (LOGIQUE DE DÉCISION) ---

    def receive_public_message(self, sender_name, message):
         """Enregistre un message public du débat dans l'historique de l'IA."""
         public_interaction = f"Message public de {sender_name}: {message}"
         self._update_history(role="user", content=public_interaction)

    def _prompt_llm_for_decision(self, prompt, model):
         """Fonction utilitaire pour obtenir une réponse concise (Nom de la cible ou du votant)."""
         self._update_history(role="user", content=prompt)
         normalized_history = self._normalize_history(self.history)
         
         response = self.client.chat.completions.create(
             messages=normalized_history,
             model=model,
             max_tokens=50, 
             temperature=0.7 
         ).choices[0].message.content
         
         self._update_history(role="assistant", content=f"Décision interne: {response}")
         return response.strip()


    def decide_night_action(self, alive_players):
        """Demande au LLM de choisir une cible pour son action de nuit."""
        if self.role.night_action == NightAction.NONE:
            return None 
            
        alive_names = [p.name for p in alive_players if p.name != self.name] 
        action_name = self.role.night_action.value
        
        prompt = (
            f"La nuit est tombée. Ton rôle ({self.role.name}) te demande d'agir: {action_name}. "
            f"Voici la liste des joueurs VIVANTS : {', '.join(alive_names)}. "
            f"RÉPONDS UNIQUEMENT AVEC LE NOM DU JOUEUR CIBLÉ. (Ex: Alice)"
        )
        
        target_name = self._prompt_llm_for_decision(prompt, self.large_language_model)
        return target_name

    def decide_vote(self, public_status, debate_summary):
        """Demande au LLM de choisir sa victime pour le lynchage de jour."""
        alive_names = [p['name'] for p in public_status if p['is_alive'] and p['name'] != self.name]

        prompt = (
            f"C'est la phase de vote. Tu es un(e) {self.role.name}. "
            f"RÉSUMÉ DU DÉBAT (ton historique): {debate_summary}. "
            f"RÉPONDS UNIQUEMENT AVEC LE NOM DU JOUEUR POUR QUI TU VOTES. (Ex: Ben)"
        )
        
        voted_name = self._prompt_llm_for_decision(prompt, self.large_language_model)
        return voted_name

    def generate_debate_message(self, current_game_status):
        """Génère un message de débat public basé sur son rôle et sa personnalité."""
        alive_names = [p['name'] for p in current_game_status if p['is_alive'] and p['name'] != self.name]
        
        prompt = (
            f"Nous sommes en phase de débat. Tu es un(e) {self.role.name} ({self.role.camp.value}). "
            f"Tu as entendu les messages suivants (dans ton historique). "
            f"GÉNÈRE UNE PHRASE DE DÉBAT : Accuse quelqu'un, défends-toi, ou pose une question stratégique. "
            f"Si tu es Loup-Garou, MENS et piège quelqu'un d'autre. Si tu es Villageois, utilise les informations que tu as. "
            f"RÉPONDS AVEC UN MESSAGE COURT ET DIRECT (pas de 'Je pense que...')."
        )
        debate_message = self.ask_llm(user_interaction=prompt)
        return debate_message

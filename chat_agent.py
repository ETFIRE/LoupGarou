# # chat_agent.py

# # -*- coding: utf-8 -*-
# from groq import Groq
# from dotenv import load_dotenv
# import os
# import base64
# import json
# import random 
# from enum import Enum 

# # --- Importations des définitions de jeu ---
# from enums_and_roles import Camp, NightAction, Role 

# # --- Dépendance de Player (mockée pour éviter la boucle d'importation) ---
# # NOTE: Cette classe est dupliquée ici ET dans game_core.py. 
# # Si tu l'enlèves d'ici, tu auras besoin d'importer Player depuis game_core, ce qui crée une boucle.
# # Nous la gardons donc ici pour la simplicité de la dépendance.
# class Player:
#     def __init__(self, name, is_human=False):
#         self.name = name
#         self.is_human = is_human
#         self.role = None
#         self.is_alive = True
#         self.has_kill_potion = False 
#         self.has_life_potion = False 
#     def assign_role(self, role):
#         self.role = role


# # --------------------------------------------------------

# class ChatAgent(Player):
#     """
#     Représente un joueur IA. Gère l'historique isolé, la personnalité et l'API LLM.
#     """
    
#     VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct" # Modèle multimodal
    
#     def __init__(self, name, personality_context_path, is_human=False):
        
#         super().__init__(name, is_human)
        
#         # NOTE: load_dotenv() est appelé dans loup_garou_arcade.py
#         if "GROQ_KEY" not in os.environ:
#              raise EnvironmentError("GROQ_KEY non trouvée. Assurez-vous d'avoir un fichier .env.")
             
#         self.client = Groq(api_key=os.environ["GROQ_KEY"])
#         self.personality_context_path = personality_context_path
#         self.history = [] 
#         self.large_language_model = "llama-3.3-70b-versatile" 
#         self.initiate_history()


#     def initiate_history(self):
#         """Initialise/réinitialise l'historique avec le contexte de personnalité."""
#         personality_context = self._read_file(self.personality_context_path)
#         self.history = [{"role": "system", "content": personality_context}]

#     # --- Méthodes Statiques Utilitaires ---
    
#     @staticmethod
#     def _read_file(file_path):
#         """Lit un fichier avec encodage UTF-8."""
#         try:
#             with open(file_path , "r", encoding="utf-8") as file:
#                 return file.read()
#         except FileNotFoundError:
#              return "You are a helpful and friendly assistant."

#     @staticmethod
#     def format_streamlit_image_to_base64(streamlit_file_object):
#         """Méthode pour la vision (non utilisée dans ce contexte Loup Garou)."""
#         # Code de conversion Base64 omis pour la concision

#     @staticmethod
#     def _create_vision_message(user_interaction, image_b64):
#         # Code de création du message vision omis
#         pass

#     # --- Gestion de l'Historique ---

#     def _update_history(self, role, content):
#          """Ajoute une interaction à l'historique isolé."""
#          self.history.append(
#                 {
#                     "role": role,
#                     "content": content,
#                 })
                
#     def _normalize_history(self, history_to_normalize):
#         """Convertit les anciens messages multimodaux (listes) en messages texte (chaînes)."""
#         normalized_history = []
#         for message in history_to_normalize:
#             normalized_message = message.copy()
#             content = normalized_message["content"]

#             if normalized_message["role"] == "user" and isinstance(content, list):
#                 text_content = next((item['text'] for item in content if item.get('type') == 'text'), 
#                                     f"Message précédent de {self.name} (image)")
#                 normalized_message["content"] = text_content
            
#             normalized_history.append(normalized_message)
            
#         return normalized_history

#     # --- Méthodes LLM / Vision (Logique API) ---

#     def ask_llm(self, user_interaction):
#         """Mode Texte Simple : Envoie l'interaction LLM et met à jour l'historique."""
#         self._update_history(role="user", content=user_interaction)
#         normalized_history = self._normalize_history(self.history)

#         response = self.client.chat.completions.create(
#             messages=normalized_history,
#             model=self.large_language_model 
#         ).choices[0].message.content
        
#         self._update_history(role="assistant", content=response)
#         return response


#     def ask_vision_model(self, user_interaction, image_b64):
#         """Mode Vision : Envoie l'interaction multimodale (Non essentiel ici)."""
#         # Code omis pour la concision.

#     # --- INTERFACE DE JEU (DECISION LOGIC) ---

#     def receive_public_message(self, sender_name, message):
#          """Enregistre un message public du débat dans l'historique de l'IA."""
#          public_interaction = f"Message public de {sender_name}: {message}"
#          self._update_history(role="user", content=public_interaction)

#     def _prompt_llm_for_decision(self, prompt, model):
#          """Fonction utilitaire pour obtenir une réponse concise (Nom de la cible ou du votant)."""
#          self._update_history(role="user", content=prompt)
#          normalized_history = self._normalize_history(self.history)
         
#          response = self.client.chat.completions.create(
#              messages=normalized_history,
#              model=model,
#              max_tokens=50, 
#              temperature=0.7 
#          ).choices[0].message.content
         
#          self._update_history(role="assistant", content=f"Décision interne: {response}")
#          return response.strip()


#     def decide_night_action(self, alive_players):
#         """Demande au LLM de choisir une cible pour son action de nuit."""
#         if self.role.night_action == NightAction.NONE:
#             return None 
            
#         alive_names = [p.name for p in alive_players if p.name != self.name] 
#         action_name = self.role.night_action.value
        
#         prompt = (
#             f"La nuit est tombée. Ton rôle ({self.role.name}) te demande d'agir: {action_name}. "
#             f"Voici la liste des joueurs VIVANTS : {', '.join(alive_names)}. "
#             f"RÉPONDS UNIQUEMENT AVEC LE NOM DU JOUEUR CIBLÉ. (Ex: Alice)"
#         )
        
#         target_name = self._prompt_llm_for_decision(prompt, self.large_language_model)
#         return target_name

#     def decide_vote(self, public_status, debate_summary):
#         """Demande au LLM de choisir sa victime pour le lynchage de jour."""
#         alive_names = [p['name'] for p in public_status if p['is_alive'] and p['name'] != self.name]

#         prompt = (
#             f"C'est la phase de vote. Tu es un(e) {self.role.name}. "
#             f"RÉSUMÉ DU DÉBAT (ton historique): {debate_summary}. "
#             f"RÉPONDS UNIQUEMENT AVEC LE NOM DU JOUEUR POUR QUI TU VOTES. (Ex: Ben)"
#         )
        
#         voted_name = self._prompt_llm_for_decision(prompt, self.large_language_model)
#         return voted_name

#     def generate_debate_message(self, current_game_status):
#         """Génère un message de débat public basé sur son rôle et sa personnalité."""
#         alive_names = [p['name'] for p in current_game_status if p['is_alive'] and p['name'] != self.name]
        
#         prompt = (
#             f"Nous sommes en phase de débat. Tu es un(e) {self.role.name} ({self.role.camp.value}). "
#             f"Tu as entendu les messages suivants (dans ton historique). "
#             f"GÉNÈRE UNE PHRASE DE DÉBAT : Accuse quelqu'un, défends-toi, ou pose une question stratégique. "
#             f"Si tu es Loup-Garou, MENS et piège quelqu'un d'autre. Si tu es Villageois, utilise les informations que tu as. "
#             f"RÉPONDS AVEC UN MESSAGE COURT ET DIRECT (pas de 'Je pense que...')."
#         )
#         debate_message = self.ask_llm(user_interaction=prompt)
#         return debate_message

# -*- coding: utf-8 -*-
from groq import Groq
from dotenv import load_dotenv
import os
import json
from enums_and_roles import Camp, NightAction, Role

load_dotenv()

class ChatAgent:
    """
    Représente un joueur IA. Gère l'historique isolé, la personnalité et l'API LLM.
    """
    
    def __init__(self, name, personality_context_path, is_human=False):
        self.name = name
        self.is_human = is_human
        self.role = None
        self.is_alive = True
        
        if "GROQ_KEY" not in os.environ:
            raise EnvironmentError("GROQ_KEY non trouvée dans .env")
             
        self.client = Groq(api_key=os.environ["GROQ_KEY"])
        self.personality_context_path = personality_context_path
        self.history = []
        self.large_language_model = "llama-3.3-70b-versatile"
        self.initiate_history()

    def initiate_history(self):
        """Initialise l'historique avec le contexte de personnalité."""
        try:
            with open(self.personality_context_path, "r", encoding="utf-8") as file:
                personality_context = file.read()
        except FileNotFoundError:
            personality_context = f"Tu es {self.name}, un joueur de Loup Garou."
        
        self.history = [{
            "role": "system", 
            "content": f"{personality_context}\nTu es dans un jeu de Loup Garou. Réponds de manière concise et naturelle."
        }]

    def _update_history(self, role, content):
        """Ajoute une interaction à l'historique."""
        self.history.append({"role": role, "content": content})

    def assign_role(self, role):
        """Assigne un rôle au joueur."""
        self.role = role
        if not self.is_human:
            self._update_history("system", 
                f"TON RÔLE ACTUEL: {role.name}. Tu es dans le camp des {role.camp.value}. "
                f"Ton action de nuit: {role.night_action.value if role.night_action else 'Aucune'}. "
                f"{'Tu dois mentir si tu es un Loup Garou.' if role.camp == Camp.LOUP else 'Tu dois trouver les Loups Garous.'}"
            )

    def receive_public_message(self, sender_name, message):
        """Enregistre un message public du débat."""
        public_interaction = f"Message public de {sender_name}: {message}"
        self._update_history("user", public_interaction)

    def ask_llm(self, prompt):
        """Envoie une requête au LLM."""
        self._update_history("user", prompt)
        
        try:
            response = self.client.chat.completions.create(
                messages=self.history,
                model=self.large_language_model,
                max_tokens=150,
                temperature=0.7
            ).choices[0].message.content
            
            self._update_history("assistant", response)
            return response.strip()
        except Exception as e:
            print(f"Erreur API pour {self.name}: {e}")
            return f"Je suis {self.name} et je réfléchis..."

    def decide_night_action(self, alive_players):
        """Décide de l'action de nuit."""
        if self.role.night_action == NightAction.NONE:
            return None
            
        alive_names = [p.name for p in alive_players if p.name != self.name]
        
        prompt = (
            f"C'est la nuit. Ton rôle ({self.role.name}) te demande de: {self.role.night_action.value}. "
            f"Joueurs vivants: {', '.join(alive_names)}. "
            f"Choisis UN SEUL nom parmi eux. Réponds uniquement avec le nom."
        )
        
        return self.ask_llm(prompt)

    def decide_vote(self, public_status, debate_summary):
        """Décide du vote pour le lynchage."""
        alive_names = [p['name'] for p in public_status if p['is_alive'] and p['name'] != self.name]
        
        prompt = (
            f"C'est la phase de vote. Tu es {self.role.name} ({self.role.camp.value}). "
            f"Dernier débat: {debate_summary}. "
            f"Qui veux-tu lyncher? Choisis parmi: {', '.join(alive_names)}. "
            f"Réponds uniquement avec le nom."
        )
        
        return self.ask_llm(prompt)

    def generate_debate_message(self, current_game_status):
        """Génère un message pour le débat."""
        prompt = (
            f"C'est le débat public. Tu es {self.name}, un(e) {self.role.name} ({self.role.camp.value}). "
            f"Que dis-tu au village? "
            f"Sois naturel, accuse ou défends-toi en 1-2 phrases."
        )
        
        return self.ask_llm(prompt)
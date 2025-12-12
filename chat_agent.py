
from groq import Groq
from dotenv import load_dotenv
import os
import json
import random 
from enum import Enum 


from enums_and_roles import Camp, NightAction, Role 


# NOTE: Cette classe doit correspondre à la structure de Player/ChatAgent dans game_core.py
class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.is_human = is_human
        self.role = None
        self.is_alive = True
        self.has_kill_potion = False 
        self.has_life_potion = False 
        self.wolf_teammates = [] 
        self.has_hunter_shot = True
    def assign_role(self, role):
        self.role = role

# --------------------------------------------------------

class ChatAgent(Player):
    """
    Représente un joueur IA. Gère l'historique isolé, la personnalité et l'API LLM (via Groq).
    """
    
    
    large_language_model = "llama-3.3-70b-versatile" 
    
    def __init__(self, name, personality_context_path, is_human=False):
        
        super().__init__(name, is_human)
        
       
        if "GROQ_KEY" not in os.environ:
             raise EnvironmentError("GROQ_KEY non trouvée. Assurez-vous d'avoir un fichier .env.")
             
        self.client = Groq(api_key=os.environ["GROQ_KEY"])
        self.personality_context_path = personality_context_path
        self.history = [] 
        self.initiate_history()

    

    def initiate_history(self):
        """Initialise/réinitialise l'historique avec le contexte de personnalité."""
        personality_context = self._read_file(self.personality_context_path)
        
        
        system_instruction = (
            "Tu es un joueur de Loup Garou. Ton but est de manipuler la discussion. "
            "Sois toujours actif, jamais neutre. Accuse, défends-toi, ou retourne la situation avec force. "
            "Rends tes interventions courtes, percutantes et conformes à ta personnalité unique. "
            "Voici ta personnalité : \n" + personality_context
        )
        self.history = [{"role": "system", "content": system_instruction}]

    @staticmethod
    def _read_file(file_path):
        """Lit un fichier avec encodage UTF-8."""
        try:
            with open(file_path , "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
             return "You are a helpful and friendly assistant."
             


    def _update_history(self, role, content):
         """Ajoute une interaction à l'historique isolé."""
         self.history.append(
                 {
                     "role": role,
                     "content": content,
                 })
                 
    def _normalize_history(self, history_to_normalize):
        """Convertit les messages multimodaux (non supportés par ce modèle) en messages texte."""
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

   

    def ask_llm(self, user_interaction):
        """Mode Texte Simple : Envoie l'interaction LLM et met à jour l'historique."""
        self._update_history(role="user", content=user_interaction)
        normalized_history = self._normalize_history(self.history)

        try:
            response = self.client.chat.completions.create(
                messages=normalized_history,
                model=self.large_language_model, 
                temperature=0.9 
            ).choices[0].message.content
            
            self._update_history(role="assistant", content=response)
            return response
            
        except Exception as e:
            print(f"Erreur GROQ API (LLM) : {e}")
            return f"[ERREUR LLM : Échec de la communication. {e}]"


    def receive_public_message(self, sender_name, message):
         """Enregistre un message public du débat dans l'historique de l'IA."""
         public_interaction = f"Message public de {sender_name}: {message}"
         self._update_history(role="user", content=public_interaction)

    def _prompt_llm_for_decision(self, prompt, model):
         """Fonction utilitaire pour obtenir une réponse concise (Nom de la cible ou du votant)."""
         self._update_history(role="user", content=prompt)
         normalized_history = self._normalize_history(self.history)
          
         try:
             response = self.client.chat.completions.create(
                 messages=normalized_history,
                 model=model,
                 max_tokens=50, 
                 temperature=0.7 
             ).choices[0].message.content
             
             self._update_history(role="assistant", content=f"Décision interne: {response}")
             return response.strip()
         except Exception as e:
             print(f"Erreur GROQ API (Décision) : {e}")
             
             # NOTE : Nécessite l'accès à la liste des joueurs vivants, ce qui n'est pas possible ici.
             return "Maître Simon" 

    def decide_night_action(self, alive_players):
         """Demande au LLM de choisir une cible pour son action de nuit."""
         if self.role.night_action == NightAction.NONE:
             return None 
             
         alive_names = [p.name for p in alive_players if p.name != self.name] 
         action_name = self.role.night_action.value
         
         prompt = (
             f"La nuit est tombée. Ton rôle ({self.role.name}) te demande d'agir: {action_name}. "
             "Basé sur l'historique des accusations et ta stratégie de victoire, choisis ta cible. "
             f"Voici la liste des joueurs VIVANTS : {', '.join(alive_names)}. "
             f"RÉPONDS UNIQUEMENT AVEC LE NOM DU JOUEUR CIBLÉ. (Ex: Alice)"
         )
         
         target_name = self._prompt_llm_for_decision(prompt, self.large_language_model)
         return target_name

    def decide_vote(self, public_status, debate_summary):
         """Demande au LLM de choisir sa victime pour le lynchage de jour (Moins Docile)."""
         alive_names = [p['name'] for p in public_status if p['is_alive'] and p['name'] != self.name]
         
         
         if self.role.camp == Camp.LOUP:
             vote_instruction = "Tu es Loup-Garou. Vote CONTRE le Villageois le plus dangereux ou qui t'accuse. Ne vote JAMAIS contre tes alliés."
         else:
             vote_instruction = "Tu es Villageois. Vote pour le joueur que tu soupçonnes le plus, en ignorant les arguments trop émotionnels. Ne t'abstient JAMAIS."
             
         targets_str = ", ".join(alive_names)
         
         prompt = (
             f"C'est la phase de vote. Tu es un(e) {self.role.name}. {vote_instruction} "
             f"Ton historique contient le débat. Tu dois voter pour l'un des joueurs vivants suivants : {targets_str}. "
             "RÈGLE IMPÉRATIVE : NE RÉPONDS QU'AVEC LE NOM DU JOUEUR CHOISI. Pas de phrase, pas d'explication, juste le nom."
         )
         
         voted_name = self._prompt_llm_for_decision(prompt, self.large_language_model)
         
        
         if voted_name and voted_name in alive_names:
             return voted_name
         
         if alive_names:
              return random.choice(alive_names)
              
         return None

    def generate_debate_message(self, current_game_status):
         """
         Génère un message de débat public, forçant l'IA à être active, accusatrice ou à révéler sa preuve.
         """
         
         alive_names = [p['name'] for p in current_game_status if p['is_alive'] and p['name'] != self.name]
         
         is_accused = any(self.name in msg['content'] for msg in self.history[-5:] if msg['role'] == 'user')
         
         is_voyante = (self.role.name == "Voyante")
         found_wolf_info = next((
             msg['content'] for msg in self.history 
             if msg['role'] == 'system' and "Loup" in msg['content'] and "vu" in msg['content']
         ), None)
         
         if is_voyante and found_wolf_info:
             
             instruction = (
                 f"Tu es la Voyante. Tu as une preuve DIRECTE: '{found_wolf_info}'. "
                 "RÉVÈLE IMMÉDIATEMENT le joueur que tu as vu comme étant LOUP. "
                 "Utilise ta personnalité de {self.role.name} pour convaincre le village de ta vérité, mais sois prudent(e). "
             )
         
        
         elif is_accused:
             
             instruction = (
                 f"On t'accuse ! Utilise ta personnalité de {self.role.name} pour TE DÉFENDRE VIRULEMMENT et CONTRE-ATTAQUER. "
                 "Réfute l'accusation en la retournant contre ton accusateur. Ne sois pas passif. "
             )
         else:
             
             instruction = (
                 f"Nous sommes en débat. Utilise ta personnalité de {self.role.name} pour ACCUSER DIRECTEMENT QUELQU'UN. "
                 "Cherche les contradictions, les silences ou attaque le joueur qui est le moins accusé. Ne reste JAMAIS neutre. "
             )
 
        
         general_instruction = (
             f"Ton rôle est {self.role.name} ({self.role.camp.value}). Consulte ton historique (TON SEUL GUIDE). "
             f"RÉPONDS AVEC UN MESSAGE TRES COURT, PERCUTANT ET DIRECT (MAXIMUM 20 MOTS). "
             "Si tu es Loup-Garou, rends ton mensonge subtil et complexe, quitte à faire une FAUSSE ACCUSATION très forte. Ne réponds qu'avec le message lui-même."
         )
 
         prompt = instruction + general_instruction
         
         debate_message = self.ask_llm(user_interaction=prompt)
         
         return debate_message
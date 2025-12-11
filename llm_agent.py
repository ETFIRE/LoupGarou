from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()


class LLMAgent:
    """
    Agent LLM pour un joueur IA.
    - Historique privé (pas partagé avec les autres IA).
    - Connaît son rôle (wolf, villager, etc.) et sa personnalité (logical, emotional...).
    - Peut être reset à la fin de la partie.
    """

    def __init__(self, role: str, personality: str, system_context: str):
        """
        role: rôle de jeu (ex: 'werewolf', 'seer', 'villager', etc.)
        personality: style de la personnalité (ex: 'logical', 'emotional', 'suspicious', etc.)
        system_context: texte global du jeu (règles, ambiance) que tu écriras plus tard.
        """
        api_key = os.environ.get("GROQ_KEY")
        if not api_key:
            raise ValueError("GROQ_KEY manquant dans le fichier .env")

        self.client = Groq(api_key=api_key)
        self.role = role
        self.personality = personality

        # Historique privé de cette IA uniquement
        self.history = [
            {
                "role": "system",
                "content": self._build_system_prompt(system_context),
            }
        ]

    def _build_system_prompt(self, base_context: str) -> str:
        """
        Construit le message système avec :
        - contexte global du jeu (base_context)
        - rôle du joueur
        - personnalité
        - rappel que l'IA doit essayer de piéger / manipuler
        """
        extra_instructions = (
            f"Tu joues au jeu du Loup Garou. "
            f"Ton rôle est: {self.role}. "
            f"Ta personnalité est: {self.personality}. "
            "Tu dois débattre, accuser, défendre, et parfois mentir ou manipuler "
            "les autres joueurs pour gagner, en restant cohérent avec ton rôle."
        )
        # Tu peux enrichir base_context plus tard avec les règles complètes.
        return base_context + "\n\n" + extra_instructions

    def reset_history(self, system_context: str):
        """
        Réinitialise complètement la mémoire pour une nouvelle partie.
        """
        self.history = [
            {
                "role": "system",
                "content": self._build_system_prompt(system_context),
            }
        ]

    def add_message(self, role: str, content: str):
        """
        Ajoute un message dans l'historique de CETTE IA.
        role: 'user' pour ce que le jeu/l'humain dit à cette IA,
              'assistant' pour ce que cette IA a déjà répondu.
        """
        self.history.append({"role": role, "content": content})

    def ask(self, user_message: str, model: str) -> str:
        """
        Envoie un message au LLM en gardant l'historique privé de cette IA.
        - user_message contient généralement le résumé des débats publics
          + la question posée à cette IA (pour qui votes-tu, que réponds-tu, etc.).
        - model est l'identifiant du modèle Groq (ex: 'llama-3.1-70b-versatile').
        """
        self.add_message(role="user", content=user_message)

        response = self.client.chat.completions.create(
            model=model,
            messages=self.history,
        ).choices[0].message.content

        self.add_message(role="assistant", content=response)
        return response

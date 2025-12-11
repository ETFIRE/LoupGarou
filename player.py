from typing import Optional
from llm_agent import LLMAgent


class Player:
    """
    Joueur générique (humain ou IA).
    """

    def __init__(self, name: str, role: str, personality: Optional[str] = None):
        self.name = name                  # nom affiché à l'écran
        self.role = role                  # loup, villageois, etc.
        self.personality = personality    # surtout pour l'IA
        self.is_alive = True
        self.current_vote_target = None   # nom ou id du joueur ciblé

    def reset_for_new_game(self):
        self.is_alive = True
        self.current_vote_target = None


class HumanPlayer(Player):
    """
    Joueur humain contrôlé au clavier/souris via Pygame.
    Pas d'LLMAgent ici.
    """

    def choose_vote_target(self, alive_players: list[str]) -> Optional[str]:
        """
        Méthode appelée par la boucle Pygame :
        - affiche les options
        - renvoie le nom/ID de la cible choisie
        Pour l'instant, on laisse la signature, tu rempliras plus tard avec Pygame.
        """
        # TODO: implémenter l'interface Pygame pour choisir la cible
        return None


class AIPlayer(Player):
    """
    Joueur IA qui utilise un LLMAgent pour parler et voter.
    """

    def __init__(self, name: str, role: str, personality: str, llm_agent: LLMAgent):
        super().__init__(name=name, role=role, personality=personality)
        self.llm_agent = llm_agent

    def speak(self, public_context: str, model: str) -> str:
        """
        Génère une phrase de débat.
        public_context: résumé des événements visibles (qui est mort, votes, etc.).
        """
        prompt = (
            "Voici le contexte public de la partie:\n"
            f"{public_context}\n\n"
            "Réponds par une seule intervention de débat (quelques phrases max)."
        )
        return self.llm_agent.ask(user_message=prompt, model=model)

    def decide_vote(self, public_context: str, candidates: list[str], model: str) -> str:
        """
        Demande au LLM pour qui voter parmi les candidats encore vivants.
        """
        options_str = ", ".join(candidates)
        prompt = (
            "Tu dois choisir un joueur à éliminer.\n"
            f"Contexte public:\n{public_context}\n\n"
            f"Joueurs possibles: {options_str}\n"
            "Réponds uniquement par le NOM du joueur que tu votes."
        )
        vote_response = self.llm_agent.ask(user_message=prompt, model=model)
        # On gardera la logique de parsing plus tard (nettoyer la réponse).
        return vote_response

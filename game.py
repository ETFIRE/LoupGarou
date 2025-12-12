import random
from typing import List
from player import HumanPlayer, AIPlayer
from llm_agent import LLMAgent

# Rôles de base (tu peux les mettre dans un fichier config séparé si tu veux)
BASE_ROLES = [
    "petite_fille",
    "sorciere",
    "villageois",
    "villageois",
    "chasseur",
    "loup_garou",
    "loup_garou",
    "loup_garou",
    "chef_du_village",
    "mentaliste",  # rôle supplémentaire
]


# Exemples de personnalités possibles
PERSONALITIES = [
    "logique",
    "emotionnel",
    "suspect",
    "paranoiaque",
    "leader",
    "timide",
    "agressif",
    "strategique",
    "chaotique",
]

DEFAULT_MODEL = "llama-3.3-70b-versatile"


class Game:
    """
    Gère l'état global d'une partie de Loup-Garou.
    - Création des joueurs (1 humain + 9 IA)
    - Distribution aléatoire des rôles et personnalités aux IA
    - Compteur de loups vivants
    - Reset de la partie
    """

    def __init__(self, system_context: str):
        self.system_context = system_context
        self.players: List[HumanPlayer | AIPlayer] = []
        self.current_day = 1
        self.is_night = False
        self.running = False
        self.model = DEFAULT_MODEL

    def _create_human_player(self, name: str, role: str) -> HumanPlayer:
        return HumanPlayer(name=name, role=role)

    def _create_ai_player(self, name: str, role: str, personality: str) -> AIPlayer:
        agent = LLMAgent(
            role=role,
            personality=personality,
            system_context=self.system_context,
        )
        return AIPlayer(name=name, role=role, personality=personality, llm_agent=agent)

    def setup_new_game(self, human_name: str = "You", human_choose_role: bool = False):
        """
        Prépare une nouvelle partie (10 joueurs max).
        - Reset complet des joueurs
        - Distribution des rôles et personnalités aléatoires
        """
        self.players.clear()
        self.current_day = 1
        self.is_night = False
        self.running = True

        roles = BASE_ROLES.copy()
        random.shuffle(roles)

        # Choix du rôle humain
        if human_choose_role:
            # Pour l'instant, on prend juste le premier rôle,
            # tu pourras remplacer ça par un vrai menu Pygame.
            human_role = roles.pop(0)
        else:
            # Rôle aléatoire parmi les rôles disponibles
            human_role = roles.pop(random.randrange(len(roles)))

        human_player = self._create_human_player(name=human_name, role=human_role)
        self.players.append(human_player)

        # Rôles restants pour les IA
        remaining_roles = roles
        personalities = PERSONALITIES.copy()
        random.shuffle(personalities)

        nb_ia = min(9, len(remaining_roles))  # sécurité

        for i in range(nb_ia):
            role = remaining_roles[i]
            personality = personalities[i % len(personalities)]
            ai_name = f"IA_{i+1}"
            ai_player = self._create_ai_player(
                name=ai_name,
                role=role,
                personality=personality,
            )
            self.players.append(ai_player)

    def get_alive_players(self) -> List[str]:
        return [p.name for p in self.players if p.is_alive]

    def count_alive_wolves(self) -> int:
        return sum(1 for p in self.players if p.is_alive and "loup" in p.role)

    def reset_all_llm_memory(self):
        """
        À appeler à la fin de la partie pour effacer la mémoire des IA.
        """
        for p in self.players:
            if isinstance(p, AIPlayer):
                p.llm_agent.reset_history(self.system_context)

    def is_game_over(self) -> bool:
        """
        Condition de fin très simple :
        - plus de loups vivants => village gagne
        - loups >= autres vivants => loups gagnent
        """
        alive = [p for p in self.players if p.is_alive]
        wolves = [p for p in alive if "loup" in p.role]
        non_wolves = [p for p in alive if "loup" not in p.role]

        if len(wolves) == 0:
            return True
        if len(wolves) >= len(non_wolves):
            return True
        return False

    def get_public_context_summary(self) -> str:
        """
        Résumé très simple de l'état public de la partie,
        utilisé pour créer les prompts des IA.
        """
        alive_names = [p.name for p in self.players if p.is_alive]
        dead_names = [p.name for p in self.players if not p.is_alive]
        wolves_count = self.count_alive_wolves()

        dead_text = ", ".join(dead_names) if dead_names else "aucun pour le moment"

        summary = (
            f"Jour {self.current_day}. "
            f"Joueurs encore en vie: {', '.join(alive_names)}. "
            f"Joueurs morts: {dead_text}. "
            f"Nombre de loups garous encore vivants (secret pour les humains): {wolves_count}."
        )
        return summary

    def debate_phase(self):
        """
        Phase de débat : chaque IA encore en vie prend la parole une fois.
        Retourne une liste de textes (log du débat) à afficher dans Pygame.
        """
        public_context = self.get_public_context_summary()
        logs = []

        for p in self.players:
            if not p.is_alive:
                continue
            if isinstance(p, AIPlayer):
                speech = p.speak(public_context=public_context, model=self.model)
                logs.append(f"{p.name}: {speech}")
            else:
                logs.append(f"{p.name}: (le joueur humain peut parler)")

        return logs

    def voting_phase(self):
        """
        Phase de vote simple :
        - toutes les IA votent parmi les joueurs vivants
        - le joueur humain votera via Pygame (à brancher plus tard)
        - le joueur avec le plus de votes est éliminé
        """
        public_context = self.get_public_context_summary()
        alive_players = [p for p in self.players if p.is_alive]
        candidate_names = [p.name for p in alive_players]

        votes = {name: 0 for name in candidate_names}

        # Votes IA
        for p in alive_players:
            if isinstance(p, AIPlayer):
                raw_vote = p.decide_vote(
                    public_context=public_context,
                    candidates=candidate_names,
                    model=self.model,
                )
                # Nettoyage très simple : on garde le premier nom qui apparaît dans la réponse
                chosen = None
                for name in candidate_names:
                    if name.lower() in raw_vote.lower():
                        chosen = name
                        break
                if chosen is None:
                    # Si le modèle se trompe, vote aléatoire
                    chosen = random.choice(candidate_names)
                votes[chosen] += 1

        # TODO: ajouter le vote du joueur humain via Pygame et incrémenter votes[target]

        # Trouver le joueur le plus voté
        max_votes = max(votes.values())
        top_candidates = [name for name, count in votes.items() if count == max_votes]
        eliminated_name = random.choice(top_candidates)  # départager les égalités

        # Marquer comme mort
        for p in self.players:
            if p.name == eliminated_name:
                p.is_alive = False
                break

        return eliminated_name, votes

import random
import time
import os
from enum import Enum

# Importations de base
from enums_and_roles import Camp, NightAction, Role, ROLES_POOL
from chat_agent import ChatAgent  # L'IA
from personalities import pick_personality_for_role


# --- CLASSE PLAYER (NON IA) -------------------------------------------------


class Player:
    """Représente un joueur humain (ou IA, mais ChatAgent hérite de celle-ci)."""

    def __init__(self, name: str, is_human: bool = True) -> None:
        self.name = name
        self.is_human = is_human
        self.role: Role | None = None
        self.is_alive: bool = True
        self.has_kill_potion: bool = False
        self.has_life_potion: bool = False

    def assign_role(self, role: Role) -> None:
        """Assigne un rôle au joueur."""
        self.role = role

    def __repr__(self) -> str:
        status = "Vivant" if self.is_alive else "Mort"
        role_name = self.role.name if self.role else "N/A"
        kind = "Humain" if self.is_human else "IA"
        return f"[{kind}] {self.name} ({role_name} - {status})"


# --- CLASSE GAMEMANAGER : ORCHESTRE UNE PARTIE ------------------------------


class GameManager:
    """Gère le déroulement et la logique d'une partie complète."""

    # Durée max simulée pour le débat (en secondes)
    DEBATE_TIME_LIMIT = 120

    def __init__(self, human_player_name: str = "Humain_Lucie") -> None:
        # État global de la partie
        self.day: int = 0
        self.players: list[Player] = []
        self.available_roles: list[Role] = list(ROLES_POOL.values())

        # Setup joueurs + rôles
        self.setup_players(human_player_name)
        self.distribute_roles()

        # Compteurs initiaux
        self.wolves_alive: int = sum(
            1 for p in self.players if p.role.camp == Camp.LOUP and p.is_alive
        )
        self.vote_counts: dict[str, int] = {}

    # --- SETUP ---------------------------------------------------------------

    def setup_players(self, human_player_name: str) -> None:
        """Crée 9 IA + 1 joueur humain avec un chemin de personnalité initial."""
        ia_names = [f"IA {i+1}" for i in range(9)]
        personality_paths = [f"context/perso_{i+1}.txt" for i in range(9)]
        random.shuffle(personality_paths)

        self.players = []
        for name, path in zip(ia_names, personality_paths):
            self.players.append(
                ChatAgent(name=name, personality_context_path=path, is_human=False)
            )

        # Le joueur humain est un Player simple
        self.players.append(Player(name=human_player_name, is_human=True))

    def distribute_roles(self, custom_roles: list[Role] | None = None) -> None:
        """
        Distribue aléatoirement les rôles aux joueurs.
        Pour chaque IA, assigne aussi une personnalité (prompt système).
        """
        roles_to_distribute = custom_roles if custom_roles else list(self.available_roles)

        if len(self.players) != len(roles_to_distribute):
            raise ValueError(
                "Le nombre de joueurs doit correspondre au nombre de rôles disponibles"
            )

        random.shuffle(roles_to_distribute)

        for player in self.players:
            role = roles_to_distribute.pop()
            player.assign_role(role)

            # Cas spécial : la Sorcière reçoit ses deux potions
            if role.name == "Sorcière":
                player.has_kill_potion = True
                player.has_life_potion = True

            # Pour une IA, on ajoute personnalité + contexte rôle
            if not player.is_human:
                personality = pick_personality_for_role(role.name)
                player.personality_context_path = personality.context_path
                player.initiate_history()  # recharge son fichier de personnalité

                player.history.append(
                    {
                        "role": "system",
                        "content": (
                            f"TON RÔLE ACTUEL DANS LA PARTIE EST: {role.name}. "
                            f"Tu es dans le camp des {role.camp.value}. "
                            f"Ta personnalité est: {personality.name}. "
                            f"Adapte ton style de langage à cette personnalité."
                        ),
                    }
                )

            print(f"Rôle assigné à {player.name}: {player.role.name}")

    # --- UTILITAIRES D'ÉTAT --------------------------------------------------

    def get_alive_players(self) -> list[Player]:
        """Retourne la liste des joueurs vivants."""
        return [p for p in self.players if p.is_alive]

    def get_public_status(self) -> list[dict]:
        """Format public minimal pour les prompts IA (nom + vivant ou non)."""
        return [{"name": p.name, "is_alive": p.is_alive} for p in self.players]

    def check_win_condition(self) -> Camp | None:
        """Retourne le camp gagnant si la partie est terminée, sinon None."""
        alive = self.get_alive_players()
        wolves = sum(1 for p in alive if p.role.camp == Camp.LOUP)
        villagers = sum(1 for p in alive if p.role.camp == Camp.VILLAGEOIS)

        if wolves == 0:
            return Camp.VILLAGEOIS
        if wolves >= villagers:
            return Camp.LOUP
        return None

    # --- BOUCLE PRINCIPALE ---------------------------------------------------

    def start_game(self) -> None:
        """Boucle principale : enchaîne nuits et jours jusqu'à la victoire d'un camp."""
        print("\n--- Début du Jeu ---")

        while self.check_win_condition() is None:
            self.day += 1
            print(f"\n=================== Jour {self.day} ===================")

            self.night_phase()
            self.day_phase()

            self.wolves_alive = sum(
                1 for p in self.players if p.role.camp == Camp.LOUP and p.is_alive
            )

            winner = self.check_win_condition()
            if winner:
                print(
                    f"\n🎉 Victoire des {winner.value} après {self.day} jours ! "
                    f"Loups restants: {self.wolves_alive}"
                )
                return

    # --- PHASE DE NUIT -------------------------------------------------------

    def night_phase(self) -> None:
        """Gère toutes les actions de nuit (voyante, loups, sorcière...)."""
        print("\n🌙 La nuit tombe. Les joueurs ferment les yeux...")

        alive = self.get_alive_players()

        # Regroupement des acteurs par type d'action de nuit
        ordered_actions: dict[NightAction, list[Player]] = {
            NightAction.INVESTIGATE: [],
            NightAction.KILL: [],
            NightAction.POTION: [],
        }

        for player in alive:
            if player.role.night_action in ordered_actions:
                ordered_actions[player.role.night_action].append(player)

        kill_target: Player | None = None

        # 1. Action de la Voyante (INVESTIGATE)
        for voyante in ordered_actions[NightAction.INVESTIGATE]:
            if not voyante.is_human:
                target_name = voyante.decide_night_action(alive)
                target = next((p for p in alive if p.name == target_name), None)
                if target:
                    voyante.history.append(
                        {
                            "role": "system",
                            "content": (
                                f"Tu as vu que {target.name} est un(e) "
                                f"{target.role.name} ({target.role.camp.value}). "
                                f"Utilise cette info dans le débat."
                            ),
                        }
                    )
                    print(f"🔮 La Voyante ({voyante.name}) a enquêté sur {target.name}.")

        # 2. Action des Loups (KILL)
        wolves_acting = ordered_actions[NightAction.KILL]
        if wolves_acting:
            leader = wolves_acting[0]
            if not leader.is_human:
                target_name = leader.decide_night_action(alive)
                kill_target = next((p for p in alive if p.name == target_name), None)
                if kill_target:
                    print(f"🐺 Les Loups ciblent {kill_target.name}.")

        # 3. Action de la Sorcière (POTION)
        sorciere = next((p for p in alive if p.role.name == "Sorcière"), None)
        if sorciere:
            # À implémenter plus tard (utilisation des potions)
            pass

        # Exécution de l'élimination
        if kill_target and kill_target.is_alive:
            kill_target.is_alive = False
            print(f"❌ {kill_target.name} est mort(e).")

    # --- PHASE DE JOUR -------------------------------------------------------

    def day_phase(self) -> None:
        """Gère débat + vote + lynchage pour un jour complet."""
        print("\n☀️ Le jour se lève. Débat et lynchage.")
        alive = self.get_alive_players()
        self.vote_counts = {}

        self.debate_phase(alive)
        self.voting_phase(alive)
        self.lynch_result(alive)

    def debate_phase(self, alive_players: list[Player]) -> None:
        """Fait parler quelques joueurs pendant un temps limité."""
        print(f"\n💬 Le débat commence (max {self.DEBATE_TIME_LIMIT}s simulées).")
        start_time = time.time()

        for _ in range(5):
            if time.time() - start_time > self.DEBATE_TIME_LIMIT:
                print("\n⏱️ FIN DU TEMPS DE DÉLIBÉRATION.")
                break

            speaker = random.choice(alive_players)

            if not speaker.is_human:
                debate_message = speaker.generate_debate_message(
                    self.get_public_status()
                )
            else:
                debate_message = "Je suis innocent(e) !"

            print(f"🗣️ {speaker.name}: {debate_message}")

            # Mise à jour de l'historique des autres IA
            for listener in [
                p for p in alive_players if not p.is_human and p != speaker
            ]:
                listener.receive_public_message(speaker.name, debate_message)

            time.sleep(0.5)

    def voting_phase(self, alive_players: list[Player]) -> None:
        """Collecte les votes de tous les joueurs (IA + humain)."""
        print("\n🗳️ Place au vote !")

        for voter in alive_players:
            if not voter.is_human:
                voted_name = voter.decide_vote(
                    self.get_public_status(),
                    debate_summary="Récapitulatif des accusations...",
                )
            else:
                # TODO : remplacer par un vrai input joueur (UI) au lieu de random
                voted_name = random.choice([p.name for p in alive_players if p != voter])

            if voted_name in [p.name for p in alive_players]:
                self.vote_counts[voted_name] = (
                    self.vote_counts.get(voted_name, 0) + 1
                )
                print(f"   -> {voter.name} vote pour {voted_name}")
            else:
                # Vote invalide, ignoré
                pass

    def register_human_vote(self, voted_player_name: str) -> None:
        """
        Méthode utilitaire pour une future UI :
        enregistre le vote du joueur humain sans passer par voting_phase().
        """
        self.vote_counts[voted_player_name] = (
            self.vote_counts.get(voted_player_name, 0) + 1
        )

    def voting_phase_ia_only(self) -> None:
        """Version alternative : ne fait voter que les IA (pour une UI pilotée)."""
        alive_players = self.get_alive_players()

        for voter in alive_players:
            if not voter.is_human and voter.is_alive:
                voted_name = voter.decide_vote(
                    self.get_public_status(),
                    debate_summary="Récapitulatif des accusations...",
                )
                if voted_name in [p.name for p in alive_players]:
                    self.vote_counts[voted_name] = (
                        self.vote_counts.get(voted_name, 0) + 1
                    )

    def lynch_result(self, alive_players: list[Player]) -> None:
        """Calcule la victime du lynchage et applique l'élimination."""
        if not self.vote_counts:
            print("Personne n'a voté. Le village est confus.")
            return

        lynch_target_name = max(self.vote_counts, key=self.vote_counts.get)
        max_votes = self.vote_counts[lynch_target_name]

        # Cas d'égalité
        if list(self.vote_counts.values()).count(max_votes) > 1:
            print("⚖️ Égalité des votes ! Personne n'est lynché.")
            self.vote_counts = {}
            return

        lynch_target = next(
            (p for p in alive_players if p.name == lynch_target_name), None
        )
        if lynch_target:
            lynch_target.is_alive = False
            print(
                f"\n🔥 {lynch_target.name} est lynché avec {max_votes} votes. "
                f"Son rôle était {lynch_target.role.name}."
            )
            if lynch_target.role.name == "Chasseur":
                print("CHASSEUR ACTIF : Tuer quelqu'un...")

        self.vote_counts = {}


# --- BLOC D'EXÉCUTION DE TEST -----------------------------------------------


if __name__ == "__main__":
    print("--- Préparation des contextes ---")
    if not os.path.exists("context"):
        os.makedirs("context")
        for i in range(1, 10):
            with open(f"context/perso_{i}.txt", "w", encoding="utf-8") as f:
                f.write(
                    f"Tu es l'IA {i} avec la personnalité {i}. "
                    f"Tu dois répondre de manière concise."
                )

    # Petit test de ChatAgent isolé
    class TestRole(Role):
        def __init__(self, name, camp, night_action: NightAction = NightAction.NONE):
            super().__init__(name, camp, night_action)

    lucia_agent = ChatAgent(
        name="Lucia_Test",
        personality_context_path="context/perso_1.txt",
        is_human=False,
    )
    lucia_agent.assign_role(
        TestRole(name="Villageois", camp=Camp.VILLAGEOIS)
    )

    print("\n--- Démarrage de la Simulation Loup Garou ---")
    game = GameManager(human_player_name="Humain_Lucie")
    game.start_game()

# game_core.py (FINAL)

# -*- coding: utf-8 -*-
import random
import time 
import os
from enum import Enum # Garder Enum ici si utilisé dans Player ou GameManager
# --- Importations de base ---
from enums_and_roles import Camp, NightAction, Role, ROLES_POOL 
from chat_agent import ChatAgent # L'IA

# --- CLASSE PLAYER (NON IA) ---

class Player:
    """Représente un joueur humain (ou IA, mais ChatAgent hérite de celle-ci)."""
    def __init__(self, name, is_human=True):
        self.name = name
        self.is_human = is_human
        self.role = None
        self.is_alive = True
        self.has_kill_potion = False
        self.has_life_potion = False

    def assign_role(self, role):
        self.role = role
    
    def __repr__(self):
        status = "Vivant" if self.is_alive else "Mort"
        return f"[{'Humain' if self.is_human else 'IA'}] {self.name} ({self.role.name if self.role else 'N/A'} - {status})"


# --- CLASSE GAMEMANAGER (VERSION COMPLÈTE UNIQUE) ---

class GameManager:
    """Gère le déroulement et la logique du jeu."""
    
    DEBATE_TIME_LIMIT = 180 # 3 minutes en secondes
    
    def __init__(self, human_player_name="Humain_Lucie"):
        
        self.day = 0
        self.players = [] 
        self.available_roles = list(ROLES_POOL.values())
        
        # Lancement des méthodes de setup
        self._setup_players(human_player_name)
        self._distribute_roles()
        
        # Initialisation des compteurs
        self.wolves_alive = sum(1 for p in self.players if p.role.camp == Camp.LOUP and p.is_alive)
        self.vote_counts = {} 
    
    
    # --- METHODES DE SETUP ET GETTERS ---
    
    def _setup_players(self, human_player_name):
        """Initialise les 9 IA et le joueur humain."""
        ia_names = [f"IA {i+1}" for i in range(9)]
        personality_paths = [f"context/perso_{i+1}.txt" for i in range(9)]
        random.shuffle(personality_paths) 
        
        self.players = []
        for name, path in zip(ia_names, personality_paths):
            self.players.append(ChatAgent(name=name, personality_context_path=path, is_human=False))
            
        self.players.append(Player(name=human_player_name, is_human=True))

    def _distribute_roles(self, custom_roles=None):
        """Distribue aléatoirement les rôles aux joueurs."""
        roles_to_distribute = custom_roles if custom_roles else list(self.available_roles)
        if len(self.players) != len(roles_to_distribute):
             raise ValueError("Le nombre de joueurs doit correspondre au nombre de rôles disponibles.")

        random.shuffle(roles_to_distribute)

        for player in self.players:
            role = roles_to_distribute.pop()
            player.assign_role(role)
            
            if role.name == "Sorcière":
                player.has_kill_potion = True
                player.has_life_potion = True
                
            if not player.is_human:
                player.history.append({
                    "role": "system",
                    "content": f"TON RÔLE ACTUEL DANS LA PARTIE EST: {role.name}. Tu es dans le camp des {role.camp.value}."
                })
            print(f"Rôle assigné à {player.name}: {player.role.name}") # Garder pour le log initial
            
    def get_alive_players(self):
        """Retourne la liste des joueurs vivants."""
        return [p for p in self.players if p.is_alive]

    def _get_public_status(self):
        """Retourne l'état public des joueurs pour le prompt des IA."""
        return [{'name': p.name, 'is_alive': p.is_alive} for p in self.players]

    def check_win_condition(self):
        """Vérifie si un camp a gagné."""
        alive = self.get_alive_players()
        wolves = sum(1 for p in alive if p.role.camp == Camp.LOUP)
        villagers = sum(1 for p in alive if p.role.camp == Camp.VILLAGEOIS)
        
        if wolves == 0:
            return Camp.VILLAGEOIS
        if wolves >= villagers:
            return Camp.LOUP
        return None

    # --- NOUVELLE LOGIQUE DE JEU (CYCLES) ---

    def start_game(self):
        """Lance le cycle de jeu principal."""
        print("\n--- Début du Jeu ---")
        
        while self.check_win_condition() is None:
            self.day += 1
            print(f"\n=================== Jour {self.day} ===================")
            
            self._night_phase() 
            self._day_phase()

            self.wolves_alive = sum(1 for p in self.players if p.role.camp == Camp.LOUP and p.is_alive)
            
            winner = self.check_win_condition()
            if winner:
                print(f"\n🎉 Victoire des {winner.value} après {self.day} jours! Loups restants: {self.wolves_alive}")
                return

    # --- Phase de Nuit ---

    def _night_phase(self):
        """Orchestre les actions secrètes des joueurs (Voyante, Loup, Sorcière...)."""
        print("\n🌙 La nuit tombe. Les joueurs ferment les yeux...")
        
        alive = self.get_alive_players()
        
        ordered_actions = {
            NightAction.INVESTIGATE: [],
            NightAction.KILL: [],
            NightAction.POTION: [],
        }
        
        for p in alive:
            if p.role.night_action in ordered_actions:
                ordered_actions[p.role.night_action].append(p)

        kill_target = None
        
        # 1. Action de la Voyante (INVESTIGATE)
        for voyante in ordered_actions[NightAction.INVESTIGATE]:
            if not voyante.is_human:
                target_name = voyante.decide_night_action(alive)
                target = next((p for p in alive if p.name == target_name), None)
                if target:
                    voyante.history.append({
                        "role": "system", 
                        "content": f"Tu as vu que {target.name} est un(e) {target.role.name} ({target.role.camp.value}). Utilise cette info dans le débat."
                    })
                    print(f"🔮 La Voyante ({voyante.name}) a enquêté sur {target.name}.")
                
        # 2. Action des Loups (KILL)
        wolves_acting = ordered_actions[NightAction.KILL]
        if wolves_acting:
            if not wolves_acting[0].is_human:
                target_name = wolves_acting[0].decide_night_action(alive)
                kill_target = next((p for p in alive if p.name == target_name), None)
                if kill_target:
                    print(f"🐺 Les Loups ciblent {kill_target.name}.")

        # 3. Action de la Sorcière (POTION)
        sorciere = next((p for p in alive if p.role.name == "Sorcière"), None)
        if sorciere:
            pass # Logique de potion à implémenter
            
        # Exécution de l'élimination
        if kill_target and kill_target.is_alive:
            kill_target.is_alive = False
            print(f"❌ {kill_target.name} est mort(e).")
        
    # --- Phase de Jour (Débat et Vote) ---

    def _day_phase(self):
        """Gère le débat, les délibérations limitées par le temps et le lynchage."""
        print("\n☀️ Le jour se lève. Débat et lynchage.")
        alive = self.get_alive_players()
        self.vote_counts = {}

        self._debate_phase(alive)
        self._voting_phase(alive)
        self._lynch_result(alive)

    def _debate_phase(self, alive_players):
        """Gère les messages publics des IA pendant le temps imparti."""
        print(f"\n💬 Le débat commence (max {self.DEBATE_TIME_LIMIT}s simulées).")
        start_time = time.time()
        
        for i in range(5): 
            if time.time() - start_time > self.DEBATE_TIME_LIMIT:
                 print("\n⏱️ FIN DU TEMPS DE DÉLIBÉRATION.")
                 break
            
            speaker = random.choice(alive_players)
            
            if not speaker.is_human:
                debate_message = speaker.generate_debate_message(self._get_public_status())
            else:
                debate_message = "Je suis innocent(e) !" 
            
            print(f"🗣️ {speaker.name}: {debate_message}")
            
            for listener in [p for p in alive_players if not p.is_human and p != speaker]:
                listener.receive_public_message(speaker.name, debate_message)
            
            time.sleep(0.5) 

    def _voting_phase(self, alive_players):
        """Collecte les votes de tous les joueurs (IA et Humain)."""
        print("\n🗳️ Place au vote !")
        
        for voter in alive_players:
            if not voter.is_human:
                voted_name = voter.decide_vote(self._get_public_status(), debate_summary="Récapitulatif des accusations...")
            else:
                voted_name = random.choice([p.name for p in alive_players if p != voter])
            
            if voted_name in [p.name for p in alive_players]:
                self.vote_counts[voted_name] = self.vote_counts.get(voted_name, 0) + 1
                print(f"   -> {voter.name} vote pour {voted_name}")
            else:
                pass

    def _lynch_result(self, alive_players):
        """Détermine la victime du lynchage et gère l'élimination."""
        
        if not self.vote_counts:
            print("Personne n'a voté. Le village est confus.")
            return

        lynch_target_name = max(self.vote_counts, key=self.vote_counts.get)
        max_votes = self.vote_counts[lynch_target_name]
        
        if list(self.vote_counts.values()).count(max_votes) > 1:
            print("⚖️ Égalité des votes ! Personne n'est lynché.")
            return
            
        lynch_target = next((p for p in alive_players if p.name == lynch_target_name), None)
        if lynch_target:
            lynch_target.is_alive = False
            print(f"\n🔥 {lynch_target.name} est lynché avec {max_votes} votes. Son rôle était {lynch_target.role.name}.")
            
            if lynch_target.role.name == "Chasseur":
                print("CHASSEUR ACTIF : Tuer quelqu'un...") 
        
        self.vote_counts = {}


# --- BLOC D'EXÉCUTION DU TEST ---

if __name__ == "__main__":
    
    print("--- Préparation des contextes ---")
    if not os.path.exists("context"):
        os.makedirs("context")
        for i in range(1, 10):
            with open(f"context/perso_{i}.txt", "w", encoding="utf-8") as f:
                f.write(f"Tu es l'IA {i} avec la personnalité {i}. Tu dois répondre de manière concise.")
    
    # Création d'un rôle pour le test simple de ChatAgent
    class TestRole(Role):
         def __init__(self, name, camp, night_action=NightAction.NONE):
             super().__init__(name, camp, night_action)

    lucia_agent = ChatAgent(name="Lucia_Test", personality_context_path="context/perso_1.txt", is_human=False)
    lucia_agent.assign_role(TestRole(name="Villageois", camp=Camp.VILLAGEOIS))


    print("\n--- Démarrage de la Simulation Loup Garou ---")
    game = GameManager(human_player_name="Humain_Lucie")
    game.start_game()
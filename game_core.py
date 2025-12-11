# game_core.py (VERSION CORRIGÉE)

# -*- coding: utf-8 -*-
import random
import time 
import os 

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
    
    DEBATE_TIME_LIMIT = 120 
    
    def __init__(self, human_player_name="Humain_Lucie"):
        
        self.day = 0
        self.players = [] 
        self.available_roles = list(ROLES_POOL.values())
        
        self._setup_players(human_player_name)
        self._distribute_roles()
        
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
            
        # NOTE: Le ChatAgent hérite de Player, donc on peut utiliser Player ici
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
                # Ajout du rôle au contexte interne de l'IA
                player.history.append({
                    "role": "system",
                    "content": f"TON RÔLE ACTUEL DANS LA PARTIE EST: {role.name}. Tu es dans le camp des {role.camp.value}."
                })
            
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

    # --- Phase de Nuit ---

    def _night_phase(self):
        """Orchestre les actions secrètes des joueurs (Voyante, Loup, Sorcière...)."""
        
        alive = self.get_alive_players()
        self.day += 1 
        
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
        
        # 2. Action des Loups (KILL)
        wolves_acting = ordered_actions[NightAction.KILL]
        if wolves_acting:
            if not wolves_acting[0].is_human:
                target_name = wolves_acting[0].decide_night_action(alive)
                kill_target = next((p for p in alive if p.name == target_name), None)
        
        # Exécution de l'élimination
        if kill_target and kill_target.is_alive:
            kill_target.is_alive = False
            return f"❌ {kill_target.name} est mort(e) pendant la nuit. Rôle: {kill_target.role.name}."
        return "Nuit passée, personne n'est mort."


    # --- Phase de Jour (Vote) ---

    def _day_phase(self):
        """Lance le cycle complet du jour : vote IA, résultat, et lynchage (si l'humain est mort)."""
        alive = self.get_alive_players()
        self.vote_counts = {}
        
        # Le vote des IA est géré ici
        self._voting_phase_ia_only() 
        
        # Résultat du Vote et Élimination
        result = self._lynch_result(alive)
        return result

    def register_human_vote(self, voted_player_name):
        """Enregistre le vote du joueur humain pour le lynchage."""
        self.vote_counts[voted_player_name] = self.vote_counts.get(voted_player_name, 0) + 1
        
        # Après le vote humain, on demande aux IA restantes de voter
        self._voting_phase_ia_only() 

    def _voting_phase_ia_only(self):
        """Collecte les votes des IA (déclenché par la fin du débat ou par le vote humain)."""
        alive_players = self.get_alive_players()
        
        # La logique de vote de l'IA doit être déclenchée ici
        for voter in alive_players:
            if not voter.is_human and voter.is_alive:
                # L'IA utilise l'historique mis à jour (qui inclut le chat humain) pour décider
                voted_name = voter.decide_vote(self._get_public_status(), debate_summary="Récapitulatif des accusations...")
                
                # Enregistrer le vote
                if voted_name in [p.name for p in alive_players]:
                     self.vote_counts[voted_name] = self.vote_counts.get(voted_name, 0) + 1

    def _lynch_result(self, alive_players):
        """Détermine la victime du lynchage et gère l'élimination."""
        
        if not self.vote_counts:
            return "Personne n'a voté. Le village est confus."

        lynch_target_name = max(self.vote_counts, key=self.vote_counts.get)
        max_votes = self.vote_counts[lynch_target_name]
        
        if list(self.vote_counts.values()).count(max_votes) > 1:
            self.vote_counts = {}
            return f"⚖️ Égalité des votes ! Personne n'est lynché (Max votes: {max_votes})."
            
        lynch_target = next((p for p in alive_players if p.name == lynch_target_name), None)
        
        if lynch_target:
            lynch_target.is_alive = False
            message = f"🔥 {lynch_target.name} est lynché avec {max_votes} votes. Rôle: {lynch_target.role.name}."
            
            if lynch_target.role.name == "Chasseur":
                message += "\nCHASSEUR ACTIF : Tuer quelqu'un..." 
        
        self.vote_counts = {}
        return message

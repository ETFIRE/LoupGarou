# game_core.py

# -*- coding: utf-8 -*-
import random
import time 
import os 

# --- Importations de base ---
from enums_and_roles import Camp, NightAction, Role, ROLES_POOL 
from chat_agent import ChatAgent

# LISTE DE NOMS
IA_NAMES_POOL = [
    "Oui Capitaine !", 
    "Oggy", 
    "Zinzin",
    "Gertrude",
    "Queeny",
    "Domi",
    "Patrick",
    "La cheloue",
    "?",
    "L'Ami",
]


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
        self.wolf_teammates = [] 
        self.has_hunter_shot = True

    def assign_role(self, role):
        self.role = role
    
    def __repr__(self):
        status = "Vivant" if self.is_alive else "Mort"
        return f"[{'Humain' if self.is_human else 'IA'}] {self.name} ({self.role.name if self.role else 'N/A'} - {status})"


# --- CLASSE GAMEMANAGER (VERSION COMPLÈTE UNIQUE) ---

class GameManager:
    """Gère le déroulement et la logique du jeu."""
    
    DEBATE_TIME_LIMIT = 20 # 20 secondes pour le débat
    
    def __init__(self, human_player_name="Humain_Lucie"):
        
        self.day = 0
        self.players = [] 
        self.available_roles = list(ROLES_POOL.values())
        
        self.human_player = None 
        
        self._setup_players(human_player_name)
        
        self.human_player = next((p for p in self.players if p.is_human), None)
        
        self._distribute_roles()
        
        self._recalculate_wolf_count() 
        self.vote_counts = {} 

    
    # --- METHODES DE SETUP ET GETTERS ---
    
    def _setup_players(self, human_player_name):
        """Initialise les 9 IA avec des noms et des contextes aléatoires."""
        
        CONTEXT_DIR = "context" 
        
        if not os.path.isdir(CONTEXT_DIR):
             raise FileNotFoundError(f"Le dossier de contexte '{CONTEXT_DIR}' est introuvable. Créez-le et ajoutez les fichiers perso_*.txt.")
             
        all_perso_paths = [
            os.path.join(CONTEXT_DIR, f) 
            for f in os.listdir(CONTEXT_DIR) 
            if f.endswith('.txt') and f.startswith('perso_')
        ]
        
        NUM_IA = 9
        if len(all_perso_paths) < NUM_IA:
             raise ValueError(f"Seulement {len(all_perso_paths)} personnalités trouvées, {NUM_IA} sont nécessaires.")
        
        selected_perso_paths = random.sample(all_perso_paths, NUM_IA)
        
        if len(IA_NAMES_POOL) < NUM_IA:
             raise ValueError("Le pool de noms doit contenir au moins 9 noms uniques.")
             
        ia_names = random.sample(IA_NAMES_POOL, NUM_IA)
        
        self.players = []
        
        for name, path in zip(ia_names, selected_perso_paths):
            self.players.append(ChatAgent(name=name, personality_context_path=path, is_human=False))
            
        self.players.append(Player(name=human_player_name, is_human=True))

    def _distribute_roles(self, custom_roles=None):
        """Distribue aléatoirement les rôles aux joueurs et informe les Loups."""
        roles_to_distribute = custom_roles if custom_roles else list(self.available_roles)
        if len(self.players) != len(roles_to_distribute):
             raise ValueError("Le nombre de joueurs doit correspondre au nombre de rôles disponibles.")

        random.shuffle(roles_to_distribute)

        # 1. Distribution initiale et ajout du rôle au contexte de chaque IA
        for player in self.players:
            role = roles_to_distribute.pop()
            player.assign_role(role)
            
            # Initialisation des potions/capacités
            if role.name == "Sorcière":
                player.has_kill_potion = True
                player.has_life_potion = True
            elif role.name == "Chasseur":
                player.has_hunter_shot = True
            
            if not player.is_human:
                # Ajout du rôle au contexte interne de l'IA
                player.history.append({
                    "role": "system",
                    "content": f"TON RÔLE ACTUEL DANS LA PARTIE EST: {role.name}. Tu es dans le camp des {role.camp.value}."
                })
        
        # --- LOGIQUE : INFORMER TOUS LES LOUPS ---
        
        # 2. Identification de TOUS les Loups (après que tous les rôles soient assignés)
        all_wolves = [p for p in self.players if p.role.camp == Camp.LOUP]
        all_wolf_names = [p.name for p in all_wolves]
        
        for p in all_wolves:
            co_wolves = [name for name in all_wolf_names if name != p.name]
            
            # 3. Informer chaque Loup-Garou IA
            if not p.is_human:
                if co_wolves: 
                    wolf_list_str = ", ".join(co_wolves)
                    p.history.append({
                        "role": "system",
                        "content": f"TES COÉQUIPIERS LOUPS-GAROUS SONT : {wolf_list_str}. Ne les trahis jamais. Travaillez ensemble pour tuer les villageois."
                    })
            
            # 4. Stocker la liste des coéquipiers pour le Joueur Humain (pour l'affichage UI)
            else: # p is human (le loup est le joueur humain)
                 p.wolf_teammates = co_wolves 
        
        # --- FIN LOGIQUE LOUPS ---

    def _recalculate_wolf_count(self):
        """Recalcule le nombre de loups vivants et met à jour l'attribut."""
        self.wolves_alive = sum(1 for p in self.players if p.role.camp == Camp.LOUP and p.is_alive)
            
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
        """Orchestre les actions secrètes des joueurs (Voyante, Loup, Sorcière, Petite Fille...)."""
        
        alive = self.get_alive_players()
        self.day += 1 
        
        pf_revelation = "" # Message de révélation pour la Petite Fille Humaine (si applicable)
        
        # --- NOUVEAU : Logique Petite Fille Humaine Nuit 1 (Découverte) ---
        if self.human_player and self.human_player.role and self.human_player.role.name == "Petite Fille":
            alive_wolves = [p for p in alive if p.role.camp == Camp.LOUP]
            if alive_wolves:
                # Select a random alive wolf
                discovered_wolf = random.choice(alive_wolves)
                pf_revelation = f"\n🔍 PETITE FILLE : Tu as découvert que **{discovered_wolf.name}** est un Loup-Garou ! Utilise cette information avec sagesse."
            else:
                pf_revelation = "\n🔍 PETITE FILLE : Il ne reste plus de Loups-Garous à découvrir."
        # --- FIN NOUVEAU ---
        
        # FIX: S'il s'agit de la Nuit 1, aucune mort n'est possible (Nuit Blanche)
        if self.day == 1:
            
            # Exécution de la Voyante (INVESTIGATE) - doit rester pour donner l'info à l'IA
            for voyante in [p for p in alive if p.role.night_action == NightAction.INVESTIGATE]:
                if not voyante.is_human:
                    target_name = voyante.decide_night_action(alive)
                    target = next((p for p in alive if p.name == target_name), None)
                    if target:
                        voyante.history.append({
                            "role": "system", 
                            "content": f"Tu as vu que {target.name} est un(e) {target.role.name} ({target.role.camp.value}). Utilise cette info dans le débat."
                        })
            
            # Les Loups choisissent une cible, mais l'exécution est ignorée.
            self._recalculate_wolf_count()
            return "🌙 Première nuit passée. Le village se réveille sans drame !" + pf_revelation

        
        # --- LOGIQUE POUR NUIT 2 et suivantes ---
        
        ordered_actions = {
            NightAction.INVESTIGATE: [],
            NightAction.KILL: [],
            NightAction.WATCH: [], 
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
        
        # 3. Action de la Petite Fille IA (WATCH) - Elle voit la cible des Loups
        if kill_target:
            for petite_fille in ordered_actions[NightAction.WATCH]:
                 if not petite_fille.is_human:
                     # L'IA Petite Fille est informée de la cible
                     petite_fille.history.append({
                         "role": "system", 
                         "content": f"Tu as vu les Loups cibler {kill_target.name} cette nuit. Utilise cette information cruciale."
                     })
                     
        is_saved = False # Flag de sauvetage
        
        # 4. Action de la Sorcière (POTION)
        sorciere = next((p for p in alive if p.role.name == "Sorcière"), None)
        
        if sorciere and sorciere.is_alive and kill_target:
            
            # Vérification de la potion de vie (Sauvetage)
            if sorciere.has_life_potion:
                
                # Logique IA normale
                if not sorciere.is_human:
                    # La Sorcière IA a 50% de chance de sauver si la cible n'est pas un Loup
                    if kill_target.role.camp != Camp.LOUP and random.random() < 0.5:
                        is_saved = True
                        sorciere.has_life_potion = False # Utilisation de la potion
        
        # Exécution de l'élimination
        if kill_target and kill_target.is_alive:
            if is_saved:
                self._recalculate_wolf_count()
                return f"✅ {kill_target.name} a été attaqué(e) mais sauvé(e) par la Sorcière !" + pf_revelation
            else:
                # Élimination confirmée
                kill_target.is_alive = False 
                self._recalculate_wolf_count()
                return f"❌ {kill_target.name} est mort(e) pendant la nuit. Rôle: {kill_target.role.name}." + pf_revelation

        self._recalculate_wolf_count()
        return "Nuit passée, personne n'est mort." + pf_revelation


    # --- Phase de Jour (Vote) ---

    def _day_phase(self):
        """Lance le cycle complet du jour : vote IA, résultat, et lynchage (si l'humain est mort)."""
        alive = self.get_alive_players()
        self.vote_counts = {}
        
        self._voting_phase_ia_only() 
        
        result = self._lynch_result(alive)
        return result

    def register_human_vote(self, voted_player_name):
        """Enregistre le vote du joueur humain pour le lynchage."""
        self.vote_counts[voted_player_name] = self.vote_counts.get(voted_player_name, 0) + 1
        
        self._voting_phase_ia_only() 

    def _voting_phase_ia_only(self):
        """Collecte les votes des IA (déclenché par la fin du débat ou par le vote humain)."""
        alive_players = self.get_alive_players()
        
        for voter in alive_players:
            if not voter.is_human and voter.is_alive:
                voted_name = voter.decide_vote(self._get_public_status(), debate_summary="Récapitulatif des accusations...")
                
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
        
        hunter_eliminated_target = None
        
        if lynch_target:
            lynch_target.is_alive = False
            
            # --- LOGIQUE DU CHASSEUR ---
            if lynch_target.role.name == "Chasseur" and lynch_target.has_hunter_shot:
                
                # Le Chasseur tire. Il choisit une cible aléatoire parmi les survivants.
                survivors = [p for p in self.get_alive_players() if p != lynch_target] 
                
                if survivors:
                    hunter_eliminated_target = random.choice(survivors)
                    hunter_eliminated_target.is_alive = False
                    lynch_target.has_hunter_shot = False # Action utilisée
                    self._recalculate_wolf_count() 

            self._recalculate_wolf_count() # Mise à jour du compte après la première mort
            
            message = f"🔥 {lynch_target.name} est lynché avec {max_votes} votes. Rôle: {lynch_target.role.name}."
            
            # Message additionnel du Chasseur
            if hunter_eliminated_target:
                message += f"\n🏹 CHASSEUR ACTIF : Il emporte {hunter_eliminated_target.name} (Rôle: {hunter_eliminated_target.role.name}) dans sa chute !" 
        else:
            message = "Erreur: Cible de lynchage invalide."
        
        self.vote_counts = {}
        return message
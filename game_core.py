# game_core.py

# -*- coding: utf-8 -*-
import random
import time 
import os 
from collections import defaultdict 
import json 

# --- Importations de base ---
from enums_and_roles import Camp, NightAction, Role 
# ASSUMPTION: La classe ChatAgent existe et est importable
try:
    from chat_agent import ChatAgent
except ImportError:
    # Classe factice pour éviter l'erreur si ChatAgent n'est pas dans le même répertoire
    class ChatAgent(object):
        # La méthode __init__ DOIT correspondre à ce qui est appelé dans _create_player_instance.
        def __init__(self, name, personality_context_path):
            self.name = name
            self.is_human = False
            self.role = None
            self.is_alive = True
            self.has_kill_potion = False
            self.has_life_potion = False
            self.wolf_teammates = []
            self.has_hunter_shot = True
            self.last_protected_target = None
            self.is_ancient_protected = False
            self.history = []
        def assign_role(self, role): self.role = role
        def receive_public_message(self, speaker, message): pass
        def decide_night_action(self, alive_players): return random.choice([p.name for p in alive_players if p.name != self.name])
        def generate_debate_message(self, public_status): return "Je pense que nous devrions être prudents."
        def decide_vote(self, public_status, debate_summary): 
            alive_names = [p['name'] for p in public_status if p['is_alive'] and p['name'] != self.name]
            return random.choice(alive_names) if alive_names else None


# LISTE DE NOMS ALÉATOIRES POUR LES IA
IA_NAMES_POOL = [
    "Oui Capitaine !", 
    "Oggy", 
    "Zinzin",
    "Gertrude",
    "Queeny",
    "Domi",
    "Patrick",
    "La Mystérieuse",
    "L'Interrogateur", 
    "L'Ami",
    "Faucheuse",
    "YesGirl",
    "Personne",
    "Félix le chat",
    "Indominous",
]


# --- CLASSE PLAYER (NON IA) ---

class Player:
    """Représente un joueur humain (ou la base pour ChatAgent)."""
    def __init__(self, name, role, is_human=False):
        self.name = name
        self.is_human = is_human
        self.role = role
        self.is_alive = True
        self.has_kill_potion = False
        self.has_life_potion = False
        self.wolf_teammates = [] 
        self.has_hunter_shot = True
        self.last_protected_target = None
        self.is_ancient_protected = False

    def assign_role(self, role):
        self.role = role
        if role == Role.ANCIEN:
            self.is_ancient_protected = True
    
    def __repr__(self):
        status = "Vivant" if self.is_alive else "Mort"
        return f"[{'Humain' if self.is_human else 'IA'}] {self.name} ({self.role.name if self.role else 'N/A'} - {status})"


# --- CLASSE GAMEMANAGER ---

class GameManager:
    """Gère le déroulement et la logique du jeu."""
    
    DEBATE_TIME_LIMIT = 20
    
    def __init__(self, human_player_name="Lucie", num_players_total=11):
        
        self.day = 0
        self.players = [] 
        self.num_players_total = num_players_total
        
        # Rôles fixes/spéciaux requis pour la partie
        self.base_roles = [
            Role.LOUP, Role.LOUP, Role.LOUP,
            Role.VOYANTE, Role.SORCIERE, Role.CHASSEUR, 
            Role.CUPIDON, 
            Role.MAIRE, 
            Role.SALVATEUR, 
            Role.ANCIEN,
        ]
        
        self.ancient_shield_triggered = False

        self.hunter_just_shot = False
        
        self.available_roles = self._adjust_roles() 
        
        self.human_player = None 
        
        self._setup_players(human_player_name) 
        
        self.human_player = next((p for p in self.players if p.is_human), None)
        
        self._distribute_roles()
        
        self._recalculate_wolf_count() 
        self.vote_counts = defaultdict(int)
        
        # --- Attributs de Nuit globaux ---
        self.is_cupid_phase_done = False
        self.lovers = None 
        self.night_kill_target = None 
        self.night_protected_target = None 
        # -----------------------------------

    
    # --- METHODES DE SETUP ET GETTERS ---
    
    def _create_player_instance(self, name, role, is_human):
        """Crée une instance Player ou ChatAgent."""
        if is_human:
            return Player(name, is_human=True)
        else:
            # Création du chemin de contexte unique pour chaque IA
            context_path = os.path.join("context", f"{name.replace(' ', '_').lower()}.txt") 
            
            # S'assurer que le fichier de contexte existe
            if not os.path.exists("context"):
                os.makedirs("context")
                
            if not os.path.exists(context_path):
                 with open(context_path, "w", encoding="utf-8") as f:
                    f.write(f"Tu es l'IA {name}. Ton rôle est d'être un joueur de Loup Garou. Réponds de manière concise.")
            
            # Appel Corrigé : Passe 'name' et l'argument obligatoire 'personality_context_path'
            return ChatAgent(name, personality_context_path=context_path) 


    def _adjust_roles(self):
        """Ajuste la liste finale des rôles en ajoutant/retirant des Villageois."""
        
        roles_list = list(self.base_roles)
        num_base_roles = len(roles_list)
        
        if num_base_roles > self.num_players_total:
            raise ValueError(
                f"Nombre de joueurs trop faible ({self.num_players_total}). "
                f"Minimum requis: {num_base_roles} pour les rôles spéciaux."
            )
            
        required_villagers = self.num_players_total - num_base_roles
        
        for _ in range(required_villagers):
            roles_list.append(Role.VILLAGEOIS)
            
        # On retourne les valeurs brutes de l'Enum pour la compatibilité avec le reste du code
        return [r.value for r in roles_list] 
        
    def _setup_players(self, human_player_name):
        """Initialise la liste des joueurs (IA et Humain) avec attribution de rôles."""
        num_ia = self.num_players_total - 1
        
        # 1. Préparer et mélanger les noms d'IA
        random.shuffle(IA_NAMES_POOL)
        ia_names = IA_NAMES_POOL[:num_ia]
        
        # 2. Générer la liste des rôles pour toute la partie et la mélanger
        # On suppose que vous avez une méthode _generate_roles qui renvoie une liste d'objets Role
        roles_pool = self._generate_roles(self.num_players_total)
        random.shuffle(roles_pool)
        
        # 3. Créer le joueur humain avec le premier rôle de la liste
        human_role = roles_pool.pop()
        self.human_player = Player(human_player_name, role=human_role, is_human=True)
        self.players.append(self.human_player)
        
        # 4. Création des IA
        for name in ia_names:
            if not roles_pool:
                break
            ia_role = roles_pool.pop()
            self.players.append(self._create_player_instance(name, ia_role, is_human=False))
        
    def _generate_roles(self, total_players):
        """Génère une liste de rôles équilibrée pour la partie."""
        roles = []
        
        # 1. Ajout des Loups (environ 1/4 ou 1/3 des joueurs)
        num_wolves = 3 if total_players >= 10 else 2
        for _ in range(num_wolves):
            roles.append(Role.LOUP)
            
        # 2. Ajout des rôles spéciaux indispensables
        mandatory_roles = [
            Role.VOYANTE, 
            Role.SORCIERE, 
            Role.CHASSEUR, 
            Role.CUPIDON, 
            Role.SALVATEUR,
            Role.ANCIEN
        ]
        
        for r in mandatory_roles:
            if len(roles) < total_players:
                roles.append(r)
                
        # 3. Remplir le reste avec des Villageois simples si nécessaire
        while len(roles) < total_players:
            roles.append(Role.VILLAGEOIS)
            
        return roles

    def _distribute_roles(self):
        """Distribue aléatoirement les rôles aux joueurs et informe les Loups."""
        roles_to_distribute = [Role(r) for r in self.available_roles] 
        if len(self.players) != len(roles_to_distribute):
             raise ValueError("Le nombre de joueurs doit correspondre au nombre de rôles disponibles.")

        random.shuffle(roles_to_distribute)

        # 1. Distribution initiale et ajout du rôle au contexte de chaque IA
        for player in self.players:
            role = roles_to_distribute.pop()
            player.assign_role(role)
            
            # Initialisation des capacités/potions
            if role == Role.SORCIERE:
                player.has_kill_potion = True
                player.has_life_potion = True
            elif role == Role.CHASSEUR:
                player.has_hunter_shot = True
            
            if not player.is_human:
                player.history.append({
                    "role": "system",
                    "content": f"TON RÔLE ACTUEL DANS LA PARTIE EST: {role.name}. Tu es dans le camp des {role.camp.value}."
                })
        
        # --- LOGIQUE : INFORMER TOUS LES LOUPS ---
        all_wolves = [p for p in self.players if p.role.camp == Camp.LOUP]
        all_wolf_names = [p.name for p in all_wolves]
        
        for p in all_wolves:
            co_wolves = [name for name in all_wolf_names if name != p.name]
            
            if not p.is_human:
                if co_wolves: 
                    wolf_list_str = ", ".join(co_wolves)
                    p.history.append({
                        "role": "system",
                        "content": f"TES COÉQUIPIERS LOUPS-GAROUS SONT : {wolf_list_str}. Ne les trahis jamais. Travaillez ensemble pour tuer les villageois."
                    })
            
            else: 
                 p.wolf_teammates = co_wolves 
        
    def _recalculate_wolf_count(self):
        """Recalcule le nombre de loups vivants et met à jour l'attribut."""
        self.wolves_alive = sum(1 for p in self.players if p.role.camp == Camp.LOUP and p.is_alive)
            
    def get_alive_players(self):
        """Retourne la liste des joueurs vivants."""
        return [p for p in self.players if p.is_alive]
        
    def get_player_by_name(self, name):
        """Retourne un joueur par son nom."""
        return next((p for p in self.players if p.name == name), None)
        
    def get_player_by_role(self, role_enum):
        """Retourne le joueur ayant ce rôle (le premier trouvé)."""
        return next((p for p in self.players if p.role == role_enum), None)

    def _get_public_status(self):
        """Retourne l'état public des joueurs pour le prompt des IA."""
        return [{'name': p.name, 'is_alive': p.is_alive} for p in self.players]

    def check_win_condition(self):
        """Vérifie si un camp a gagné."""
        alive = self.get_alive_players()
        wolves = sum(1 for p in alive if p.role.camp == Camp.LOUP)
        villagers = sum(1 for p in alive if p.role.camp == Camp.VILLAGE)
        
        if wolves == 0:
            return Camp.VILLAGE
        if wolves >= villagers:
            return Camp.LOUP
        return None
        
    # --- Logique de Mort Centralisée ---
    def _kill_player(self, target_player_name, reason="tué par les Loups"):
        """
        Tue un joueur et gère l'effet de mort en chaîne du Chasseur et du Cupidon.
        Retourne le message de mort complet.
        """
        
        target = self.get_player_by_name(target_player_name)
        if not target or not target.is_alive:
            return f"{target_player_name} n'a pas pu être tué."
            
        target.is_alive = False
        message = f"❌ {target.name} est mort(e) ({reason}). Rôle: {target.role.name}."
        
        hunter_eliminated_target = None

        if target.role == Role.ANCIEN and target.is_ancient_protected and "lynché" not in reason:
            self.ancient_shield_triggered = True
            target.is_ancient_protected = False
            
            return f"🌟 **L'ANCIEN** a été attaqué, mais son totem de protection lui a sauvé la vie cette fois ! Il est désormais vulnérable."
        
        # S'il survit, on sort de la fonction sans le tuer ni activer les effets de mort.
        if target.role == Role.ANCIEN and not target.is_ancient_protected and "lynché" not in reason:
            # S'il a déjà utilisé son jeton, il meurt normalement et active les effets.
            pass

        target.is_alive = False
        message = f"❌ {target.name} est mort(e) ({reason}). Rôle: {target.role.name}."
        
        # 1. LOGIQUE DU CHASSEUR
        if target.role == Role.CHASSEUR and target.has_hunter_shot:
            survivors = [p for p in self.get_alive_players() if p.name != target.name] 
            
            if survivors:
                self.hunter_just_shot = True
                hunter_eliminated_target = random.choice(survivors)
                # Utilisation de _kill_player pour gérer la mort en chaîne
                self._kill_player(hunter_eliminated_target.name, reason="emporté(e) par le Chasseur")
                target.has_hunter_shot = False 
                message += f"\n🏹 CHASSEUR ACTIF : Il emporte {hunter_eliminated_target.name} (Rôle: {hunter_eliminated_target.role.name}) dans sa chute !"
        
        # 2. LOGIQUE DU CUPIDON (Mort en chaîne)
        if self.lovers and target_player_name in self.lovers:
            # Trouver le partenaire
            partner_name = self.lovers[0] if target_player_name == self.lovers[1] else self.lovers[1]
            partner = self.get_player_by_name(partner_name)
            
            if partner and partner.is_alive:
                # Appel récursif pour tuer le partenaire
                self._kill_player(partner_name, reason="mort de chagrin d'amour")
                message += f"\n💖 COUPLE CASSÉ : Suite à la mort de {target.name}, {partner_name} est mort(e) de chagrin."
        
        self._recalculate_wolf_count()
        return message

    # --- Phase d'Action Cupidon ---
    def _handle_cupid_phase(self, human_choice=None):
        """Gère l'action du Cupidon pendant la première nuit (avant tout autre action)."""
        if self.is_cupid_phase_done:
            return "La phase Cupidon est terminée."

        cupidon = self.get_player_by_role(Role.CUPIDON)

        if not cupidon or not cupidon.is_alive:
            self.is_cupid_phase_done = True
            return "Pas de Cupidon ou Cupidon mort. Phase ignorée."

        # Logique Humain
        if cupidon.is_human and human_choice and len(human_choice.split(',')) == 2:
            target1_name, target2_name = human_choice.split(',')
            self.lovers = (target1_name.strip(), target2_name.strip())
            self.is_cupid_phase_done = True
            return f"💖 {cupidon.name} a lié {self.lovers[0]} et {self.lovers[1]}."
        
        # Logique IA
        elif not cupidon.is_human:
            potential_targets = [p.name for p in self.players] 
            if len(potential_targets) >= 2:
                love_targets = random.sample(potential_targets, 2)
                self.lovers = (love_targets[0], love_targets[1])
                self.is_cupid_phase_done = True
                return f"💖 Cupidon (IA) a lié {self.lovers[0]} et {self.lovers[1]}."
            
        return "Action Cupidon en attente ou erreur de sélection."
    # ----------------------------------------


    # --- Phase de Nuit ---

    def _night_phase(self):
        """Orchestre les actions secrètes des joueurs."""
        from collections import defaultdict
        import random

        alive = self.get_alive_players()
        night_messages = []
    
        # 1. NUIT BLANCHE (aucune mort ou action spéciale la Nuit 1)
        if self.day == 1:
            night_messages.append("🌙 Première nuit passée. Le village se réveille sans drame !")
            self._recalculate_wolf_count()
            return "\n".join(night_messages)
            # --- LOGIQUE POUR NUIT 2 et suivantes ---
        actions_by_priority = defaultdict(list)
        for p in alive:
            if p.role and p.role.night_action != NightAction.NONE:
                actions_by_priority[p.role.priority].append(p)
        sorted_priorities = sorted(actions_by_priority.keys())
    
        self.night_kill_target = None
        self.night_protected_target = None 
        is_saved_by_witch = False 
    
        for priority in sorted_priorities:
            for player in actions_by_priority[priority]:
            
                # A. Logique VOYANTE (INVESTIGATE) - Priorité 20
                if player.role.night_action == NightAction.INVESTIGATE and not player.is_human:
                    target_name = player.decide_night_action(alive)
                    target = self.get_player_by_name(target_name)
                    if target:
                        player.history.append({
                            "role": "system", 
                            "content": f"Tu as vu que {target.name} est un(e) {target.role.name} ({target.role.camp.value})."
                        })
            
                # B. Logique SALVATEUR (PROTECT) - Priorité 25
                elif player.role.night_action == NightAction.PROTECT:
                    target_name = None
                
                    if player.is_human:
                        # On récupère le choix stocké via l'interface
                        target_name = getattr(self, 'human_choice', None)
                    else:
                        # IA : On cherche une cible valide (pas celle de la nuit précédente)
                        last_protected = getattr(player, 'last_protected_target', None)
                        targets_available = [p.name for p in alive if p.name != last_protected]
                        if targets_available:
                            target_name = random.choice(targets_available)

                    # Validation et application de la protection
                    if target_name:
                        # Double vérification de la règle (surtout pour l'humain)
                        if target_name != getattr(player, 'last_protected_target', None):
                            self.night_protected_target = target_name
                            player.last_protected_target = target_name
                        else:
                            # Si l'humain a triché ou erreur : pas de protection cette nuit
                            pass

                # C. Logique LOUPS (KILL) - Priorité 30
                elif player.role.night_action == NightAction.KILL and player.role.camp == Camp.LOUP:
                    if not self.night_kill_target:
                        if not player.is_human:
                            t_name = player.decide_night_action(alive)
                        else:
                            # Loup humain
                            t_name = getattr(self, 'human_choice', None)
                        self.night_kill_target = self.get_player_by_name(t_name)

        # 3. Résolution du Meurtre des Loups
        kill_target = self.night_kill_target
        if kill_target:
            # Vérification Protection SALVATEUR
            if kill_target.name == self.night_protected_target:
                night_messages.append(f"🛡️ **{kill_target.name}** a été attaqué(e) mais **sauvé(e) par le Salvateur** !")
                kill_target = None # On annule la mort
            else:
                # Logique SORCIERE (POTION) - Priorité 40
                sorciere = self.get_player_by_role(Role.SORCIERE)
                if sorciere and sorciere.is_alive:
                    # Sorcière IA
                    if not sorciere.is_human and getattr(sorciere, 'has_life_potion', False):
                        if kill_target.role.camp != Camp.LOUP and random.random() < 0.5:
                            is_saved_by_witch = True
                            sorciere.has_life_potion = False 
                            night_messages.append(f"✅ {kill_target.name} a été sauvé(e) par la Sorcière !")
                
                    # Sorcière Humaine (vérification du choix 'SAUVER')
                    elif sorciere.is_human and getattr(self, 'human_action_type', None) == "SAUVER":
                        if getattr(sorciere, 'has_life_potion', False):
                            is_saved_by_witch = True
                            sorciere.has_life_potion = False
                            night_messages.append(f"✅ Vous avez utilisé votre potion pour sauver {kill_target.name} !")
                # Exécution finale de la mort si non sauvé
                if not is_saved_by_witch:
                    message_mort = self._kill_player(kill_target.name, reason="tué par les Loups")
                    night_messages.append(message_mort)
                    self.last_death_was_by_wolf = True
                else:
                    self.last_death_was_by_wolf = False

        self._recalculate_wolf_count()
        # On réinitialise les choix humains pour la nuit suivante
        self.human_choice = None
        self.human_action_type = None

        return "\n".join(night_messages) if night_messages else "La nuit a été calme."
    
    
    # --- Phase de Jour (Vote) ---

    def _day_phase(self):
        """Lance le cycle complet du jour : vote IA, résultat, et lynchage (si l'humain est mort)."""
        alive = self.get_alive_players()
        self.vote_counts = defaultdict(int)
        
        self._voting_phase_ia_only() 
        
        result = self._lynch_result(alive)
        return result

    def register_human_vote(self, voted_player_name):
        """Enregistre le vote du joueur humain pour le lynchage."""
        if self.human_player.is_alive:
            self.vote_counts[voted_player_name] += 1
        
        self._voting_phase_ia_only() 

    def _voting_phase_ia_only(self):
        """Collecte les votes des IA (déclenché par la fin du débat ou par le vote humain)."""
        alive_players = self.get_alive_players()
        
        for voter in alive_players:
            if not voter.is_human and voter.is_alive:
                voted_name = voter.decide_vote(self._get_public_status(), debate_summary="Récapitulatif des accusations...")
                
                if voted_name and voted_name in [p.name for p in alive_players]:
                     self.vote_counts[voted_name] += 1

    def _lynch_result(self, alive_players):
        if not self.vote_counts:
            # Sécurité pour éviter le crash de max() sur un dictionnaire vide
            return "Le village n'a pas réussi à se mettre d'accord. Personne n'est lynché."

        # --- LOGIQUE MAIRE (Double Vote) ---
        mayor_player = self.get_player_by_role(Role.MAIRE)
        mayor_name = mayor_player.name if mayor_player and mayor_player.is_alive else None
        
        mayor_message = ""
        if mayor_name and mayor_player.is_alive:
            
            # --- Simplification: Si l'humain est le maire ---
            if self.human_player.role == Role.MAIRE and self.human_player.is_alive:
                
                human_vote_target = next((name for name, count in self.vote_counts.items() if count % 2 != 0), None)
                
                if human_vote_target:
                    self.vote_counts[human_vote_target] += 1 
                    mayor_message = f"🗳️ **Le vote du Maire ({mayor_player.name}) a été doublé.** "
                else:
                    mayor_message = f"🗳️ **Le Maire ({mayor_player.name}) n'a pas voté ce tour.** "

            # --- Si l'IA est le maire ---
            elif not self.human_player.role == Role.MAIRE and mayor_player.is_alive:
                 mayor_message = f"🗳️ **Le Maire ({mayor_player.name}) est vivant.** "


        # ---------------------------------------------
        
        lynch_target_name = max(self.vote_counts, key=self.vote_counts.get)
        max_votes = self.vote_counts[lynch_target_name]
        
        if list(self.vote_counts.values()).count(max_votes) > 1:
            self.vote_counts.clear()
            return f"⚖️ Égalité des votes ! Personne n'est lynché (Max votes: {max_votes}). {mayor_message}"
            
        # Élimination via la méthode centralisée
        message = self._kill_player(lynch_target_name, reason="lynché(e) par le village")
        
        self.vote_counts.clear()
        # On ajoute le message du Maire au début du résultat du lynchage
        return mayor_message + message
# enums_and_roles.py

from enum import Enum 

# --- Camps (Factions) ---
class Camp(Enum):
    VILLAGE = "Villageois"
    LOUP = "Loups-Garous"
    SOLO = "Solitaire" # Non utilisé pour l'instant, mais bonne pratique

# --- Actions de Nuit Possibles ---
class NightAction(Enum):
    NONE = 0
    KILL = 1         # Loup-Garou
    INVESTIGATE = 2  # Voyante
    POTION = 3       # Sorcière
    PAIR = 4         # Cupidon (NOUVEAU)

# --- Définition des Rôles et de leurs Attributs ---
class Role(Enum):
    # --- Villageois Simples ---
    VILLAGEOIS = {
        "name": "Villageois",
        "camp": Camp.VILLAGE,
        "night_action": NightAction.NONE,
        "priority": 0
    }
    
    # --- Loups-Garous ---
    LOUP = {
        "name": "Loup-Garou",
        "camp": Camp.LOUP,
        "night_action": NightAction.KILL,
        "priority": 30
    }
    
    # --- Villageois Spéciaux (Phase de Nuit Active) ---
    VOYANTE = {
        "name": "Voyante",
        "camp": Camp.VILLAGE,
        "night_action": NightAction.INVESTIGATE,
        "priority": 20
    }
    
    SORCIERE = {
        "name": "Sorcière",
        "camp": Camp.VILLAGE,
        "night_action": NightAction.POTION,
        "priority": 40
    }
    
    # --- Villageois Spéciaux (Phase de Nuit Passive) ---
    CHASSEUR = {
        "name": "Chasseur",
        "camp": Camp.VILLAGE,
        "night_action": NightAction.NONE, # L'action du chasseur est déclenchée à sa mort
        "priority": 0
    }
    
    # --- NOUVEAU RÔLE : Cupidon ---
    CUPIDON = {
        "name": "Cupidon",
        "camp": Camp.VILLAGE,
        "night_action": NightAction.PAIR,  # Action spécifique de la première nuit
        "priority": 10
    }
    
    # --- NOUVEAU RÔLE : Maire ---
    MAIRE = {
        "name": "Maire",
        "camp": Camp.VILLAGE,
        "night_action": NightAction.NONE, # L'action est pendant le jour (vote)
        "priority": 0
    }
    

    # --- Pour faciliter la gestion des rôles IA ---
    @property
    def name(self):
        return self.value["name"]

    @property
    def camp(self):
        return self.value["camp"]

    @property
    def night_action(self):
        return self.value["night_action"]
        
    @property
    def priority(self):
        return self.value["priority"]
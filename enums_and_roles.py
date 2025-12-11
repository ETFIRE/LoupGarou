# enums_and_roles.py

from enum import Enum

class Camp(Enum):
    LOUP = "Loup-Garou"
    VILLAGEOIS = "Villageois"

class NightAction(Enum):
    NONE = "Aucune"
    INVESTIGATE = "Enquête"  # Voyante
    KILL = "Meurtre"        # Loup-Garou
    POTION = "Potion"       # Sorcière
    WATCH = "Observation"   # NOUVEAU: Petite Fille

class Role:
    def __init__(self, name, camp, night_action=NightAction.NONE):
        self.name = name
        self.camp = camp
        self.night_action = night_action

# Définition des Rôles utilisés dans la partie (10 joueurs)
ROLES_POOL = {
    "LoupGarou1": Role("Loup-Garou", Camp.LOUP, NightAction.KILL),
    "LoupGarou2": Role("Loup-Garou", Camp.LOUP, NightAction.KILL),
    "LoupGarou3": Role("Loup-Garou", Camp.LOUP, NightAction.KILL),
    
    "Voyante": Role("Voyante", Camp.VILLAGEOIS, NightAction.INVESTIGATE),
    "Sorciere": Role("Sorcière", Camp.VILLAGEOIS, NightAction.POTION),
    "Chasseur": Role("Chasseur", Camp.VILLAGEOIS),
    "PetiteFille": Role("Petite Fille", Camp.VILLAGEOIS, NightAction.WATCH), # <-- NOUVEAU
    "Villageois1": Role("Villageois", Camp.VILLAGEOIS),
    "Villageois2": Role("Villageois", Camp.VILLAGEOIS),
    "Villageois3": Role("Villageois", Camp.VILLAGEOIS),
}
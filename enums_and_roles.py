# -*- coding: utf-8 -*-
from enum import Enum

class Camp(Enum):
    """Définit le camp du joueur pour la condition de victoire."""
    VILLAGEOIS = 'Villageois'
    LOUP = 'Loup-Garou'
    SOLO = 'Solo'

class NightAction(Enum):
    """Définit l'action de nuit associée à un rôle."""
    KILL = 'Tuer'
    INVESTIGATE = 'Enquêter'
    POTION = 'Potions'
    VOTE_LEADER = 'Vote Leader'
    NONE = 'Aucune'

class Role:
    """Représente un rôle avec ses propriétés de jeu."""
    def __init__(self, name, camp, night_action=NightAction.NONE):
        self.name = name
        self.camp = camp
        self.night_action = night_action

    def __repr__(self):
        return f"{self.name} ({self.camp.value})"

# Définition de l'ensemble des rôles (ROLES_POOL pour 10 joueurs)
ROLES_POOL = {
    # Loups (3)
    "Loup Garou A": Role("Loup Garou", Camp.LOUP, NightAction.KILL),
    "Loup Garou B": Role("Loup Garou", Camp.LOUP, NightAction.KILL),
    "Loup Garou C": Role("Loup Garou", Camp.LOUP, NightAction.KILL),
    
    # Villageois (7)
    "Voyante": Role("Voyante", Camp.VILLAGEOIS, NightAction.INVESTIGATE),
    "Sorcière": Role("Sorcière", Camp.VILLAGEOIS, NightAction.POTION),
    "Chasseur": Role("Chasseur", Camp.VILLAGEOIS),
    "Petite Fille": Role("Petite Fille", Camp.VILLAGEOIS, NightAction.NONE),
    "Chef du Village": Role("Chef du Village", Camp.VILLAGEOIS, NightAction.VOTE_LEADER),
    "Villageois Simple 1": Role("Simple Villageois", Camp.VILLAGEOIS),
    "Villageois Simple 2": Role("Simple Villageois", Camp.VILLAGEOIS),
}
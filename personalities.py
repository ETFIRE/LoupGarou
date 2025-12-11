# Dans GameManager._setup_players ou _distribute_roles : j assignes d’abord le rôle.

# Ensuite je choisis une personnalité adaptée via ce mapping et passes le bon context_path au ChatAgent 
# ce code constitue un gros pool de personnalités variées,
# un mapping préférences de rôle → types de personnalités,
# une fonction utilitaire pour tirer une personnalité avec biais mais pas déterministe,
# une version maj de _distribute_roles dans GameManager.

import random


class Personality:
    def __init__(self, name, context_path):
        self.name = name              # "Mentaliste", "Streameuse Drama", etc.
        self.context_path = context_path

    def __repr__(self):
        return f"Personality({self.name})"


# === POOL GLOBAL DE PERSONNALITÉS (drôles + réalistes) ===
PERSONALITIES_POOL = [
    # Sérieux / stratégiques
    Personality("Enquêteur Froid", "context/perso_enqueteur_froid.txt"),
    Personality("Analyste Logique", "context/perso_analyste_logique.txt"),
    Personality("Capitaine de Police", "context/perso_capitaine_police.txt"),
    Personality("Avocat de la Défense", "context/perso_avocat_defense.txt"),
    Personality("Procureur Agressif", "context/perso_procureur_agressif.txt"),

    # Mystiques / occultes
    Personality("Médium Mystique", "context/perso_medium_mystique.txt"),
    Personality("Médium Cynique", "context/perso_medium_cynique.txt"),
    Personality("Occultiste Fatigué", "context/perso_occultiste_fatigue.txt"), 
    
    ]
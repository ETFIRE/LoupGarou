
import random


class Personality:
    def __init__(self, name, context_path):
        self.name = name            
        self.context_path = context_path

    def __repr__(self):
        return f"Personality({self.name})"


# POOL GLOBAL DE PERSONNALITÉS
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
    
     # Réseaux sociaux / drama
    Personality("Streameuse Drama", "context/perso_streameuse_drama.txt"),
    Personality("Influenceuse Insta", "context/perso_influenceuse_insta.txt"),
    Personality("Tiktokeuse Occulte", "context/perso_tiktokeuse_occulte.txt"),
    Personality("Community Manager", "context/perso_community_manager.txt"),

    # Comiques / chaotiques
    Personality("Comique de Service", "context/perso_comique_service.txt"),
    Personality("Meme Lord", "context/perso_meme_lord.txt"),
    Personality("Drama Queen", "context/perso_drama_queen.txt"),
    Personality("Troll du Village", "context/perso_troll_village.txt"),
    
     # Intellos / vieux sages
    Personality("Philosophe Existentialiste", "context/perso_philosophe_existentialiste.txt"),
    Personality("Prof d'Histoire", "context/perso_prof_histoire.txt"),
    Personality("Scientifique Cartésien", "context/perso_scientifique_cartesien.txt"),
    Personality("Prof de Maths Aigri", "context/perso_prof_maths_aigri.txt"),
    
     # Autres archétypes
    Personality("Journaliste d'Investigation", "context/perso_journaliste_investigation.txt"),
    Personality("Journaliste à Scandales", "context/perso_journaliste_scandales.txt"),
    Personality("Cowboy Nerveux", "context/perso_cowboy_nerveux.txt"),
    Personality("Vétéran de Guerre", "context/perso_veteran_guerre.txt"),
    Personality("Artiste Maudit", "context/perso_artiste_maudit.txt"),
    Personality("Aventurier Bavard", "context/perso_aventurier_bavard.txt"),
    Personality("Naïf", "context/perso_naif.txt"),
    Personality("Sceptique", "context/perso_sceptique.txt"),
    Personality("Timide", "context/perso_timide.txt"),
    Personality("Blagueur Lourd", "context/perso_blagueur_lourd.txt"),
    
    ]

ROLE_TO_PERSONALITIES = {
    "Sorcière": [
        "Médium Mystique",
        "Médium Cynique",
        "Tiktokeuse Occulte",
        "Occultiste Fatigué",
    ],
    "Voyante": [
        "Médium Mystique",
        "Médium Cynique",
        "Philosophe Existentialiste",
        "Journaliste d'Investigation",
    ],
    "Chef du Village": [
        "Philosophe Existentialiste",
        "Analyste Logique",
        "Capitaine de Police",
        "Maire Populiste",  
    ],
    "Loup Garou": [
        "Troll du Village",
        "Meme Lord",
        "Streameuse Drama",
        "Journaliste à Scandales",
        "Blagueur Lourd",
    ],
    "Simple Villageois": [
        "Naïf",
        "Sceptique",
        "Comique de Service",
        "Timide",
    ],
    "Petite Fille": [
        "Curieuse",
        "Influenceuse Insta",
        "Drama Queen",
        "Naïf",
    ],
    "Chasseur": [
        "Cowboy Nerveux",
        "Justicier",
        "Vétéran de Guerre",
    ],
    
}


def get_personality_by_name(name: str) -> Personality | None:
    """Retrouve un objet Personality à partir de son nom"""
    for p in PERSONALITIES_POOL:
        if p.name == name:
            return p
    return None


def pick_personality_for_role(role_name: str, bias_probability: float = 0.6) -> Personality:
    """
    Tire une personnalité pour un rôle donné
    - Avec 'bias_probability' on privilégie une personnalité parmi la liste ROLE_TO_PERSONALITIES[role_name]
      si elle existe 60% du temps
    - Le reste du temps, on pioche au hasard dans le pool global
    Résultat : difficile d'associer 'rôle = personnalité' pour les joueurs humains
    """
    preferred_names = ROLE_TO_PERSONALITIES.get(role_name, [])

    use_bias = preferred_names and (random.random() < bias_probability)

    if use_bias:
       
        chosen_name = random.choice(preferred_names)
        personality = get_personality_by_name(chosen_name)
        if personality:
            return personality

    
    return random.choice(PERSONALITIES_POOL)

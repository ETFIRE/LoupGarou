🐺 Loup-Garou IA - Arcade Edition 🌙
Ce projet est une simulation du jeu de rôle Loup-Garou (Werewolf/Mafia) où 9 joueurs IA aux personnalités distinctes affrontent un joueur humain dans une interface graphique interactive construite avec Python Arcade.

Les débats, les accusations et les votes sont animés par des modèles de langage (LLM) configurés pour être stratégiques, agressifs et imprévisibles.

🌟 Fonctionnalités Clés
10 Joueurs : 1 Humain vs. 9 IA.

Personnalités Dynamiques : À chaque partie, les 9 IA reçoivent un nom aléatoire et un rôle de personnalité unique (Drama Queen, Analyste Logique, Cowboy Nerveux, etc.) provenant du dossier /context.

Rôles de Jeu Complets : Implémentation des rôles clés (Voyante, Sorcière, Chasseur, Petite Fille) et de leurs actions nocturnes.

Interface Intuitive :

Journal de Bord (Gauche) : Historique complet et permanent des événements et messages.

Chat Actif (Droite) : Affichage de la frappe en temps réel de l'IA, persistant jusqu'à la prochaine prise de parole.

Équilibrage Stratégique :

Nuit 1 Blanche : Aucune mort n'est possible lors de la première nuit.

Voyante Agressive : L'IA Voyante est forcée de partager ses découvertes de Loups-Garous dans le débat pour alerter le village.

Accessibilité : Identification visuelle des alliés Loups-Garous (nom en couleur) si le joueur humain est lui-même un Loup.

🚀 Démarrage et Installation
Prérequis
Python (version 3.8+)

Une clé API Groq (pour le modèle Llama)

1. Cloner le Dépôt & Installer les Dépendances
Assurez-vous que tous les fichiers (.py, .env, context/) sont dans le même répertoire.

Bash

# Installation des librairies via le fichier requirements.txt
pip install -r requirements.txt
2. Configuration de l'API (Clé Groq)
Ce projet utilise l'API Groq pour le modèle llama-3.3-70b-versatile.

Obtenez votre clé API sur le site de Groq.

Créez un fichier nommé .env à la racine de votre projet.

Ajoutez votre clé API Groq dans ce fichier :

Extrait de code

# .env
GROQ_KEY="gsk_votre_clé_secrète_groq_ici"
3. Lancer le Jeu
Bash

python loup_garou_arcade.py
Le jeu démarrera en état SETUP. Cliquez sur "COMMENCER LA PARTIE" pour lancer la Nuit 1.

Rôle,Camp,Action Humaine de Nuit,Règle Spécifique
Voyante,Villageois,NUIT - OUI (Enquêter sur un joueur : Révèle immédiatement le rôle).,L'IA est forcée de partager les Loups découverts en débat.
Sorcière,Villageois,NUIT - OUI (Tuer/Sauver : via boutons d'intention).,Possède une potion de vie et une potion de mort (utilisables une fois).
Chasseur,Villageois,NUIT - NON,"S'il est lynché, il tire aléatoirement sur un autre joueur encore en vie."
Petite Fille,Villageois,NUIT - NON (Passe son tour).,L'humain découvre l'identité d'un Loup-Garou vivant à chaque nuit.
Loup-Garou,Loup-Garou,NUIT - NON (L'IA choisit la cible d'élimination).,Le joueur voit les noms de ses alliés en jaune.
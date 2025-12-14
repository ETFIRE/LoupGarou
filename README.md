🐺 Loup-Garou IA - Arcade Edition 🌙
Ce projet est une simulation du jeu de rôle Loup-Garou (Werewolf/Mafia) où 10 joueurs IA aux personnalités distinctes affrontent un joueur humain dans une interface graphique interactive construite avec Python Arcade.

Les débats, les accusations et les votes sont animés par des modèles de langage (LLM) configurés pour être stratégiques, agressifs et imprévisibles.

🌟 Fonctionnalités Clés
11 Joueurs : 1 Humain vs. 10 IA (pour intégrer l'Ancien).

Personnalités Dynamiques : À chaque partie, les IA reçoivent un nom aléatoire et un rôle de personnalité unique (Drama Queen, Analyste Logique, Cowboy Nerveux, etc.) provenant du dossier /context.

Rôles de Jeu Avancés : Implémentation des rôles clés pour un jeu équilibré : Voyante, Sorcière, Chasseur, Cupidon, Maire, Salvateur et Ancien.

Logique Rôles Spéciaux :

Maire : Le vote du Maire compte double lors du lynchage de jour.

Salvateur : Peut protéger un joueur par nuit, mais ne peut pas protéger la même cible deux nuits de suite, ni se protéger lui-même.

Ancien : Survit à la première attaque nocturne (sauf s'il est lynché de jour).

Interface Intuitive :

Journal de Bord (Gauche) : Historique complet et permanent des événements et messages.

Chat Actif (Centre) : Affichage de la frappe en temps réel de l'IA, persistant jusqu'à la prochaine prise de parole.

Équilibrage Stratégique :

Nuit 1 Blanche : Aucune mort n'est possible lors de la première nuit.

Voyante Agressive : L'IA Voyante est forcée de partager les Loups découverts dans le débat pour alerter le village.

Accessibilité : Identification visuelle des alliés Loups-Garous (nom en couleur) si le joueur humain est lui-même un Loup.

Rôle,Camp,Action Humaine de Nuit,Règle Spécifique
Voyante,Villageois,OUI (Enquêter sur un joueur : Révèle immédiatement le rôle).,L'IA est forcée de partager les Loups découverts en débat.
Sorcière,Villageois,OUI (Tuer/Sauver : via boutons d'intention).,Possède une potion de vie et une potion de mort (utilisables une fois chacune).
Salvateur,Villageois,OUI (Protéger un joueur).,"Ne peut pas se protéger, ni protéger la même cible deux nuits de suite."
Cupidon,Villageois,OUI (Première nuit : Lier deux joueurs).,Le couple meurt ensemble.
Maire,Villageois,NON (Vote de Jour).,Son vote compte double lors du lynchage.
Ancien,Villageois,NON,Survit à la première attaque de nuit (sauf s'il est lynché).
Chasseur,Villageois,NON,"S'il est éliminé, il tire aléatoirement sur un autre joueur encore en vie."
Loup-Garou,Loup-Garou,NON (L'IA choisit la cible d'élimination).,Le joueur humain voit les noms de ses alliés Loups.
Villageois,Villageois,NON,Simple villageois.


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

Plaintext

# .env
GROQ_KEY="gsk_votre_clé_secrète_groq_ici"
3. Lancer le Jeu
Bash

python loup_garou_arcade.py
Le jeu démarrera en état SETUP. Cliquez sur "COMMENCER LA PARTIE" pour lancer la Nuit 1 (phase Cupidon/Action Humaine de Nuit).



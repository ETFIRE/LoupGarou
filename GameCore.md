# Game Core

Fonctions Globales / Classe Factice (`ChatAgent`)

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, name, personality_context_path)` | Initialise les attributs de la classe factice (base pour l'IA). |
| `assign_role(self, role)` | Attribue un rôle (méthode de la classe factice). |
| `receive_public_message(self, speaker, message)` | Enregistre un message public (méthode de la classe factice). |
| `decide_night_action(self, alive_players)` | Choisit une cible d'action de nuit aléatoire (méthode de la classe factice). |
| `generate_debate_message(self, public_status)` | Génère un message de débat simple (méthode de la classe factice). |
| `decide_vote(self, public_status, debate_summary)` | Choisit un joueur à voter de manière aléatoire (méthode de la classe factice). |

 Classe `Player`

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, name, is_human=True)` | Initialise un joueur (principalement utilisé pour le joueur humain), y compris les attributs de rôle/statut. |
| `assign_role(self, role)` | Attribue un rôle au joueur et active les capacités initiales spécifiques (ex: protection de l'Ancien). |
| `__repr__(self)` | Représentation en chaîne de caractères du joueur (pour le débogage/log). |

Classe `GameManager`

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, human_player_name="Lucie", num_players_total=11)` | Constructeur. Initialise les rôles, les joueurs, distribue les rôles, et initialise les compteurs de vote et les attributs de nuit. |
| `_create_player_instance(self, name, role, is_human)` | Crée une instance `Player` (pour l'humain) ou `ChatAgent` (pour l'IA), s'assurant que les fichiers de contexte IA existent. |
| `_adjust_roles(self)` | Ajuste la liste des rôles de la partie en ajoutant des `VILLAGEOIS` pour atteindre le nombre total de joueurs. |
| `_setup_players(self, human_player_name)` | Crée l'instance du joueur humain et les instances des joueurs IA (`ChatAgent`). |
| `_distribute_roles(self)` | Distribue les rôles mélangés aux joueurs et informe secrètement tous les Loups-Garous de leurs coéquipiers. |
| `_recalculate_wolf_count(self)` | Recalcule et met à jour le nombre de loups vivants. |
| `get_alive_players(self)` | Retourne la liste des objets joueurs qui sont encore vivants. |
| `get_player_by_name(self, name)` | Recherche et retourne un joueur par son nom. |
| `get_player_by_role(self, role_enum)` | Recherche et retourne le joueur associé à un rôle spécifique. |
| `_get_public_status(self)` | Retourne une liste simplifiée de l'état des joueurs (nom, statut vivant/mort) pour le prompt des IA. |
| `check_win_condition(self)` | Vérifie si les conditions de victoire des Loups (`Camp.LOUP`) ou des Villageois (`Camp.VILLAGE`) sont remplies. |
| `_kill_player(self, target_player_name, reason="tué par les Loups")` | Méthode centralisée pour la mort. Tue un joueur, gère la protection de l'Ancien, et déclenche la mort en chaîne du Chasseur et de Cupidon. |
| `_handle_cupid_phase(self, human_choice=None)` | Gère l'action du Cupidon pendant la première nuit, en acceptant le choix humain ou en le décidant par IA. |
| `_night_phase(self)` | Orchestre l'ensemble des actions de nuit (Voyante, Salvateur, Loups, Sorcière), en respectant la priorité et les protections. |
| `_day_phase(self)` | Lance le cycle complet du jour pour le lynchage (principalement utilisé lorsque l'humain est mort ou absent). |
| `register_human_vote(self, voted_player_name)` | Enregistre le vote du joueur humain, puis collecte immédiatement les votes IA. |
| `_voting_phase_ia_only(self)` | Collecte les votes de l'ensemble des joueurs IA. |
| `_lynch_result(self, alive_players)` | Détermine le joueur lynché par le vote (gère l'égalité et le double vote du Maire) et exécute la mort via `_kill_player`. |
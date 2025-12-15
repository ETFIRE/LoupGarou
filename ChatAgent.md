# Chat Agent

Classe `Player` (Classe de Base)

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, name, is_human=False)` | Initialise les attributs de base du joueur (nom, statut humain/IA, rôle, statut de vie, possessions spécifiques aux rôles). |
| `assign_role(self, role)` | Attribue un rôle au joueur et initialise les attributs spécifiques à ce rôle (ex: protection de l'Ancien). |

Classe `ChatAgent` (Hérite de `Player`)

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, name, personality_context_path, is_human=False)` | Constructeur. Initialise l'agent IA, la connexion à l'API Groq, le chemin du contexte de personnalité, et lance l'initialisation de l'historique. |
| `initiate_history(self)` | Initialise ou réinitialise l'historique de chat de l'agent en chargeant le contexte de personnalité du fichier et en créant les instructions système pour le LLM. |
| `_read_file(file_path)` | **Méthode Statique.** Lit le contenu d'un fichier spécifié (utilisé pour lire le contexte de personnalité). |
| `_update_history(self, role, content)` | Ajoute une nouvelle interaction (`user` ou `assistant`) à l'historique de chat isolé de l'agent. |
| `_normalize_history(self, history_to_normalize)` | Convertit l'historique pour s'assurer que les messages multimodaux (non supportés par ce modèle LLM) sont représentés par du texte. |
| `ask_llm(self, user_interaction)` | Mode Texte Simple. Envoie l'interaction au LLM (via Groq), met à jour l'historique avec la réponse de l'IA et la retourne. |
| `receive_public_message(self, sender_name, message)` | Enregistre un message du débat public dans l'historique de l'IA (en tant qu'interaction `user`) pour influencer ses futures réponses. |
| `_prompt_llm_for_decision(self, prompt, model)` | Fonction utilitaire interne pour obtenir une réponse concise du LLM, utilisée pour les actions de nuit et les votes. |
| `decide_night_action(self, alive_players)` | Demande au LLM de choisir une cible pour son action de nuit spécifique (Loup, Salvateur, etc.), en tenant compte des exclusions de règles. |
| `decide_vote(self, public_status, debate_summary)` | Demande au LLM de choisir sa victime pour le vote de lynchage de jour, en fonction de son rôle et des arguments du débat. |
| `generate_debate_message(self, current_game_status)` | Génère un message de débat public court et percutant de l'IA, en priorisant la défense si elle est accusée, ou l'attaque/révélation d'une preuve si elle ne l'est pas. |
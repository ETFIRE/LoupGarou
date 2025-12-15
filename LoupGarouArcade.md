# Loup Garou

Fonctions Globales

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `main()` | Fonction principale pour lancer l'application Arcade, gère la saisie du nom du joueur et du nombre de joueurs. |

Classe `MenuButton`

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, center_x, center_y, width, height, text, action)` | Initialise un bouton avec sa position, sa taille, son texte et son action. |
| `draw(self)` | Dessine le bouton à l'écran avec une couleur basée sur son texte/action. |
| `check_click(self, x, y)` | Vérifie si les coordonnées de la souris sont à l'intérieur du bouton. |

Classe `ChatInput`

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, x, y, width, height, game_instance)` | Initialise le champ de saisie du chat et les références aux boutons Envoyer/STT. |
| `draw(self)` | Dessine le champ de saisie, le texte qu'il contient et le curseur clignotant. |
| `update_position(self, x, y, width)` | Met à jour la position et la taille du champ de saisie (appelé lors du redimensionnement de la fenêtre). |
| `handle_key_press(self, symbol, modifiers)` | Gère la saisie au clavier (ajout/suppression de caractères, envoi avec **ENTER**). |
| `send_message(self)` | Envoie le message saisi par l'humain au log et aux IA, puis réinitialise le champ. |
| `check_click(self, x, y)` | Gère l'activation du champ de saisie par clic et le clic sur le bouton Envoyer. |

 Classe `LoupGarouGame` (Hérite de `arcade.Window`)

| **Nom de la Fonction** | **Rôle / Description** |
| --- | --- |
| `__init__(self, width, height, title, human_name="Lucie", num_players_total=11)` | Constructeur. Initialise la fenêtre, charge les ressources, initialise le moteur de jeu, et les variables d'état/affichage. |
| `_setup_ui_elements(self)` | Initialise ou recalcule la position des éléments d'interface utilisateur (chat input, boutons Envoyer/STT). |
| `_setup_sprites(self)` | Crée les objets visuels (`arcade.Sprite`) pour chaque joueur, en les positionnant en cercle. |
| `_setup_circle_sprites(self)` | Méthode de secours pour créer des sprites en forme de cercle si les images d'avatars manquent. |
| `start_game_loop(self)` | Initialise l'état du jeu à `SETUP` et affiche le rôle du joueur humain. |
| `_start_night_phase(self)` | Gère la transition entre les actions de nuit humaines et IA (en fonction du jour et du rôle humain). |
| `on_mouse_press(self, x, y, button, modifiers)` | **Gestion des événements de souris.** Traite les clics pour le démarrage, les votes, les actions de nuit, et le chat/STT. |
| `_handle_cupid_selection_click(self, x, y)` | Logique de sélection des deux amoureux par le Cupidon humain. |
| `_display_cupid_selection_indicators(self)` | Dessine les indicateurs de sélection (cercle rose) pour les amoureux et la ligne les reliant. |
| `_handle_stt_toggle(self)` | Démarre ou arrête l'enregistrement vocal (Speech-to-Text). |
| `_listen_for_speech(self)` | S'exécute dans un thread séparé pour enregistrer la parole et la convertir en texte via Google Speech API. |
| `on_resize(self, width, height)` | **Gestion des événements de redimensionnement.** Recalcule les positions des éléments UI et des sprites des joueurs. |
| `on_key_press(self, symbol, modifiers)` | Gère les événements clavier, notamment le chat, le verrouillage des majuscules et le mode plein écran (`F`). |
| `on_draw(self)` | **Fonction de rendu.** Dessine tous les éléments du jeu (fond, joueurs, log, boutons, chat). |
| `draw_localized_chat_bubble(self)` | Dessine la bulle de texte flottante sous le joueur IA qui est en train de parler. |
| `on_update(self, delta_time)` | **Fonction de logique de jeu (boucle principale).** Gère les transitions d'état (`NIGHT_IA_ACTION`, `DEBATE`, `VOTING`, `RESULT`). |
| `_display_human_night_action_buttons(self)` | Prépare les boutons d'action de nuit spécifiques (Voyante: **ENQUÊTER**, Sorcière: **TUER/SAUVER**, Salvateur: **PROTÉGER**). |
| `_handle_human_night_action_click(self, x, y)` | Traite le choix du joueur humain pour son action de nuit (applique l'effet et passe à la phase IA). |
| `_update_debate(self, delta_time)` | Gère le minuteur du débat, la vitesse de frappe du message IA et la transition vers le vote. |
| `enter_human_voting_state(self)` | Prépare les boutons pour le vote de lynchage de l'humain. |
| `draw_log(self)` | Dessine le panneau du journal de bord (historique des événements) à gauche de l'écran. |
| `draw_status(self)` | Dessine le panneau d'état (nombre de loups, minuteur) à droite de l'écran. |
# loup_garou_arcade.py

# -*- coding: utf-8 -*-
import arcade
import random
import time
from enum import Enum 
import math
import os
import sys
from dotenv import load_dotenv

# --- NOUVELLES IMPORTATIONS POUR SPEECH-TO-TEXT ---
import speech_recognition as sr
import threading # Nécessaire pour l'écoute non bloquante
# --------------------------------------------------

# Charger les variables d'environnement (y compris GROQ_API_KEY)
load_dotenv() 

# Importation de vos classes de jeu
from game_core import GameManager, Player 
from enums_and_roles import Camp, NightAction, Role # Role importé pour tous les rôles spéciaux

# --- Paramètres de la Fenêtre & États ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

class GameState(Enum):
    SETUP = 1 
    CUPID_ACTION = 15 # ÉTAT POUR L'ACTION CUPIDON
    NIGHT_HUMAN_ACTION = 2 
    NIGHT_IA_ACTION = 3     
    DEBATE = 4
    HUMAN_ACTION = 5     
    VOTING = 6
    RESULT = 7
    GAME_OVER = 8


# --- Bouton Interactif ---
class MenuButton:
    """Classe pour dessiner et gérer les boutons de vote/action."""
    def __init__(self, center_x, center_y, width, height, text, action):
        self.center_x = center_x
        self.center_y = center_y
        self.width = width
        self.height = height
        self.text = text
        self.action = action 

    def draw(self):
        color_map = {
            "ENQUÊTER": arcade.color.PURPLE,
            "TUER": arcade.color.RED_DEVIL,
            "SAUVER": arcade.color.YELLOW_GREEN,
            "PASSER": arcade.color.YELLOW_ORANGE,
            "Voter": arcade.color.DARK_RED,
            "COMMENCER": arcade.color.DARK_GREEN,
            "Envoyer": arcade.color.DARK_CYAN,
            "PROTÉGER": arcade.color.SKY_BLUE, # COULEUR SALVATEUR
            "Parler": arcade.color.DARK_GREEN, # COULEUR STT PAR DEFAUT
            "ARRÊTER": arcade.color.RED_DEVIL, # COULEUR STT EN COURS
            "DEFAULT": arcade.color.DARK_BLUE
        }
        
        base_action = self.text.split()[0]
        # Logique pour choisir la couleur basée sur le texte (y compris Parler/ARRÊTER)
        color = color_map.get(base_action, color_map.get(self.text.split('[')[0].strip(), color_map.get(self.text, color_map["DEFAULT"])))

        arcade.draw_lbwh_rectangle_filled(
            self.center_x - self.width / 2, 
            self.center_y - self.height / 2, 
            self.width, 
            self.height, 
            color
        )
        arcade.draw_text(self.text, self.center_x, self.center_y,
                          arcade.color.WHITE, 12, anchor_x="center", anchor_y="center")

    def check_click(self, x, y):
        """Vérifie si les coordonnées de la souris sont dans le bouton."""
        return (self.center_x - self.width/2 < x < self.center_x + self.width/2 and
                self.center_y - self.height/2 < y < self.center_y + self.height/2) 


# --- Champ de Saisie de Chat ---
class ChatInput:
    """Représente la boîte de saisie de texte pour l'humain."""
    def __init__(self, x, y, width, height, game_instance):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = ""
        self.active = False
        self.game = game_instance
        self.send_button = None 
        self.stt_button = None 

    def draw(self):
        color = arcade.color.WHITE if self.active else arcade.color.LIGHT_GRAY
        arcade.draw_lbwh_rectangle_filled(self.x, self.y, self.width, self.height, color)
        
        cursor = ("|" if self.active and int(time.time() * 2) % 2 == 0 else "")
        arcade.draw_text(self.text + cursor, 
                          self.x + 5, self.y + 5, 
                          arcade.color.BLACK, 14)
        
        if self.send_button:
            self.send_button.draw()
        if self.stt_button: 
             self.stt_button.draw()
            
    def update_position(self, x, y, width):
        """Met à jour la position et la taille après un redimensionnement."""
        self.x = x
        self.y = y
        self.width = width
        
        # Mettre à jour la position des boutons
        if self.send_button:
            self.send_button.center_x = x + width + 45
            self.send_button.center_y = y + self.height / 2
        if self.stt_button:
            self.stt_button.center_x = x + width + 135
            self.stt_button.center_y = y + self.height / 2
            
    def handle_key_press(self, symbol, modifiers):
        if self.active:
            if symbol == arcade.key.ENTER:
                self.send_message()
            elif symbol == arcade.key.BACKSPACE:
                self.text = self.text[:-1]
            else:
                try:
                    char = chr(symbol)
                    if char.isprintable(): 
                        if len(self.text) < 80: 
                            if symbol >= arcade.key.A and symbol <= arcade.key.Z:
                                if modifiers & arcade.key.LSHIFT or modifiers & arcade.key.RSHIFT or self.game.key_is_caps:
                                    self.text += char.upper()
                                else:
                                    self.text += char.lower()
                            elif symbol == arcade.key.SPACE:
                                self.text += ' '
                            else:
                                self.text += char
                            
                except ValueError:
                    pass
                
    def send_message(self):
        if self.text.strip():
            message = self.text.strip()
            
            self.game.log_messages.append(f"🗣️ {self.game.human_player.name} : {message}")
            
            alive_ais = [p for p in self.game.game_manager.get_alive_players() if not p.is_human]
            for listener in alive_ais:
                listener.receive_public_message(self.game.human_player.name, message)
            
            self.text = ""
            self.game.current_speaker = None
            
    def check_click(self, x, y):
        is_in_input = (self.x < x < self.x + self.width and self.y < y < self.y + self.height)
        
        if self.send_button and self.send_button.check_click(x, y):
             self.send_message()
        else:
            self.active = is_in_input


class LoupGarouGame(arcade.Window):
    
    def __init__(self, width, height, title, human_name="Lucie", num_players_total=11):
        # 1. INITIALISATION DE LA FENÊTRE
        super().__init__(width, height, title, resizable=True)
        self.set_fullscreen(True)

        self.sound_start_game = None
        try:
            # Assurez-vous que le fichier start.mp3 ou start.wav existe dans le dossier sounds
            if os.path.exists("sounds/start.mp3"):
                self.sound_start_game = arcade.load_sound("sounds/start.mp3")
        except Exception as e:
            print(f"Erreur chargement son de démarrage : {e}")

        # --- NOUVEAU : GESTION DES SONS ---
        self.sound_wolf_kill = None
        try:
            # On charge le son de mort des loups
            if os.path.exists("sounds/wolf_kill.mp3"):
                self.sound_wolf_kill = arcade.load_sound("sounds/wolf_kill.mp3")
            else:
                print("AVERTISSEMENT : sounds/wolf_kill.mp3 non trouvé.")
        except Exception as e:
            print(f"Erreur lors du chargement du son : {e}")

        self.night_processing = False
        
        # 2. Chargement du fond d'écran
        BACKGROUND_IMAGE_PATH = "images/fond/images.png" 
        self.background_sprite = None
        self.background_list = arcade.SpriteList() 
        
        if os.path.exists(BACKGROUND_IMAGE_PATH):
            self.background_sprite = arcade.Sprite(
                BACKGROUND_IMAGE_PATH,
                scale=1.0 
            )
            self.background_list.append(self.background_sprite) 
            print(f"Fond d'écran chargé comme Sprite.")
        else:
             print(f"ATTENTION : Image de fond non trouvée à '{BACKGROUND_IMAGE_PATH}'.")
             
        # 3. Chargement du Sprite du FEU DE CAMP
        CAMPFIRE_IMAGE_PATH = "images/fond/campfire.png" 
        self.campfire_sprite = None
        self.campfire_list = arcade.SpriteList()
        
        if os.path.exists(CAMPFIRE_IMAGE_PATH):
            self.campfire_sprite = arcade.Sprite(
                CAMPFIRE_IMAGE_PATH,
                scale=0.4 # TAILLE AUGMENTÉE
            )
            self.campfire_list.append(self.campfire_sprite)
        else:
            print(f"ATTENTION : Image du feu de camp non trouvée à '{CAMPFIRE_IMAGE_PATH}'.")


        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        # 4. Initialisation du Moteur de Jeu
        self.game_manager = GameManager(human_player_name=human_name, num_players_total=num_players_total)
        self.human_player = self.game_manager.human_player
        
        # 5. Variables d'Affichage et Log
        self.log_messages = [] 
        self.player_sprites = arcade.SpriteList()
        self.player_map = {} 
        self.action_buttons = []
        self.key_is_caps = False
        
        # --- Initialisation des boutons par sécurité ---
        self.stt_button = None 
        self.start_button = None 
        # --------------------------------------------
        
        # --- Variables pour l'action Cupidon ---
        self.cupid_targets = []
        self.cupid_selection_buttons = []
        # ---------------------------------------

        # 6. Gestion du Temps et Vitesse d'écriture (Débat)
        self.debate_timer = 60 
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 
        self.typing_delay = 2          # Vitesse d'écriture rapide
        self.messages_generated = 0           
        self.max_messages_per_debate = 10     
        self.message_is_complete = False 
        
        # 7. INITIALISATION DES ÉLÉMENTS D'INTERFACE UTILISATEUR
        self._setup_ui_elements() 
        
        # 8. Initialisation des Sprites
        self._setup_sprites()
        
        # 9. Commencer le jeu
        self.start_game_loop()

        # 10. Initialisation du Speech-to-Text
        self.is_listening = False
        try:
            self.recognizer = sr.Recognizer() # Initialiser le Recognizer
            self.mic = sr.Microphone()
            self.stt_available = True
        except Exception as e:
            self.log_messages.append(f"⚠️ Erreur STT : {e}. Assurez-vous d'avoir installé 'SpeechRecognition' et 'PyAudio'.")
            self.stt_available = False


    def play_death_sound(self):
        """Joue le son de mort des loups s'il est chargé."""
        if self.sound_wolf_kill:
            arcade.play_sound(self.sound_wolf_kill)

    def _async_night_ai(self):
        """Exécute la phase de nuit dans un thread séparé pour éviter les lags."""
        # Note : Dans votre code original, cette fonction n'était pas appelée. 
        # Pour éviter les lags, il faut déclencher _night_phase() ici.
        night_message = self.game_manager._night_phase()
        
        # On repasse sur le thread principal pour mettre à jour l'UI
        arcade.schedule(lambda dt: self._finalize_night(night_message), 0)

    def _finalize_night(self, message):
        """Reçoit le résultat du thread et met à jour le jeu."""
        arcade.unschedule(self._finalize_night) 
    
        self.log_messages.append(message)
    
        # --- NOUVEAU : LOGIQUE DU SON ---
        # Si le message indique un meurtre par les loups, on joue le son
        if "tué par les Loups" in message:
            self.play_death_sound()
    
        # Transition d'état vers le jour
        self.night_processing = False
        self.current_state = GameState.DEBATE
        self.debate_timer = 60
        self.messages_generated = 0
        self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")

    # --- Méthodes de gestion de l'État ---

    def _setup_ui_elements(self):
        """Initialise/Recalcule la position des éléments d'interface utilisateur."""
        
        PANEL_WIDTH = self.width // 3 
        INPUT_HEIGHT = 30
        
        # Définition de input_y et input_x
        input_y = 5 
        input_x = self.width - PANEL_WIDTH - 10 
        
        # Réduire la largeur du champ de saisie pour les deux boutons
        input_width = PANEL_WIDTH - 180 
        
        if not hasattr(self, 'chat_input'):
            self.chat_input = ChatInput(input_x, input_y, input_width, INPUT_HEIGHT, self)
        else:
            self.chat_input.update_position(input_x, input_y, input_width)
        
        # Position du bouton Envoyer
        send_btn = MenuButton(
            input_x + input_width + 45, 
            input_y + INPUT_HEIGHT / 2, 
            80, 
            INPUT_HEIGHT, 
            "Envoyer", 
            "SEND_MESSAGE"
        )
        self.chat_input.send_button = send_btn
        
        # NOUVEAU : Bouton Parler (STT)
        self.stt_button = MenuButton(
            input_x + input_width + 135, 
            input_y + INPUT_HEIGHT / 2, 
            80, 
            INPUT_HEIGHT, 
            "Parler", 
            "START_STT"
        )
        # S'assurer que ChatInput utilise la référence au bouton pour le dessin
        self.chat_input.stt_button = self.stt_button
        
        # Bouton de Démarrage (initialisé ici)
        self.start_button = MenuButton( 
            self.width / 2, 
            self.height / 2, 
            300, 
            60, 
            "COMMENCER LA PARTIE", 
            "start_game"
        )
        
    def _setup_sprites(self):
        """Crée les représentations visuelles des joueurs."""
        
        IMAGE_DIR = "images"
        if not os.path.isdir(IMAGE_DIR):
            return self._setup_circle_sprites() 

        num_players = len(self.game_manager.players)
        center_x = self.width / 2
        center_y = self.height / 2
        angle_step = 360 / num_players
        
        available_images = [f for f in os.listdir(IMAGE_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
        random.shuffle(available_images)
        
        SPRITE_SCALE = 0.1
        # Calculer le rayon du cercle en fonction du nombre de joueurs
        # Plus il y a de joueurs, plus la distance doit être grande, mais limitée par la taille de l'écran
        max_dim = min(self.width, self.height)
        if num_players <= 12:
            CIRCLE_RADIUS = max_dim * 0.35
        else:
            CIRCLE_RADIUS = max_dim * 0.40 # Augmenter légèrement pour plus de joueurs
        
        for i, player in enumerate(self.game_manager.players):
            angle = i * angle_step
            rad_angle = math.radians(angle)
            x = center_x + CIRCLE_RADIUS * math.cos(rad_angle)
            y = center_y + CIRCLE_RADIUS * math.sin(rad_angle)
            
            image_path = None

            if player.is_human:
                human_images = [f for f in available_images if 'humain' in f.lower()]
                if human_images:
                     image_path = os.path.join(IMAGE_DIR, human_images[0])
                
            if not image_path and available_images:
                image_path = os.path.join(IMAGE_DIR, available_images.pop())

            if image_path:
                sprite = arcade.Sprite(image_path, scale=SPRITE_SCALE, center_x=x, center_y=y)
            else:
                sprite = arcade.SpriteCircle(50, arcade.color.GRAY, center_x=x, center_y=y)

            self.player_sprites.append(sprite)
            self.player_map[player.name] = sprite
            
    def _setup_circle_sprites(self):
        """Méthode de secours pour dessiner des cercles si les images manquent."""
        num_players = len(self.game_manager.players)
        center_x = self.width / 2
        center_y = self.height / 2
        angle_step = 360 / num_players
        CIRCLE_RADIUS = min(self.width, self.height) * 0.35
        
        for i, player in enumerate(self.game_manager.players):
            angle = i * angle_step
            rad_angle = math.radians(angle)
            x = center_x + CIRCLE_RADIUS * math.cos(rad_angle)
            y = center_y + CIRCLE_RADIUS * math.sin(rad_angle)
            color = arcade.color.GREEN 
            sprite = arcade.SpriteCircle(50, color, center_x=x, center_y=y)
            self.player_sprites.append(sprite)
            self.player_map[player.name] = sprite

    def start_game_loop(self):
        """Initialise le jeu en état de SETUP."""
        self.log_messages.append("--- Initialisation de la Partie ---")
        self.log_messages.append(f"Ton rôle est: {self.human_player.role.name}")
        
        if self.human_player.role and self.human_player.role.camp == Camp.LOUP:
            if self.human_player.wolf_teammates:
                teammates_str = ", ".join(self.human_player.wolf_teammates)
                self.log_messages.append(f"🐺 **TU ES LOUP-GAROU** ! Tes coéquipiers sont : {teammates_str}")
            else:
                 self.log_messages.append("🐺 **TU ES LOUP-GAROU** ! Tu es le seul loup de la partie.")
        
        self.current_state = GameState.SETUP 
        self.log_messages.append(f"\nCliquez sur 'COMMENCER LA PARTIE' pour lancer la phase initiale.")

    # --- Gestion des Phases Cupid / Nuit ---

    def _start_night_phase(self):
        """Déclenche la première nuit après la phase Cupidon (ou la nuit suivante)."""
        
        # Le Salvateur (PROTECT) a une action de nuit
        active_night_roles = [NightAction.INVESTIGATE, NightAction.POTION, NightAction.PROTECT] 
        
        # Modification : L'action de nuit humaine (Sorcière, Voyante, Salvateur) n'est déclenchée qu'à partir du Jour 2 (Nuit 2)
        if (self.human_player.is_alive and 
            self.human_player.role.night_action in active_night_roles and
            self.game_manager.day > 1):
            
            self.current_state = GameState.NIGHT_HUMAN_ACTION
            self.log_messages.append(f"\nNUIT {self.game_manager.day}: Exécute ton action de {self.human_player.role.name}.")
        else:
            self.current_state = GameState.NIGHT_IA_ACTION
            self.log_messages.append(f"\nNUIT {self.game_manager.day}: Les IA agissent.")

    def on_mouse_press(self, x, y, button, modifiers):
        """Gère le clic de la souris."""
        
        if self.current_state == GameState.SETUP:
            # Vérification de sécurité
            if self.start_button and self.start_button.check_click(x, y):
                if self.sound_start_game:
                    arcade.play_sound(self.sound_start_game) 
                cupidon = self.game_manager.get_player_by_role(Role.CUPIDON)
                
                # Vérifie si Cupidon humain doit agir (première nuit uniquement)
                if cupidon and cupidon.is_human and not self.game_manager.is_cupid_phase_done:
                    self.current_state = GameState.CUPID_ACTION
                    self.log_messages.append("💘 Cupidon : Choisis DEUX joueurs à lier (clic sur leurs icônes).")
                else:
                    # Déclenche l'action Cupidon IA (si Cupidon IA) et passe à la nuit
                    cupid_message = self.game_manager._handle_cupid_phase()
                    if cupid_message:
                        self.log_messages.append(cupid_message)
                    
                    # Le jour 1 est passé, on lance la nuit 1
                    self.game_manager.day = 1 
                    self._start_night_phase()
                return 
                
        elif self.current_state == GameState.CUPID_ACTION:
            self._handle_cupid_selection_click(x, y)

        elif self.current_state == GameState.HUMAN_ACTION:
            for btn in self.action_buttons:
                if btn.check_click(x, y):
                    voted_player_name = btn.action
                    self.log_messages.append(f"🗳️ {self.human_player.name} vote pour {voted_player_name}")
                    
                    # Correction : On enregistre le vote SANS bloquer l'interface
                    self.game_manager.register_human_vote(voted_player_name)
                    
                    # On vide les boutons immédiatement pour éviter les doubles clics
                    self.action_buttons = [] 
                    
                    # On passe à l'état VOTING (qui sera traité par on_update)
                    self.current_state = GameState.VOTING
                    return
                    
        elif self.current_state == GameState.DEBATE and self.human_player.is_alive:
            # Gérer le clic sur le bouton Envoyer (dans ChatInput.check_click)
            self.chat_input.check_click(x, y)
            
            # NOUVEAU : Gérer le clic sur le bouton STT
            if self.stt_available and self.stt_button and self.stt_button.check_click(x, y):
                 self._handle_stt_toggle()
                 return # Ne pas laisser le clic se propager au chat input
        
        elif self.current_state == GameState.NIGHT_HUMAN_ACTION:
             self._handle_human_night_action_click(x, y)

    # --- Logique Cupidon UI ---

    def _handle_cupid_selection_click(self, x, y):
        """Gère la sélection des amoureux par Cupidon humain."""
        
        clicked_player_name = None
        
        # Vérification des clics sur les sprites des joueurs
        for player in self.game_manager.get_alive_players():
            sprite = self.player_map.get(player.name)
            if sprite and sprite.collides_with_point((x, y)):
                clicked_player_name = player.name
                break
        
        if clicked_player_name:
            
            if clicked_player_name in self.cupid_targets:
                self.cupid_targets.remove(clicked_player_name)
                self.log_messages.append(f"💘 Désélectionné: {clicked_player_name}")
            elif len(self.cupid_targets) < 2:
                self.cupid_targets.append(clicked_player_name)
                self.log_messages.append(f"💘 Sélectionné: {clicked_player_name} (Total: {len(self.cupid_targets)}/2)")

            if len(self.cupid_targets) == 2:
                # Applique le choix et passe à la nuit
                choice_str = f"{self.cupid_targets[0]},{self.cupid_targets[1]}"
                cupid_message = self.game_manager._handle_cupid_phase(human_choice=choice_str)
                self.log_messages.append(cupid_message)
                self.cupid_targets = [] # Nettoyer la sélection
                
                # Passer à la première phase de nuit
                self.game_manager.day = 1 
                self._start_night_phase()
                
    def _display_cupid_selection_indicators(self):
        """Dessine un cercle pour les joueurs sélectionnés par Cupidon ET la ligne des amoureux."""
        
        # Dessiner la ligne entre les amoureux si la liaison est faite (IA ou Humain)
        if self.game_manager.lovers and len(self.game_manager.lovers) == 2:
            name1, name2 = self.game_manager.lovers
            
            # Récupérer les objets Joueur réels pour vérifier l'état
            player1 = self.game_manager.get_player_by_name(name1)
            player2 = self.game_manager.get_player_by_name(name2)
            
            # Récupérer les Sprites pour le dessin
            sprite1 = self.player_map.get(name1)
            sprite2 = self.player_map.get(name2)
            
            # Vérifier si les joueurs VIVANTS existent pour dessiner la ligne
            if (sprite1 and sprite2 and player1 and player2 and 
                player1.is_alive and player2.is_alive):
                 # Dessine un lien rose entre les deux sprites vivants
                 arcade.draw_line(
                     sprite1.center_x, sprite1.center_y,
                     sprite2.center_x, sprite2.center_y,
                     arcade.color.PINK,
                     line_width=3
                 )


        if self.current_state != GameState.CUPID_ACTION:
            return

        # Dessiner l'indicateur de sélection pour l'action en cours (CUPID_ACTION)
        for player_name in self.cupid_targets:
            sprite = self.player_map.get(player_name)
            if sprite:
                # Dessine un indicateur de sélection
                arcade.draw_circle_outline(
                    sprite.center_x, 
                    sprite.center_y, 
                    sprite.width * 0.6, 
                    arcade.color.PINK, 
                    border_width=3
                )
                
    # --- Logique Speech-to-Text (STT) ---

    def _handle_stt_toggle(self):
        """Lance ou arrête l'enregistrement vocal et traite l'audio."""
        if not self.stt_available:
            self.log_messages.append("🚫 STT non disponible. Vérifiez les dépendances (SpeechRecognition/PyAudio).")
            return
            
        if not self.is_listening:
            self.is_listening = True
            self.log_messages.append("🎙️ Micro activé : Parlez maintenant (5s max)...")
            # Commencer à écouter dans un thread séparé pour ne pas bloquer Arcade
            threading.Thread(target=self._listen_for_speech, daemon=True).start()
        else:
            # L'arrêt est géré par la reconnaissance vocale ou l'utilisateur clique à nouveau
            self.is_listening = False
            self.log_messages.append("🎙️ Micro désactivé.")

    def _listen_for_speech(self):
        """Tente d'écouter et de reconnaître la parole."""
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                # Écouter jusqu'à ce que le silence soit détecté ou le timeout atteint
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10) 
            except sr.WaitTimeoutError:
                self.log_messages.append("⏰ Timeout vocal atteint. Réessayez.")
                self.is_listening = False
                return
            except Exception as e:
                self.log_messages.append(f"Erreur d'écoute: {e}")
                self.is_listening = False
                return

        recognized_text = ""
        try:
            # Utilisez l'API Google Speech pour la reconnaissance
            recognized_text = self.recognizer.recognize_google(audio, language="fr-FR")
            
            # Mettre à jour l'interface (chat_input)
            self.chat_input.text = recognized_text
            self.log_messages.append(f"✅ Reconnaissance vocale : {recognized_text[:40]}...")

        except sr.UnknownValueError:
            self.log_messages.append("❌ Je n'ai pas compris la parole. Réessayez.")
        except sr.RequestError as e:
            self.log_messages.append(f"❌ Erreur de l'API Google Speech : {e}")
        finally:
            self.is_listening = False

    # --- Autres Méthodes de Classe (on_resize, on_key_press, etc.) ---

    def on_resize(self, width, height):
        """Appelée chaque fois que la fenêtre est redimensionnée."""
        super().on_resize(width, height)
        
        self._setup_ui_elements()
        
        self.player_sprites = arcade.SpriteList()
        self.player_map = {} 
        self._setup_sprites()
        
        # Recalculer la position du feu de camp
        if self.campfire_sprite:
            self.campfire_sprite.center_x = width / 2
            self.campfire_sprite.center_y = height / 2 - 100 
        
    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (y compris la saisie du chat)."""
        
        if symbol == arcade.key.CAPSLOCK:
            self.key_is_caps = not self.key_is_caps
            
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.handle_key_press(symbol, modifiers)
        
        if symbol == arcade.key.F:
            self.set_fullscreen(not self.fullscreen)

        elif symbol == arcade.key.SPACE:
            if self.current_state == GameState.DEBATE:
                self.debate_timer = 0 
                if self.current_speaker:
                    self.current_message_display = self.current_message_full
                    self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                self.current_speaker = None
                self.message_is_complete = False 
                self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")


    def on_draw(self):
        """Affichage : appelé à chaque image pour dessiner."""
        self.clear()
        
        # --- 1. DESSIN DU FOND D'ÉCRAN via SPRITELIST ---
        if self.background_sprite:
            self.background_sprite.width = self.width
            self.background_sprite.height = self.height
            self.background_sprite.center_x = self.width / 2
            self.background_sprite.center_y = self.height / 2
            self.background_list.draw() 
        
        # --- 2. DESSIN DU FEU DE CAMP AU CENTRE ---
        if self.campfire_sprite:
            self.campfire_sprite.center_x = self.width / 2
            self.campfire_sprite.center_y = self.height / 2 - 100 
            self.campfire_list.draw()
            
        # ----------------------------------------------------------------

        human_is_wolf = (self.human_player.role and self.human_player.role.camp == Camp.LOUP)
        wolf_teammates = self.human_player.wolf_teammates
        
        # 3. Dessiner les joueurs et la Spritelist
        for player in self.game_manager.players:
             sprite = self.player_map.get(player.name)
             if sprite:
                 color = arcade.color.WHITE
                 
                 # GESTION DE LA MORT
                 if not player.is_alive:
                     color = arcade.color.RED
                     sprite.alpha = 100
                 else:
                     sprite.alpha = 255
                     
                 # Mise en couleur des Loups alliés
                 if human_is_wolf and player.name in wolf_teammates:
                     color = arcade.color.YELLOW
                 
                 # Dessiner le nom et le statut
                 arcade.draw_text(
                     f"{player.name} ({'IA' if not player.is_human else 'H'})",
                     sprite.center_x, sprite.center_y + 60, color, 12, anchor_x="center"
                 )
                 
                 # Affichage du rôle si la partie est terminée OU si c'est le joueur humain (pour référence)
                 if self.current_state == GameState.GAME_OVER or player.is_human:
                     role_text = f"Role: {player.role.name}"
                     arcade.draw_text(role_text, sprite.center_x, sprite.center_y - 60, arcade.color.YELLOW_GREEN, 10, anchor_x="center")
                 
                 # Indicateur pour le Maire (M)
                 if player.role == Role.MAIRE and player.is_alive:
                     arcade.draw_text(
                         "M", sprite.center_x + 30, sprite.center_y + 60, 
                         arcade.color.GOLD, 14, anchor_x="center"
                     )


        # Afficher l'indicateur de sélection Cupidon et le lien d'amour (Ceci dessine aussi la ligne rose)
        self._display_cupid_selection_indicators()
        
        self.player_sprites.draw()
        
        # --- DESSINER LE CHAT LOCALISÉ ---
        self.draw_localized_chat_bubble()

        # AFFICHAGE DE LA LOGIQUE 
        self.draw_log()
        self.draw_status()
        
        
        # Dessiner les boutons d'Action/Vote
        for btn in self.action_buttons:
            btn.draw()
            
        # Afficher les boutons de nuit si nécessaire
        if self.current_state == GameState.NIGHT_HUMAN_ACTION and not self.action_buttons:
            self._display_human_night_action_buttons()
        
        # Dessiner le champ de chat si en mode DEBATE
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            # Mettre à jour l'apparence du bouton STT avant de dessiner la boîte de chat
            if self.stt_available and self.stt_button:
                self.stt_button.text = "ARRÊTER" if self.is_listening else "Parler"

            self.chat_input.draw() # Dessine la boite de chat et les boutons Envoyer/Parler
            
            # Afficher l'indicateur d'écoute si le micro est actif
            if self.is_listening:
                 arcade.draw_text("EN COURS D'ÉCOUTE...", 
                                  self.chat_input.x, self.chat_input.y + self.chat_input.height + 5, 
                                  arcade.color.RED_ORANGE, 12)
            
        # AFFICHER LE BOUTON DE DÉMARRAGE si en SETUP
        if self.current_state == GameState.SETUP:
            # La variable self.start_button est garantie d'exister ici grâce à l'initialisation dans __init__
            if self.start_button:
                self.start_button.draw() 


    # --- MÉTHODE DE DESSIN DU CHAT LOCALISÉ ---
    def draw_localized_chat_bubble(self):
        """Dessine la bulle de chat/frappe sous le sprite de l'orateur actuel."""
        
        speaker_player = self.current_speaker
        
        if speaker_player and speaker_player.is_alive:
            sprite = self.player_map.get(speaker_player.name)
            if sprite:
                
                is_typing = (not self.message_is_complete)
                display_text = self.current_message_display if is_typing else self.current_message_full
                
                cursor = ("|" if is_typing and int(time.time() * 2) % 2 == 0 else "")
                
                CHAT_WIDTH = 120 
                TEXT_X = sprite.center_x - CHAT_WIDTH / 2 + 5
                TEXT_Y = sprite.center_y - 90 
                
                arcade.draw_text(
                    f"{display_text}{cursor}", 
                    TEXT_X, 
                    TEXT_Y, 
                    arcade.color.LIGHT_YELLOW,
                    12, 
                    width=CHAT_WIDTH - 10,
                    multiline=True,
                    anchor_x="left",
                )
                
                if is_typing:
                    arcade.draw_text("...", sprite.center_x + 40, sprite.center_y + 40, arcade.color.AZURE, 18)


    def on_update(self, delta_time):
        """Logique : appelé à chaque image pour mettre à jour l'état."""
        
        if self.current_state in [GameState.SETUP, GameState.CUPID_ACTION, GameState.NIGHT_HUMAN_ACTION]:
            return

        # GESTION ASYNCHRONE DE LA NUIT IA POUR ÉVITER LE LAG
        if self.current_state == GameState.NIGHT_IA_ACTION:
            if not self.night_processing:
                self.night_processing = True
                # On lance le calcul de l'IA dans un thread séparé
                threading.Thread(target=self._async_night_ai, daemon=True).start()

        elif self.current_state == GameState.DEBATE:
            self._update_debate(delta_time) 
        
        elif self.current_state == GameState.VOTING:
            lynch_message = self.game_manager._lynch_result(self.game_manager.get_alive_players()) 
            self.log_messages.append(lynch_message)
            self.current_state = GameState.RESULT
        
        elif self.current_state == GameState.RESULT:
            winner = self.game_manager.check_win_condition()
            if winner:
                 self.log_messages.append(f"\n🎉 VICTOIRE des {winner.value} ! Fin de la partie.")
                 self.current_state = GameState.GAME_OVER
            else:
                 self.game_manager.day += 1
                 self.log_messages.append(f"\nJOUR {self.game_manager.day} : La NUIT tombe.") 
                 # La phase Cupidon est ignorée après la première nuit (day > 1)
                 self._start_night_phase()

        
    # --- LOGIQUE D'ACTION HUMAINE DE NUIT ---

    def _display_human_night_action_buttons(self):
        """Prépare les boutons d'action de nuit pour la Voyante/Sorcière/Salvateur humain."""
        
        self.action_buttons = []
        alive = self.game_manager.get_alive_players()
        role_name = self.human_player.role.name if self.human_player.role else "N/A" 
        
        button_y = 50 
        button_width = 150
        button_height = 40
        
        targets = [p for p in alive if p != self.human_player]
        targets_msg = ""

        if role_name == "Voyante":
            action = "ENQUÊTER"
            targets_msg = "Choisis qui enquêter (Voyante) :"
            
            start_x = self.width / 2 - (len(targets) * (button_width + 10) / 2) + 50
            for i, target in enumerate(targets):
                x = start_x + (i * (button_width + 10))
                btn = MenuButton(
                    x, button_y, button_width, button_height, 
                    f"{action} {target.name}", 
                    f"{action}:{target.name}" 
                )
                self.action_buttons.append(btn)
            self.log_messages.append(f"-> {role_name}: {targets_msg}")
            
        elif role_name == "Sorcière" and (self.human_player.has_kill_potion or self.human_player.has_life_potion):
            targets_msg = "Sorcière: Choisis ton action"
            
            x_start = self.width / 2 - 150
            if self.human_player.has_kill_potion:
                 self.action_buttons.append(MenuButton(x_start, button_y, 140, button_height, "TUER [Potion Mort]", "TUER"))
                 x_start += 150
            if self.human_player.has_life_potion:
                 self.action_buttons.append(MenuButton(x_start, button_y, 140, button_height, "SAUVER [Potion Vie]", "SAUVER"))
                 x_start += 150
                 
            self.action_buttons.append(MenuButton(x_start, button_y, 100, button_height, "PASSER", "PASSER"))
            
            self.log_messages.append(f"-> {targets_msg}")
            return
            
        elif role_name == "Salvateur":
            targets_msg = "Choisis qui protéger (Salvateur) :"
            
            # Exclusion : ne peut pas se protéger lui-même ni la cible précédente
            last_target = self.human_player.last_protected_target
            
            # Inclure tous les vivants SAUF soi-même et la cible précédente
            protect_targets = [p for p in alive if p.name != self.human_player.name and p.name != last_target]
            
            start_x = self.width / 2 - (len(protect_targets) * (button_width + 10) / 2) + 50
            
            for i, target in enumerate(protect_targets):
                x = start_x + (i * (button_width + 10))
                btn = MenuButton(
                    x, button_y, button_width, button_height, 
                    f"PROTÉGER {target.name}", 
                    f"PROTÉGER:{target.name}" 
                )
                self.action_buttons.append(btn)
            
            if last_target:
                self.log_messages.append(f"⚠️ **Attention :** Impossible de protéger {last_target} deux nuits de suite.")
            self.log_messages.append(f"-> {role_name}: {targets_msg}")
            return
            
        else:
            # S'il n'y a pas d'action de nuit humaine, on passe à l'IA.
            self.current_state = GameState.NIGHT_IA_ACTION
            return

    def _handle_human_night_action_click(self, x, y):
        """Traite le clic du joueur humain sur un bouton d'action de nuit."""
        
        clicked_action_data = None
        for btn in self.action_buttons:
            if btn.check_click(x, y):
                clicked_action_data = btn.action
                break
        
        if not clicked_action_data:
            return

        self.action_buttons = [] 
        
        if self.human_player.role == Role.VOYANTE and ":" in clicked_action_data:
            action_type, target_name = clicked_action_data.split(":", 1)
            target = next((p for p in self.game_manager.players if p.name == target_name), None)
            
            if action_type == "ENQUÊTER" and target:
                target_role = target.role.name
                target_camp = target.role.camp.value
                self.log_messages.append(f"🕵️‍♀️ Révélation : {target.name} est un(e) **{target_role}** ({target_camp}).")
                self.current_state = GameState.NIGHT_IA_ACTION
                return
                
        elif self.human_player.role == Role.SORCIERE and clicked_action_data in ["TUER", "SAUVER", "PASSER"]:
            
            if clicked_action_data == "PASSER":
                self.log_messages.append("Action de nuit passée.")
            
            elif clicked_action_data == "TUER" and self.human_player.has_kill_potion:
                 self.human_player.has_kill_potion = False
                 self.log_messages.append(f"🧪 Sorcière : Potion de mort utilisée. L'impact sera résolu.")
            
            elif clicked_action_data == "SAUVER" and self.human_player.has_life_potion:
                 self.human_player.has_life_potion = False
                 self.log_messages.append(f"💖 Sorcière : Potion de vie utilisée. L'impact sera résolu.")
            
            self.current_state = GameState.NIGHT_IA_ACTION
            return
            
        elif self.human_player.role == Role.SALVATEUR and ":" in clicked_action_data:
            action_type, target_name = clicked_action_data.split(":", 1)
            target = self.game_manager.get_player_by_name(target_name)
            
            if action_type == "PROTÉGER" and target:
                # Stocker la cible pour que _night_phase l'utilise
                self.game_manager.night_protected_target = target_name
                self.human_player.last_protected_target = target_name
                self.log_messages.append(f"🛡️ Le Salvateur protège **{target.name}** cette nuit.")
                self.current_state = GameState.NIGHT_IA_ACTION
                return
        
        else:
             self.log_messages.append("Action invalide ou non supportée.")
             self.current_state = GameState.NIGHT_IA_ACTION

        if self.current_state == GameState.NIGHT_IA_ACTION:
             self.log_messages.append("Résolution des actions IA...")
             self.current_state = GameState.NIGHT_IA_ACTION
        

    # --- LOGIQUE D'UPDATE ET D'AFFICHAGE ---
    
    def _update_debate(self, delta_time):
        """Gère le temps et la parole pendant la phase de débat."""
        
        self.debate_timer -= delta_time
        
        if self.current_speaker is not None and not self.message_is_complete:
            self.typing_speed_counter += 1
            if self.typing_speed_counter >= self.typing_delay:
                current_len = len(self.current_message_display)
                if current_len < len(self.current_message_full):
                    self.current_message_display += self.current_message_full[current_len]
                else:
                    self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                    self.message_is_complete = True
                self.typing_speed_counter = 0

        if (self.debate_timer <= 0 or self.messages_generated >= self.max_messages_per_debate) and self.current_state == GameState.DEBATE:
            
            if self.current_speaker is not None and not self.message_is_complete:
                 self.current_message_display = self.current_message_full
                 self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")

            self.current_speaker = None 
            self.message_is_complete = False 
            self.log_messages.append("\n🗳️ FIN DU DÉBAT. PLACE AU VOTE.")
            self.messages_generated = 0 
            
            if self.human_player.is_alive:
                self.enter_human_voting_state() 
                self.current_state = GameState.HUMAN_ACTION
            else:
                self.current_state = GameState.VOTING
                
        elif (self.current_speaker is None or self.message_is_complete) and self.messages_generated < self.max_messages_per_debate: 
            
            self.current_speaker = None
            self.current_message_full = ""
            self.current_message_display = ""
            self.message_is_complete = False 
            
            alive_ais = [p for p in self.game_manager.get_alive_players() if not p.is_human]
            if alive_ais:
                speaker = random.choice(alive_ais)
                
                debate_message = speaker.generate_debate_message(self.game_manager._get_public_status())
                
                self.current_speaker = speaker
                self.current_message_full = debate_message
                self.current_message_display = ""
                
                for listener in [p for p in alive_ais if p != speaker]:
                    listener.receive_public_message(speaker.name, debate_message)
                    
                self.messages_generated += 1 

    def enter_human_voting_state(self):
        """Prépare les boutons pour le vote de lynchage du joueur humain."""
        alive = self.game_manager.get_alive_players()
        self.action_buttons = []
        
        button_y = 50 
        button_width = 100
        button_height = 30
        
        voting_targets = [p for p in alive if p != self.human_player]
        
        CENTER_X = self.width / 2 
        start_x = CENTER_X - (len(voting_targets) * (button_width + 10) / 2)
        
        for i, target in enumerate(voting_targets):
            x = start_x + (i * (button_width + 10))
            btn = MenuButton(
                x, button_y, button_width, button_height, 
                f"Voter {target.name}", target.name 
            )
            self.action_buttons.append(btn)
            
        self.log_messages.append(f"-> {self.human_player.name}, choisis ta victime (CLIC) :")


    # --- MÉTHODES D'AFFICHAGE ---
    
    def draw_log(self):
        """Dessine le Journal de Bord (Historique Permanent) à GAUCHE."""
        LOG_X_START = 10
        LOG_WIDTH = self.width // 5
        LOG_HEIGHT = self.height - 40 
        
        arcade.draw_lbwh_rectangle_filled(
            LOG_X_START, 
            10,
            LOG_WIDTH, 
            LOG_HEIGHT, 
            (20, 20, 20, 180) 
        )
        
        x_pos = LOG_X_START + 10
        y_pos = self.height - 30 
        line_spacing = 85 
        font_size = 14 
        
        arcade.draw_text("JOURNAL DE BORD:", x_pos, y_pos, arcade.color.ORANGE_RED, 14)
        y_pos -= 30 
        
        for msg in reversed(self.log_messages):
            if y_pos < 50: 
                break
            
            arcade.draw_text(
                msg, 
                x_pos, 
                y_pos, 
                arcade.color.LIGHT_GRAY, 
                font_size, 
                width=LOG_WIDTH - 30,
                multiline=True
            )
            y_pos -= line_spacing 
            
    def draw_status(self):
        """Dessine les compteurs (Loups, Timer) à DROITE, en haut."""
        
        PANEL_WIDTH = self.width // 3
        RIGHT_PANEL_START_X = self.width - PANEL_WIDTH
        
        arcade.draw_text(
            f"Loups Vivants : {self.game_manager.wolves_alive}",
            RIGHT_PANEL_START_X + 20, self.height - 30, arcade.color.WHITE, 16
        )
        
        if self.current_state in [GameState.DEBATE, GameState.VOTING, GameState.HUMAN_ACTION]:
             arcade.draw_text(
                f"Temps Restant : {int(self.debate_timer)}s",
                RIGHT_PANEL_START_X + 20, self.height - 60, arcade.color.YELLOW, 14
            )
        
        if self.current_state == GameState.NIGHT_HUMAN_ACTION:
             # Afficher l'action requise (Salvateur ou autre)
             action_text = f"ACTION NOCTURNE REQUISE ({self.human_player.role.name})"
             arcade.draw_text(
                action_text,
                RIGHT_PANEL_START_X + 20, self.height - 200, arcade.color.ORANGE, 16
            )
        elif self.current_state == GameState.CUPID_ACTION:
             arcade.draw_text(
                f"PHASE CUPIDON (Sélectionnez 2)",
                RIGHT_PANEL_START_X + 20, self.height - 200, arcade.color.PINK, 16
            )


    # --- MÉTHODE DE DESSIN DU CHAT LOCALISÉ ---
    def draw_localized_chat_bubble(self):
        """Dessine la bulle de chat/frappe sous le sprite de l'orateur actuel."""
        
        speaker_player = self.current_speaker
        
        if speaker_player and speaker_player.is_alive:
            sprite = self.player_map.get(speaker_player.name)
            if sprite:
                
                is_typing = (not self.message_is_complete)
                display_text = self.current_message_display if is_typing else self.current_message_full
                
                cursor = ("|" if is_typing and int(time.time() * 2) % 2 == 0 else "")
                
                CHAT_WIDTH = 120 
                TEXT_X = sprite.center_x - CHAT_WIDTH / 2 + 5
                TEXT_Y = sprite.center_y - 90 
                
                arcade.draw_text(
                    f"{display_text}{cursor}", 
                    TEXT_X, 
                    TEXT_Y, 
                    arcade.color.LIGHT_YELLOW,
                    12, 
                    width=CHAT_WIDTH - 10,
                    multiline=True,
                    anchor_x="left",
                )
                
                if is_typing:
                    arcade.draw_text("...", sprite.center_x + 40, sprite.center_y + 40, arcade.color.AZURE, 18)


# --- Lancement du Jeu ---

def main():
    """Fonction principale pour lancer l'application Arcade."""
    
    # 1. PERMETTRE AU JOUEUR DE CHOISIR SON NOM
    try:
        # Note: L'input console ne s'affiche pas dans l'environnement graphique, 
        # mais fonctionne si le script est lancé depuis un terminal.
        input_name = input("Entrez votre nom de joueur (laissez vide pour 'Lucie') : ")
        human_name = input_name.strip() or "Lucie"
    except EOFError:
        human_name = "Lucie"
        
    # 2. PERMETTRE AU JOUEUR DE CHOISIR LE NOMBRE TOTAL DE JOUEURS
    while True:
        try:
            num_input = input("Entrez le nombre TOTAL de joueurs (Min. 10, Max. 15) : ")
            num_players = int(num_input.strip())
            
            # Le minimum est 10 car il y a 10 rôles spéciaux/fixes (3 Loups + 7 Villageois spé)
            if num_players < 10 or num_players > 15:
                print("Le nombre doit être compris entre 10 et 15.")
                continue
            break
        except ValueError:
            print("Veuillez entrer un nombre valide.")
            
    # 3. PASSER LE NOM ET LE NOMBRE À LA CLASSE DE JEU
    game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, 
                          human_name=human_name, 
                          num_players_total=num_players)
    arcade.run()


if __name__ == "__main__":
    
    # S'assure que les dossiers existent pour éviter des erreurs
    if not os.path.exists("context"):
        os.makedirs("context")
    
    if not os.path.exists("sounds"):
        os.makedirs("sounds")
        
    if not os.path.exists("images"):
        os.makedirs("images")
    if not os.path.exists("images/fond"):
        os.makedirs("images/fond")

    main()
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
            "LANCER": arcade.color.DARK_GREEN,
            "Envoyer": arcade.color.DARK_CYAN,
            "PROTÉGER": arcade.color.SKY_BLUE,
            "Parler": arcade.color.DARK_GREEN,
            "ARRÊTER": arcade.color.RED_DEVIL,
            "DEFAULT": arcade.color.DARK_BLUE
        }
        
        base_action = self.text.split()[0]
        color = color_map.get(base_action, color_map.get(self.text, color_map["DEFAULT"]))

        # Calcul manuel des bords (Left, Right, Bottom, Top)
        l = self.center_x - self.width / 2
        r = self.center_x + self.width / 2
        b = self.center_y - self.height / 2
        t = self.center_y + self.height / 2

        # Dessin du corps du bouton avec la nouvelle syntaxe lrbt
        arcade.draw_lrbt_rectangle_filled(l, r, b, t, color)
        
        # Bordure fine pour le relief (Flat Design)
        arcade.draw_lrbt_rectangle_outline(l, r, b, t, arcade.color.WHITE, 1)

        # Texte centré et en gras
        arcade.draw_text(
            self.text, 
            self.center_x, 
            self.center_y,
            arcade.color.WHITE, 
            11, 
            anchor_x="center", 
            anchor_y="center", 
            bold=True
        )

    def check_click(self, x, y):
        """Vérifie si les coordonnées (x, y) sont à l'intérieur du bouton."""
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
        # 1. Calcul des bords (Left, Right, Bottom, Top)
        # Note : On utilise lrbt (Left, Right, Bottom, Top) pour Arcade 3.0+
        l, r, b, t = self.x, self.x + self.width, self.y, self.y + self.height

        # 2. Fond de la barre : Noir semi-transparent
        bg_color = (20, 20, 20, 180) if not self.active else (40, 40, 40, 220)
        
        arcade.draw_lrbt_rectangle_filled(l, r, b, t, bg_color)

        # 3. Bordure lumineuse (Cyan si actif, gris sinon)
        border_color = arcade.color.CYAN if self.active else (100, 100, 100, 150)
        border_width = 2 if self.active else 1
        
        arcade.draw_lrbt_rectangle_outline(l, r, b, t, border_color, border_width)

        # 4. Gestion du texte et du curseur moderne "_"
        cursor = ("_" if self.active and int(time.time() * 2) % 2 == 0 else "")
        
        if not self.text and not self.active:
            arcade.draw_text("Écrire un message...", self.x + 10, self.y + 8, 
                             (150, 150, 150), 12, italic=True)
        else:
            arcade.draw_text(f"{self.text}{cursor}", self.x + 10, self.y + 8, 
                             arcade.color.WHITE, 13)
        
        # 5. Dessin des boutons associés
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
    
    def __init__(self, width, height, title):
        # 1. INITIALISATION DE LA FENÊTRE
        super().__init__(width, height, title, resizable=True)
        self.set_update_rate(1/60)
        # self.maximize() # Optionnel selon votre préférence

        # --- ÉLÉMENTS DU MENU ACCUEIL ---
        self.menu_human_name = "Lucie"
        self.menu_num_players = 11
        self.name_input_active = False
        
        # Initialisation des boutons de réglage du menu
        self.btn_plus = MenuButton(0, 0, 40, 40, "+", "PLUS")
        self.btn_minus = MenuButton(0, 0, 40, 40, "-", "MINUS")

        # --- CHARGEMENT DU FOND DU MENU ---
        self.menu_background_list = arcade.SpriteList()
        if os.path.exists("images/fond/menu_bg.jpg"):
            self.menu_bg_sprite = arcade.Sprite("images/fond/menu_bg.jpg")
            self.menu_background_list.append(self.menu_bg_sprite)

        # --- CHARGEMENT DES SONS ---
        self._init_sounds()

        # --- ÉTAT ET MOTEUR ---
        self.current_state = GameState.SETUP
        self.game_manager = None # Sera initialisé au clic sur START
        self.human_player = None
        self.night_processing = False
        
        # --- GRAPHISMES DU JEU ---
        self._init_graphics()

        # --- VARIABLES DE JEU ET UI ---
        self.log_messages = [] 
        self.player_sprites = arcade.SpriteList()
        self.player_map = {} 
        self.action_buttons = []
        self.key_is_caps = False
        self.stt_button = None 
        self.start_button = None 
        
        # --- ACTIONS SPÉCIALES ---
        self.cupid_targets = []
        self.cupid_selection_buttons = []

        # --- PARAMÈTRES DU DÉBAT ---
        self.debate_timer = 60 
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 
        self.typing_delay = 2 
        self.messages_generated = 0 
        self.max_messages_per_debate = 10 
        self.message_is_complete = False 
        
        # --- INITIALISATION UI ET STT ---
        self._setup_ui_elements() 
        self._init_stt()

        self.sound_start_game = None # On l'initialise à None par défaut
        try:
            if os.path.exists("sounds/start.mp3"):
                self.sound_start_game = arcade.load_sound("sounds/start.mp3")
        except Exception as e:
            print(f"Erreur chargement son de démarrage : {e}")
            
    def _init_sounds(self):
        """Centralisation du chargement des sons."""
        self.sounds = {}
        sound_files = {
            "start": "sounds/start.mp3",
            "ambient": "sounds/ambient_night.mp3",
            "ancient": "sounds/ancient_shield.mp3",
            "guardian": "sounds/guardian_protect.mp3",
            "cupid": "sounds/cupid_power.mp3",
            "hunter": "sounds/hunter_shot.mp3",
            "seer": "sounds/seer_power.mp3",
            "villager_death": "sounds/villager_death.mp3",
            "witch": "sounds/witch_power.mp3",
            "wolf_kill": "sounds/wolf_kill.mp3"
        }

        for key, path in sound_files.items():
            if os.path.exists(path):
                try:
                    if key == "ambient":
                        self.bg_music = arcade.load_sound(path, streaming=True)
                        self.music_player = arcade.play_sound(self.bg_music, volume=0.15, loop=True)
                    else:
                        self.sounds[key] = arcade.load_sound(path)
                except Exception as e:
                    print(f"Erreur chargement son {key} : {e}")

    def _init_graphics(self):
        """Initialisation des listes de sprites de décor."""
        self.background_list = arcade.SpriteList() 
        if os.path.exists("images/fond/images.png"):
            self.background_sprite = arcade.Sprite("images/fond/images.png", scale=1.0)
            self.background_list.append(self.background_sprite) 
             
        self.campfire_list = arcade.SpriteList()
        if os.path.exists("images/fond/campfire.png"):
            self.campfire_sprite = arcade.Sprite("images/fond/campfire.png", scale=0.4)
            self.campfire_list.append(self.campfire_sprite)

    def _init_stt(self):
        """Initialisation du moteur Speech-to-Text."""
        self.is_listening = False
        try:
            self.recognizer = sr.Recognizer()
            self.mic = sr.Microphone()
            self.stt_available = True
        except Exception as e:
            print(f"STT non disponible : {e}")
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
        """
        Reçoit le résultat du thread de calcul de nuit et met à jour le jeu.
        Gère les déclenchements sonores (Loups, Chasseur).
        """
        # On arrête la planification si on utilise arcade.schedule (sécurité)
        arcade.unschedule(self._finalize_night) 

        # 1. Ajout du rapport de nuit au journal
        self.log_messages.append(message)

        # 2. GESTION DES SONS DE MORT (LOUPS)
        # Si le message indique qu'un joueur a été tué par les loups
        if "tué par les Loups" in message:
            if self.sound_wolf_kill:
                arcade.play_sound(self.sound_wolf_kill)

        # 3. GESTION DU SON DU CHASSEUR
        # On vérifie l'indicateur dans le GameManager (activé dans _kill_player)
        if self.game_manager.hunter_just_shot:
            if self.sound_hunter_shot:
                arcade.play_sound(self.sound_hunter_shot)
            # Important : Réinitialiser l'indicateur pour ne pas rejouer le son
            self.game_manager.hunter_just_shot = False

        if self.game_manager.ancient_shield_triggered:
            if self.sound_ancient_power:
                arcade.play_sound(self.sound_ancient_power)
            # Important : Réinitialiser pour la prochaine nuit
            self.game_manager.ancient_shield_triggered = False

        # 4. Transition d'état vers le jour (Débat)
        self.night_processing = False
        self.current_state = GameState.DEBATE
        
        # Réinitialisation des paramètres de débat
        self.debate_timer = 10
        self.messages_generated = 0
        self.current_speaker = None
        self.message_is_complete = False
        
        self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le soleil se lève sur le village.")

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

        if self.current_state == GameState.SETUP:
            # Bouton Moins
            self.btn_minus = MenuButton(self.width/2 - 60, self.height/2, 40, 40, "-", "MINUS")
            # Bouton Plus
            self.btn_plus = MenuButton(self.width/2 + 60, self.height/2, 40, 40, "+", "PLUS")
            # Bouton Valider
            self.start_button = MenuButton(self.width/2, self.height/2 - 100, 250, 50, "LANCER LA PARTIE", "START_GAME")
        
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
        """Déclenche la phase de nuit en vérifiant si le joueur est vivant et a un rôle."""
        # Liste des actions nécessitant une intervention humaine
        active_night_roles = [NightAction.INVESTIGATE, NightAction.POTION, NightAction.PROTECT] 
    
        # Sécurité : vérifier si human_player existe et est en vie
        if (self.human_player and self.human_player.is_alive and 
            self.human_player.role and 
            self.human_player.role.night_action in active_night_roles):
        
            self.current_state = GameState.NIGHT_HUMAN_ACTION
            self.log_messages.append(f"C'est à vous d'agir ({self.human_player.role.name}).")
        else:
            # Si le joueur est mort ou n'a pas d'action, on passe directement à l'IA
            self.current_state = GameState.NIGHT_IA_ACTION
            self.night_processing = False # Prêt pour le thread IA

    def on_mouse_press(self, x, y, button, modifiers):
        """Gère le clic de la souris selon l'état du jeu."""
        
        if self.current_state == GameState.SETUP:
            # 1. Bouton PLUS : augmente le nombre (max 15)
            if self.btn_plus.check_click(x, y):
                self.menu_num_players = min(15, self.menu_num_players + 1)
                return # On arrête ici pour ne pas lancer le jeu

            # 2. Bouton MINUS : descend le nombre (min 6)
            if self.btn_minus.check_click(x, y):
                self.menu_num_players = max(6, self.menu_num_players - 1)
                return # On arrête ici pour ne pas lancer le jeu

            # 3. Bouton de focus pour le nom (cliquer sur la zone du nom)
            cx, cy = self.width / 2, self.height / 2
            if cx - 75 < x < cx + 175 and cy + 35 < y < cy + 75:
                self.name_input_active = True
                return
            else:
                self.name_input_active = False

            # 4. Bouton COMMENCER (Le vrai lancement est ici)
            if self.start_button.check_click(x, y):
                # INITIALISATION RÉELLE DU JEU
                self.game_manager = GameManager(
                    human_player_name=self.menu_human_name, 
                    num_players_total=self.menu_num_players
                )
                self.human_player = self.game_manager.human_player
                
                # Chargement des éléments visuels
                self._setup_sprites()
                self._setup_ui_elements() 
                
                if self.sound_start_game:
                    arcade.play_sound(self.sound_start_game) 
                
                # Lancement de la logique de boucle
                self.start_game_loop()

                cupidon = self.game_manager.get_player_by_role(Role.CUPIDON)
                
                # Cas 1 : Cupidon est humain
                if cupidon and cupidon.is_human and not self.game_manager.is_cupid_phase_done:
                    self.current_state = GameState.CUPID_ACTION
                    self.log_messages.append("💘 Cupidon : Choisis DEUX joueurs à lier (clic sur leurs icônes).")
                
                # Cas 2 : Cupidon IA ou absent
                else:
                    cupid_message = self.game_manager._handle_cupid_phase()
                    if cupid_message:
                        self.log_messages.append(cupid_message)
                        if "lié" in cupid_message and self.sound_cupid_power:
                            arcade.play_sound(self.sound_cupid_power)
                    
                    self.game_manager.day = 1 
                    self._start_night_phase()
                return 

        elif self.current_state == GameState.CUPID_ACTION:
            old_targets_count = len(self.cupid_targets)
            self._handle_cupid_selection_click(x, y)
            if old_targets_count == 1 and len(self.cupid_targets) == 0 and self.sound_cupid_power:
                arcade.play_sound(self.sound_cupid_power)

        elif self.current_state == GameState.HUMAN_ACTION:
            for btn in self.action_buttons:
                if btn.check_click(x, y):
                    voted_player_name = btn.action
                    self.log_messages.append(f"🗳️ {self.human_player.name} vote pour {voted_player_name}")
                    self.game_manager.register_human_vote(voted_player_name)
                    self.action_buttons = [] 
                    self.current_state = GameState.VOTING
                    return
                    
        elif self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.check_click(x, y)
            if self.stt_available and self.stt_button and self.stt_button.check_click(x, y):
                 self._handle_stt_toggle()
                 return 
        
        elif self.current_state == GameState.NIGHT_HUMAN_ACTION:
            for btn in self.action_buttons:
                if btn.check_click(x, y):
                    action_data = btn.action 
                    if "PROTÉGER" in action_data and self.sound_guardian_power:
                        arcade.play_sound(self.sound_guardian_power)
                    elif "ENQUÊTER" in action_data and self.sound_seer_power:
                        arcade.play_sound(self.sound_seer_power)
                    elif (action_data == "TUER" or action_data == "SAUVER") and self.sound_witch_power:
                        arcade.play_sound(self.sound_witch_power)
            
                    self._handle_human_night_action_click(x, y)
                    return
                
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
        super().on_resize(width, height)
        self._setup_ui_elements()

        if self.game_manager is not None:
            self.player_sprites = arcade.SpriteList()
            self.player_map = {} 
            self._setup_sprites()
    
        if self.campfire_sprite:
            self.campfire_sprite.center_x = width / 2
            self.campfire_sprite.center_y = height / 2 - 100
        
        if hasattr(self, 'menu_bg_sprite'):
            self.menu_bg_sprite.width = width
            self.menu_bg_sprite.height = height
            self.menu_bg_sprite.center_x = width / 2
            self.menu_bg_sprite.center_y = height / 2

    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (y compris la saisie du chat)."""

        # --- 1. SAISIE DU NOM DANS LE MENU SETUP ---
        if self.current_state == GameState.SETUP:
            if symbol == arcade.key.BACKSPACE:
                self.menu_human_name = self.menu_human_name[:-1]
            elif len(self.menu_human_name) < 12:
                try:
                    char = chr(symbol)
                    if char.isalnum():
                        # Gestion des majuscules via Shift ou CapsLock
                        if (modifiers & arcade.key.MOD_SHIFT) or self.key_is_caps:
                            self.menu_human_name += char.upper()
                        else:
                            self.menu_human_name += char.lower()
                except ValueError:
                    pass # Ignore les touches non-caractères (F1, Ctrl, etc.)
            return # On arrête ici si on est dans le menu

        # --- 2. SAISIE DU CHAT PENDANT LE DÉBAT ---
        if self.chat_input.active:
            self.chat_input.handle_key_press(symbol, modifiers)
            return
    
        # --- 3. RACCOURCIS GÉNÉRAUX ---
        # Plein écran
        if symbol == arcade.key.F:
            self.set_fullscreen(not self.fullscreen)

        # Verrouillage majuscule (pour votre variable interne)
        elif symbol == arcade.key.CAPSLOCK:
            self.key_is_caps = not self.key_is_caps
        
        # Passer le débat (Espace)
        elif symbol == arcade.key.SPACE:
            if self.current_state == GameState.DEBATE:
                self.debate_timer = 0 
                if self.current_speaker:
                    self.current_message_display = self.current_message_full
                    self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
            
                self.current_speaker = None
                self.message_is_complete = False 
                self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")

    def _draw_setup_menu(self):
        """Dessine l'écran de configuration initial."""

        # 1. Dessiner le sprite de fond
        if len(self.menu_background_list) > 0:
            self.menu_background_list.draw()
        else:
            arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        # Titre principal
        arcade.draw_text("CONFIGURATION DE LA PARTIE", self.width/2, self.height/2 + 150, 
                     arcade.color.WHITE, 30, anchor_x="center")

        # --- CORRECTION ICI : menu_human_name ---
        arcade.draw_text(f"Nom : {self.menu_human_name}", self.width/2, self.height/2 + 80, 
                     arcade.color.CYAN, 20, anchor_x="center")
    
        arcade.draw_text("(Tapez au clavier pour modifier)", self.width/2, self.height/2 + 55, 
                     arcade.color.GRAY, 12, anchor_x="center")

        # --- CORRECTION ICI : menu_num_players ---
        arcade.draw_text(f"Nombre de joueurs : {self.menu_num_players}", self.width/2, self.height/2 + 10, 
                 arcade.color.WHITE, 20, anchor_x="center")

        # Dessin des boutons (+, -, LANCER)
        self.btn_minus.draw()
        self.btn_plus.draw()
        self.start_button.draw()

    def on_draw(self):
        """Affichage : appelé à chaque image pour dessiner."""
        self.clear()
        
        if self.current_state == GameState.SETUP:
            self._draw_setup_menu() # (votre code actuel de menu)
            return
        
        if self.game_manager is None or self.human_player is None:
            return
    
        self.btn_minus.draw()
        self.btn_plus.draw()
        self.start_button.draw()

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
                self.night_processing = True # Bloque le déclenchement de multiples threads
                thread = threading.Thread(target=self._async_night_ai, daemon=True)
                thread.start()

        elif self.current_state == GameState.DEBATE:
            self._update_debate(delta_time) 
        
        elif self.current_state == GameState.VOTING:
            # On récupère le dictionnaire des votes avant qu'il ne soit vidé par _lynch_result
            if self.game_manager.vote_counts:
            # Trouver qui a reçu le plus de votes (identique à la logique interne du GameManager)
                lynch_target_name = max(self.game_manager.vote_counts, key=self.game_manager.vote_counts.get)
                target_player = self.game_manager.get_player_by_name(lynch_target_name)

            # Exécuter le lynchage et obtenir le message
            lynch_message = self.game_manager._lynch_result(self.game_manager.get_alive_players())
            self.log_messages.append(lynch_message)

            # Vérifier si la mort a eu lieu et si ce n'était pas un loup
            if "mort(e)" in lynch_message and target_player:
                # On vérifie le camp du rôle (Camp.VILLAGE)
                if target_player.role.camp == Camp.VILLAGE:
                    if self.sound_villager_death:
                        arcade.play_sound(self.sound_villager_death)
    
            self.current_state = GameState.RESULT
        
        elif self.current_state == GameState.RESULT:
            winner = self.game_manager.check_win_condition()
            if winner:
                self.log_messages.append(f"\n🎉 VICTOIRE des {winner.value} !")
                self.current_state = GameState.GAME_OVER
            else:
            # TRÈS IMPORTANT : Réinitialiser night_processing ici
                self.night_processing = False 
                self.game_manager.day += 1
                self.log_messages.append(f"\n🌙 NUIT {self.game_manager.day} : Le village s'endort...") 
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
                if self.sound_seer_power:
                    arcade.play_sound(self.sound_seer_power)
                target_role = target.role.name
                target_camp = target.role.camp.value
                self.log_messages.append(f"🕵️‍♀️ Révélation : {target.name} est un(e) **{target_role}** ({target_camp}).")
                self.current_state = GameState.NIGHT_IA_ACTION
                return
                
        elif self.human_player.role == Role.SORCIERE and clicked_action_data in ["TUER", "SAUVER", "PASSER"]:
            
            if clicked_action_data == "PASSER":
                self.log_messages.append("Action de nuit passée.")
            
            elif clicked_action_data == "TUER" and self.human_player.has_kill_potion:
                 if self.sound_witch_power:
                    arcade.play_sound(self.sound_witch_power)
                 self.human_player.has_kill_potion = False
                 self.log_messages.append(f"🧪 Sorcière : Potion de mort utilisée. L'impact sera résolu.")
            
            elif clicked_action_data == "SAUVER" and self.human_player.has_life_potion:
                 if self.sound_witch_power:
                    arcade.play_sound(self.sound_witch_power)
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
    # On crée le jeu sans passer le nom ni le nombre ici
    game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
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
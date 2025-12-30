# -*- coding: utf-8 -*-
import arcade
import random
import time
from enum import Enum 
import math
import os
import socket
from dotenv import load_dotenv
import speech_recognition as sr
import threading
import math
import json

load_dotenv() 

from game_core import GameManager, Player 
from enums_and_roles import Camp, NightAction, Role

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

class NetworkHandler:
    def __init__(self, game_instance):
        self.game = game_instance
        self.socket = None
        self.conn = None
        self.is_host = False
        self.running = False

    def start_host(self, port=5555):
        """Lance le serveur sans bloquer l'affichage Arcade."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('0.0.0.0', port))
        self.socket.listen(1)
        self.is_host = True
        self.running = True
    
        # On utilise un Thread pour que .accept() ne fige pas le jeu
        accept_thread = threading.Thread(target=self._wait_for_client, daemon=True)
        accept_thread.start()

    def _wait_for_client(self):
        """Cette fonction tourne en arrière-plan."""
        print("Hôte : En attente du Joueur 2...")
        self.conn, addr = self.socket.accept() # C'est ici que ça bloquait
        print(f"Joueur 2 connecté depuis {addr}")
        self._start_listening()

    def _accept_connection(self):
        self.conn, addr = self.socket.accept()
        print(f"Connecté avec : {addr}")
        self._start_listening()

    def connect_to_host(self, ip, port=5555):
        """Lance la connexion dans un thread pour ne pas figer Arcade."""
        self.target_ip = ip
        self.target_port = port
        self.is_host = False
        
        # On lance la tentative de connexion en arrière-plan
        connect_thread = threading.Thread(target=self._async_connect, daemon=True)
        connect_thread.start()

    def _async_connect(self):
        """Tentative de connexion réelle."""
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Timeout court pour ne pas attendre indéfiniment
            self.conn.settimeout(4) 
            self.conn.connect((self.target_ip, self.target_port))
            self.conn.settimeout(None) # Repasser en mode normal
            self.running = True
            print(f"✅ Connecté à l'hôte {self.target_ip}")
            
            ip_succes = self.target_ip
            arcade.schedule(lambda dt: self.game.log_messages.append(f"✅ Connecté à {ip_succes}"), 0)
            
            self._start_listening()

        except Exception as err:
            # CRUCIAL : On transforme l'exception en chaîne de caractères immédiatement
            error_msg = str(err)
            arcade.schedule(lambda dt: self.game.log_messages.append(f"❌ Échec connexion : {error_msg}"), 0)

    def _start_listening(self):
        thread = threading.Thread(target=self._receive_loop, daemon=True)
        thread.start()

    def _receive_loop(self):
        while self.running:
            try:
                data = self.conn.recv(4096).decode('utf-8')
                if data:
                    packet = json.loads(data)
                    self.handle_network_packet(packet)
            except:
                self.running = False

    def send(self, data):
        """Envoie un dictionnaire Python converti en JSON."""
        if self.conn:
            self.conn.sendall(json.dumps(data).encode('utf-8'))

    def handle_network_packet(self, packet):
        """Traite les données reçues du réseau."""
        if packet["type"] == "CHAT":
            msg = f"🗣️ {packet['sender']} : {packet['text']}"
            # On ajoute le message au log du jeu
            arcade.schedule(lambda dt: self.game.handle_network_packet(packet), 0)
        
            if self.is_host:
                self.send(packet)

        # CE BLOC DOIT ÊTRE ALIGNÉ ICI (Pas à l'intérieur du bloc CHAT)
        elif packet["type"] == "START_GAME":
            print("Signal de lancement reçu par le client !")
            # On demande au jeu de lancer la phase de démarrage
            arcade.schedule(lambda dt: self.game._finalize_setup_and_start(), 0)

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

        l = self.center_x - self.width / 2
        r = self.center_x + self.width / 2
        b = self.center_y - self.height / 2
        t = self.center_y + self.height / 2

        arcade.draw_lrbt_rectangle_filled(l, r, b, t, color)
        
        arcade.draw_lrbt_rectangle_outline(l, r, b, t, arcade.color.WHITE, 1)

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

        l, r, b, t = self.x, self.x + self.width, self.y, self.y + self.height


        bg_color = (20, 20, 20, 180) if not self.active else (40, 40, 40, 220)
        
        arcade.draw_lrbt_rectangle_filled(l, r, b, t, bg_color)

        border_color = arcade.color.CYAN if self.active else (100, 100, 100, 150)
        border_width = 2 if self.active else 1
        
        arcade.draw_lrbt_rectangle_outline(l, r, b, t, border_color, border_width)

        cursor = ("_" if self.active and int(time.time() * 2) % 2 == 0 else "")
        
        if not self.text and not self.active:
            arcade.draw_text("Écrire un message...", self.x + 10, self.y + 8, 
                             (150, 150, 150), 12, italic=True)
        else:
            arcade.draw_text(f"{self.text}{cursor}", self.x + 10, self.y + 8, 
                             arcade.color.WHITE, 13)
        
        if self.send_button:
            self.send_button.draw()
        if self.stt_button: 
             self.stt_button.draw()
            
    def update_position(self, x, y, width):
        """Met à jour la position et la taille après un redimensionnement."""
        self.x = x
        self.y = y
        self.width = width
        
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
            nom_joueur = self.game.human_player.name
        
            # Envoi local 
            self.game.log_messages.append(f"🗣️ {nom_joueur} : {message}")
        
        
        if self.game.network and self.game.network.running:
            self.game.network.send({
                "type": "CHAT", 
                "sender": nom_joueur, 
                "text": message
            })
            
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
    
    def __init__(self, width, height, title, is_host=True):
        super().__init__(width, height, title, resizable=True)

        self.network = NetworkHandler(self) 
        self.target_ip = "127.0.0.1"
        self.ip_input_active = False
        self.game_manager = None

        self.receive_thread = threading.Thread(target=self._network_receive_loop, daemon=True)

        self.set_update_rate(1/60)

        self.menu_human_name = "Lucie"
        self.menu_num_players = 11
        self.name_input_active = False

        self.chaos_mode = False
        self.btn_chaos = MenuButton(0, 0, 180, 40, "!! CHAOS !! : CLASSIQUE", "INVOQUER LE CHAOS")

        self.menu_num_wolves = 3  # Valeur par défaut
        self.btn_wolf_plus = MenuButton(0, 0, 40, 40, "+", "WOLF_PLUS")
        self.btn_wolf_minus = MenuButton(0, 0, 40, 40, "-", "WOLF_MINUS")

        self.difficulty_levels = ["DEBUTANT", "NORMAL", "EXPERT"]
        self.menu_diff_index = 1  # "NORMAL" par défaut

        self.btn_diff_prev = MenuButton(0, 0, 40, 40, "<", "DIFF_PREV")
        self.btn_diff_next = MenuButton(0, 0, 40, 40, ">", "DIFF_NEXT")
        
        self.available_roles = 0  # Par défaut : ALEATOIRE
        
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
        self.cupid_indicators = arcade.SpriteList()

        # --- PARAMÈTRES DU DÉBAT ---
        self.debate_timer = 10 
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 
        self.typing_delay = 4 
        self.messages_generated = 0 
        self.max_messages_per_debate = 20 
        self.message_is_complete = False 
        
        # --- INITIALISATION UI ET STT ---
        self._setup_ui_elements() 
        self._init_stt()

        self.sound_start_game = None
        try:
            if os.path.exists("sounds/start.mp3"):
                self.sound_start_game = arcade.load_sound("sounds/start.mp3")
        except Exception as e:
            print(f"Erreur chargement son de démarrage : {e}")

        # Sélection du rôle
        self.available_roles = [
            "ALEATOIRE",
            Role.VILLAGEOIS, Role.LOUP, Role.VOYANTE, Role.SORCIERE, 
            Role.CHASSEUR, Role.CUPIDON, Role.SALVATEUR, Role.ANCIEN
        ]
        self.menu_role_index = 0  # 
        self.btn_role_next = MenuButton(0, 0, 40, 40, ">", "NEXT_ROLE")
        self.btn_role_prev = MenuButton(0, 0, 40, 40, "<", "PREV_ROLE")

        self.debate_duration_setup = 60
        self.setup_buttons = []

        self.witch_choosing_target = False

    def handle_network_packet(self, packet):
        """Traite les données reçues du réseau."""
        if packet["type"] == "CHAT":
            msg = f"🗣️ {packet['sender']} : {packet['text']}"
            # On ajoute le message au log du jeu
            arcade.schedule(lambda dt: self.game.handle_network_packet(packet), 0)
        
            if self.is_host:
                self.send(packet)

        # CE BLOC DOIT ÊTRE ALIGNÉ ICI (Pas à l'intérieur du bloc CHAT)
        elif packet["type"] == "START_GAME":
            print("Signal de lancement reçu par le client !")
            # On demande au jeu de lancer la phase de démarrage
            arcade.schedule(lambda dt: self.game._finalize_setup_and_start(), 0)
    
    def _network_receive_loop(self):
        """Boucle tournant dans un thread séparé pour recevoir les paquets."""
        while True:
            # On vérifie si une connexion est établie ET active
            if self.network and self.network.conn:
                try:
                    data = self.network.conn.recv(4096).decode('utf-8')
                    if data:
                        packet = json.loads(data)
                        arcade.schedule(lambda dt: self.handle_network_packet(packet), 0)
                except (ConnectionResetError, ConnectionAbortedError):
                    print("La connexion a été perdue.")
                    self.network.conn = None
                    break
                except Exception as e:
                    # Évite d'inonder la console si le socket n'est pas encore prêt
                    pass
        
        time.sleep(0.2)  # Laisse respirer le processeur

    def _init_sounds(self):
        """Centralisation du chargement des sons et création des attributs."""
        self.sounds = {}
    
        # Mapping entre la clé du dictionnaire et le nom de l'attribut utilisé dans le jeu
        sound_files = {
            "start": ("sounds/start.mp3", "sound_start_game"),
            "ambient": ("sounds/ambient_night.mp3", "bg_music"),
            "ancient": ("sounds/ancient_shield.mp3", "sound_ancient_power"),
            "guardian": ("sounds/guardian_protect.mp3", "sound_guardian_power"),
            "cupid": ("sounds/cupid_power.mp3", "sound_cupid_power"),
            "hunter": ("sounds/hunter_shot.mp3", "sound_hunter_shot"),
            "seer": ("sounds/seer_power.mp3", "sound_seer_power"),
            "villager_death": ("sounds/villager_death.mp3", "sound_villager_death"),
            "witch": ("sounds/witch_power.mp3", "sound_witch_power"),
            "wolf_kill": ("sounds/wolf_kill.mp3", "sound_wolf_kill")
        }

        for _, attr_name in sound_files.values():
            setattr(self, attr_name, None)

        for key, (path, attr_name) in sound_files.items():
            if os.path.exists(path):
                try:
                    if key == "ambient":
                        # Chargement de la musique d'ambiance en streaming
                        sound_obj = arcade.load_sound(path, streaming=True)
                        setattr(self, attr_name, sound_obj)
                        self.music_player = arcade.play_sound(sound_obj, volume=0.15, loop=True)
                    else:
                        # Chargement des effets sonores standards
                        sound_obj = arcade.load_sound(path)
                        self.sounds[key] = sound_obj
                        setattr(self, attr_name, sound_obj)
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
        night_message = self.game_manager._night_phase()
        
        arcade.schedule(lambda dt: self._finalize_night(night_message), 0)

    def _finalize_night(self, message):

        arcade.unschedule(self._finalize_night) 

        self.log_messages.append(message)

        # 2. GESTION DES SONS DE MORT (LOUPS)
        if "tué par les Loups" in message:
            if self.sound_wolf_kill:
                arcade.play_sound(self.sound_wolf_kill)

        # 3. GESTION DU SON DU CHASSEUR
        if self.game_manager.hunter_just_shot:
            if self.sound_hunter_shot:
                arcade.play_sound(self.sound_hunter_shot)
            self.game_manager.hunter_just_shot = False

        if self.game_manager.ancient_shield_triggered:
            if self.sound_ancient_power:
                arcade.play_sound(self.sound_ancient_power)
            self.game_manager.ancient_shield_triggered = False

        # 4. Transition d'état vers le jour (Débat)
        self.game_manager.day += 1
        self.night_processing = False
        self.current_state = GameState.DEBATE
        
        # Réinitialisation des paramètres de débat
        self.debate_timer = self.game_manager.debate_duration
        self.messages_generated = 0
        self.current_speaker = None
        self.message_is_complete = False

        self.debate_timer = self.game_manager.debate_duration
        
        self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le soleil se lève sur le village.")

    # --- Méthodes de gestion de l'État ---

    def _setup_ui_elements(self):
        """Initialise/Recalcule la position des éléments d'interface utilisateur."""
        PANEL_WIDTH = self.width // 3 
        INPUT_HEIGHT = 30
        input_y = 5 
        input_x = self.width - PANEL_WIDTH - 10 
        input_width = PANEL_WIDTH - 180 
        
        if not hasattr(self, 'chat_input'):
            self.chat_input = ChatInput(input_x, input_y, input_width, INPUT_HEIGHT, self)
        else:
            self.chat_input.update_position(input_x, input_y, input_width)
        
        self.chat_input.send_button = MenuButton(
            input_x + input_width + 45, input_y + INPUT_HEIGHT / 2, 80, INPUT_HEIGHT, "Envoyer", "SEND_MESSAGE"
        )
        self.stt_button = MenuButton(
            input_x + input_width + 135, input_y + INPUT_HEIGHT / 2, 80, INPUT_HEIGHT, "Parler", "START_STT"
        )
        self.chat_input.stt_button = self.stt_button

        cx = self.width / 2
        cy = self.height / 2

        if self.current_state == GameState.SETUP:
            y_role = cy - 30 
            if hasattr(self, 'btn_role_prev'):
                self.btn_role_prev.center_x, self.btn_role_prev.center_y = cx - 220, y_role
            if hasattr(self, 'btn_role_next'):
                self.btn_role_next.center_x, self.btn_role_next.center_y = cx + 220, y_role

            self.btn_chaos.center_x, self.btn_chaos.center_y = cx, 280

            y_lancer  = 70   # Le bouton vert tout en bas
            y_reseau  = 160  # Les boutons Héberger/Rejoindre au-dessus
            y_ip_text = 210  # Le texte de l'IP juste au-dessus
            y_temps   = 270  # Le réglage du temps encore au-dessus
            y_chaos   = 340

            # 1. Rôles (haut)
            y_role = cy - 30 
            if hasattr(self, 'btn_role_prev'):
                self.btn_role_prev.center_x, self.btn_role_prev.center_y = cx - 220, y_role
            if hasattr(self, 'btn_role_next'):
                self.btn_role_next.center_x, self.btn_role_next.center_y = cx + 220, y_role

            # 2. Chaos
            self.btn_chaos.center_x, self.btn_chaos.center_y = cx, y_chaos

            # 3. Temps du débat
            self.setup_buttons = [
                MenuButton(cx - 160, y_temps, 40, 40, "-", "DEC_TIME"),
                MenuButton(cx + 160, y_temps, 40, 40, "+", "INC_TIME")
            ]

            # 2. Boutons Réseau (Héberger / Rejoindre)
            self.btn_host = MenuButton(cx - 110, y_reseau, 180, 50, "HÉBERGER", "START_HOST")
            self.btn_join = MenuButton(cx + 110, y_reseau, 180, 50, "REJOINDRE", "START_JOIN")

            self.setup_buttons = [
                MenuButton(cx - 200, y_temps, 40, 40, "-", "DEC_TIME"),
                MenuButton(cx + 200, y_temps, 40, 40, "+", "INC_TIME")
            ]

            # 3. Bouton Lancer la partie
            self.start_button = MenuButton(cx, y_lancer, 320, 70, "LANCER LA PARTIE", "START_GAME")
            
            # On garde ces valeurs en mémoire pour le dessin
            self.y_ip_text = y_ip_text
            self.y_temps_text = y_temps
        
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
        max_dim = min(self.width, self.height)
        if num_players <= 12:
            CIRCLE_RADIUS = max_dim * 0.35
        else:
            CIRCLE_RADIUS = max_dim * 0.40
        
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
        """Prépare la transition vers la nuit et vérifie si l'humain peut agir."""
        self.night_processing = False

        active_night_actions = [NightAction.INVESTIGATE, NightAction.POTION, NightAction.PROTECT] 

        can_human_act = (
            self.human_player and 
            self.human_player.is_alive and 
            self.human_player.role and 
            (self.human_player.role.night_action in active_night_actions) and
            self.game_manager.day > 1
        )

        if can_human_act:
            self.current_state = GameState.NIGHT_HUMAN_ACTION
            self._display_human_night_action_buttons()
            self.log_messages.append(f"C'est à vous d'agir ({self.human_player.role.name}).")
        else:
            self.current_state = GameState.NIGHT_IA_ACTION
            self.night_processing = False
    
        for player in self.game_manager.players:
            player.has_acted_this_night = False
    
        self.log_messages.append("🌙 La nuit tombe...")

    def _display_human_night_action_buttons(self):
        """Génère les boutons de la Sorcière et maintient l'état interactif."""
        self.action_buttons = []
        cx = self.width / 2
        button_y = 70

        self.current_state = GameState.NIGHT_HUMAN_ACTION
        if self.human_player.role == Role.SORCIERE:
            has_life = getattr(self.human_player, 'has_life_potion', True)
            has_kill = getattr(self.human_player, 'has_kill_potion', True)
            victim = getattr(self.game_manager, 'victim_of_wolves', None)

        if has_life and victim:
            self.action_buttons.append(MenuButton(cx - 160, button_y, 140, 45, f"SAUVER {victim}", "SAUVER"))
            self.log_messages.append(f"🧪 Sorcière : {victim} a été attaqué(e).")
        
        if has_kill:
            x_pos = cx if not (has_life and victim) else cx
            self.action_buttons.append(MenuButton(x_pos, button_y, 140, 45, "TUER", "TUER"))
        
        self.action_buttons.append(MenuButton(cx + 160, button_y, 120, 45, "PASSER", "PASSER"))
            
        if not victim:
            self.log_messages.append("🧪 Sorcière : Pas de victime des loups détectée pour l'instant.")

    def on_mouse_press(self, x, y, button, modifiers):
        """Dispatche les clics de souris vers les fonctions spécialisées selon l'état."""

        # Le Chat
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.check_click(x, y)
            if self.chat_input.active:
                return

        print(f"Clic détecté aux coordonnées : x={x}, y={y}") 

        # DISPATCH SELON L'ÉTAT
        if self.current_state == GameState.SETUP:
            cx = self.width / 2
            cy = self.height / 2
            y_ip = 205 # Assurez-vous que cette valeur est identique à celle de _draw_setup_menu

            # --- DÉTECTION CLIC SUR CHAMP IP ---
            if cx - 150 < x < cx + 150 and 190 < y < 230:
                print("--- FOCUS SUR IP ACTIVE ---")
                self.ip_input_active = True
                self.name_input_active = False # Désactive le nom si vous l'aviez
                return
            
            # --- DÉSACTIVATION SI CLIC AILLEURS ---
            # Si on clique ailleurs, on désactive les saisies (sauf si c'est un bouton)
            self.ip_input_active = False
            self.name_input_active = False

            # 2. Gestion des autres boutons de setup (Joueurs, Loups, Start)
            self._handle_setup_clicks(x, y)

            # --- DÉTECTION CLIC SUR CHAMP NOM ---
            # (Zone autour de cy + 170 où est dessiné le nom)
            if cx - 150 < x < cx + 150 and (cy + 170) - 20 < y < (cy + 170) + 20:
                self.name_input_active = True
                self.ip_input_active = False
                return

            # 1. Vérification des boutons de réglage du temps (+/-)
            for btn in self.setup_buttons:
                if btn.check_click(x, y):
                    # On définit 'action' UNIQUEMENT si le clic est confirmé
                    action = btn.action 
                    
                    if action == "INC_TIME":
                        self.debate_duration_setup = min(300, self.debate_duration_setup + 10)
                    elif action == "DEC_TIME":
                        self.debate_duration_setup = max(10, self.debate_duration_setup - 10)
                    return # Sortie immédiate après avoir traité le clic
            
        elif self.current_state == GameState.CUPID_ACTION:
            self._handle_cupid_selection_click(x, y)

        elif self.current_state == GameState.NIGHT_HUMAN_ACTION:
            self._handle_night_human_clicks(x, y)

        elif self.current_state == GameState.HUMAN_ACTION:
            self._handle_voting_clicks(x, y)

        self._update_cupid_visuals()

    def _handle_setup_clicks(self, x, y):
        """Gère tous les clics dans le menu de configuration."""
        # Boutons Joueurs
        if self.btn_plus.check_click(x, y):
            self.menu_num_players = min(15, self.menu_num_players + 1)
        elif self.btn_minus.check_click(x, y):
            self.menu_num_players = max(6, self.menu_num_players - 1)
        
        # Boutons Loups
        elif self.btn_wolf_plus.check_click(x, y):
            self.menu_num_wolves = min(self.menu_num_players // 2, self.menu_num_wolves + 1)
        elif self.btn_wolf_minus.check_click(x, y):
            self.menu_num_wolves = max(1, self.menu_num_wolves - 1)

        # Boutons Rôles
        elif self.btn_role_next.check_click(x, y):
            self.menu_role_index = (self.menu_role_index + 1) % len(self.available_roles)
        elif self.btn_role_prev.check_click(x, y):
            self.menu_role_index = (self.menu_role_index - 1) % len(self.available_roles)
        
        # Boutons Difficulté
        elif self.btn_diff_next.check_click(x, y):
            self.menu_diff_index = (self.menu_diff_index + 1) % len(self.difficulty_levels)
        elif self.btn_diff_prev.check_click(x, y):
            self.menu_diff_index = (self.menu_diff_index - 1) % len(self.difficulty_levels)

        # Mode Chaos
        elif self.btn_chaos.check_click(x, y):
            self.chaos_mode = not self.chaos_mode
            self.btn_chaos.text = f"!! CHAOS !! : {'INVOQUER LE CHAOS' if self.chaos_mode else 'CLASSIQUE'}"

        # Bouton Lancer la partie
        elif self.start_button.check_click(x, y):
            self._finalize_setup_and_start()

        elif self.btn_host.check_click(x, y):
            self.log_messages.append("🌐 Tentative d'hébergement...")
            self.network.start_host()
            if not self.receive_thread.is_alive():
                self.receive_thread.start()

        elif self.btn_join.check_click(x, y):
            print("Bouton Rejoindre cliqué") # Pour tester
            self.log_messages.append(f"🔌 Connexion à {self.target_ip}...")
            # On utilise la nouvelle version non-bloquante de connect_to_host
            self.network.connect_to_host(self.target_ip)

    def _handle_seer_click(self, x, y):
        for name, sprite in self.player_map.items():
            if sprite.collides_with_point((x, y)):
                target = self.game_manager.get_player_by_name(name)
            
                # On vérifie que la cible est valide
                if target and target.is_alive and target != self.human_player:
                    # 1. Marquer l'action comme faite
                    self.human_player.has_acted_this_night = True
                
                    # 2. Révéler le rôle
                    role_name = target.role.name
                    self.log_messages.append(f"🔮 La Voyante voit que {name} est {role_name} !")
                
                    # 3. Passer à la phase suivante (IA ou Loups)
                    self.current_state = GameState.NIGHT_IA_ACTION
                    return
                
    def _update_cupid_visuals(self):
        
        if self.game_manager is None:
            return
        
        self.cupid_indicators.clear()

        # --- 1. CROIX ROUGE POUR TOUS LES MORTS ---
        for player in self.game_manager.players:
            if not player.is_alive:
                sprite = self.player_map.get(player.name)
                if sprite:
                    # On crée un "X" avec deux traits rouges
                    size = int(sprite.width * 0.8)
                    thickness = 5 # Croix bien visible
                    
                    # Branche 1 : \
                    line1 = arcade.SpriteSolidColor(size, thickness, arcade.color.RED)
                    line1.position, line1.angle = sprite.position, 45
                    self.cupid_indicators.append(line1)
                    
                    # Branche 2 : /
                    line2 = arcade.SpriteSolidColor(size, 5, arcade.color.RED)
                    line2.position, line2.angle = sprite.position, -45
                    self.cupid_indicators.append(line2)

        if self.game_manager.lovers and len(self.game_manager.lovers) == 2:
            n1, n2 = self.game_manager.lovers
            s1, s2 = self.player_map.get(n1), self.player_map.get(n2)
            p1, p2 = self.game_manager.get_player_by_name(n1), self.game_manager.get_player_by_name(n2)
        
            if s1 and s2 and p1 and p2 and p1.is_alive and p2.is_alive:
                
                # 2. TEXTES : On les monte à +85 pour éviter la superposition
                for s in [s1, s2]:
                    # Le texte "UwU"
                    uwu = arcade.create_text_sprite(text="UwU", color=arcade.color.RED, font_size=14)
                    uwu.center_x = s.center_x - 15
                    uwu.center_y = s.center_y + 85  # Augmenté pour être au-dessus du nom
                    self.cupid_indicators.append(uwu)

                    # Le coeur
                    heart = arcade.create_text_sprite(text="❤️", color=arcade.color.RED, font_size=18)
                    heart.center_x = s.center_x + 20
                    heart.center_y = s.center_y + 85
                    self.cupid_indicators.append(heart)
                
    def _handle_cupid_selection_click(self, x, y):
        """Gère la sélection des amoureux et valide le lien."""
        selected_name = None

        # 1. Identifier le joueur cliqué
        for name, sprite in self.player_map.items():
            if sprite.collides_with_point((x, y)):
                selected_name = name
                break
            
        if not selected_name:
            return 

        player = self.game_manager.get_player_by_name(selected_name)

        # 2. Ajouter à la sélection si valide
        if player and player.is_alive and selected_name not in self.cupid_targets:
            self.cupid_targets.append(selected_name)
            self.log_messages.append(f"💘 {selected_name} sélectionné...")
            self._update_cupid_visuals()
    
        # 3. Validation : UNIQUEMENT quand on a atteint DEUX joueurs
        if len(self.cupid_targets) == 2:
            p1, p2 = self.cupid_targets
        
            # On crée le lien dans le moteur
            msg = self.game_manager.bind_lovers(p1, p2)
        
            # On affiche le message de confirmation
            if msg:
                self.log_messages.append(msg)
        
            self.cupid_targets = []
            self.game_manager.is_cupid_phase_done = True
        
            self._update_cupid_visuals() 
        
            # Transition vers la suite du jeu
            self.game_manager.day = 1 
            self._start_night_phase()

    def _handle_night_human_clicks(self, x, y):
        
        if self.action_buttons:
            for btn in self.action_buttons:
                if btn.check_click(x, y):
                    self._handle_human_night_action_click(x, y)
                    return
        
        if self.witch_choosing_target:
            for name, sprite in self.player_map.items():
                if sprite.collides_with_point((x, y)):
                    target = self.game_manager.get_player_by_name(name)
                    if target and target.is_alive and target != self.human_player:
                        target.is_alive = False
                        self.human_player.has_kill_potion = False
                        self.game_manager.night_kill_target = name 
                        self.log_messages.append(f"🧪 La Sorcière a empoisonné {name}.")
                    
                        # C'est seulement ICI qu'on termine le tour
                        self.witch_choosing_target = False
                        self.current_state = GameState.NIGHT_IA_ACTION
                        self.night_processing = False
                        return
                
        if self.human_player.role == Role.VOYANTE and not self.human_player.has_acted_this_night:
            for name, sprite in self.player_map.items():
                if sprite.collides_with_point((x, y)):
                    self._logic_seer_action(f"ENQUÊTER:{name}")
                    self.human_player.has_acted_this_night = True
                    self.current_state = GameState.NIGHT_IA_ACTION
                    break

    def _handle_voting_clicks(self, x, y):
        """Gère le clic sur les boutons de vote."""
        for btn in self.action_buttons:
            if btn.check_click(x, y):
                voted_player_name = btn.action
                self.log_messages.append(f"🗳️ {self.human_player.name} vote pour {voted_player_name}")
                self.game_manager.register_human_vote(voted_player_name)
                self.action_buttons = [] 
                self.current_state = GameState.VOTING
                break

    def _finalize_setup_and_start(self):
        """Initialise le moteur de jeu et lance la première phase."""

        if self.current_state != GameState.SETUP:
            return

        # Si on est l'hôte, on prévient le client avant de démarrer localement
        if self.network and self.network.is_host and self.network.running:
            print("Envoi du signal de lancement au réseau...")
            self.network.send({"type": "START_GAME"})

        diff_choisie = self.difficulty_levels[self.menu_diff_index]
        self.game_manager = GameManager(
            human_player_name=self.menu_human_name,
            num_players_total=self.menu_num_players,
            difficulty=diff_choisie
        )

        selected_role = self.available_roles[self.menu_role_index]
        if selected_role == "ALEATOIRE":
            selected_role = random.choice(self.available_roles[1:])
        
        self.human_player = self.game_manager.human_player
        self.human_player.assign_role(selected_role)
        self.game_manager._distribute_roles_after_human_choice(
            selected_role, 
            num_wolves_chosen=self.menu_num_wolves
        )

        self._setup_sprites()
        self._setup_ui_elements()
        
        if self.sound_start_game:
            arcade.play_sound(self.sound_start_game) 
        
        self.start_game_loop()

        # Transition Cupidon ou Nuit
        cupidon = self.game_manager.get_player_by_role(Role.CUPIDON)
        if cupidon and cupidon.is_human and not self.game_manager.is_cupid_phase_done:
            self.current_state = GameState.CUPID_ACTION
            self.log_messages.append("💘 Cupidon : Choisis DEUX joueurs à lier.")
        else:
            self.game_manager.day = 1 
            self._start_night_phase()

        self.game_manager.debate_duration = self.debate_duration_setup

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
            self.is_listening = False
            self.log_messages.append("🎙️ Micro désactivé.")

    def _listen_for_speech(self):
        """Tente d'écouter et de reconnaître la parole."""
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source)
            try:
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
            
            self.chat_input.text = recognized_text
            self.log_messages.append(f"✅ Reconnaissance vocale : {recognized_text[:40]}...")

        except sr.UnknownValueError:
            self.log_messages.append("❌ Je n'ai pas compris la parole. Réessayez.")
        except sr.RequestError as e:
            self.log_messages.append(f"❌ Erreur de l'API Google Speech : {e}")
        finally:
            self.is_listening = False


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

    def on_text(self, text):
        """Reçoit directement les caractères imprimables (gère Shift, ., etc.)"""
        # Si on est en train de taper l'IP
        if self.ip_input_active:
            if text in "0123456789.":
                self.target_ip += text
            return

        # Si on est en train de taper le nom
        if self.name_input_active:
            if text.isalnum() and len(self.menu_human_name) < 12:
                self.menu_human_name += text
            return

    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (y compris la saisie du chat)."""

        # --- PRIORITÉ 1 : SAISIE DE L'IP ---
        if self.ip_input_active:
            if symbol == arcade.key.BACKSPACE:
                self.target_ip = self.target_ip[:-1]
            elif symbol == arcade.key.ENTER:
                self.ip_input_active = False
            
        # --- PRIORITÉ 2 : MENU SETUP (NOM) ---
        if self.current_state == GameState.SETUP:
            # On n'écrit le nom que si le champ IP n'est pas actif
            if symbol == arcade.key.BACKSPACE:
                self.menu_human_name = self.menu_human_name[:-1]
            elif symbol == arcade.key.ENTER:
                # Appuyer sur Enter peut valider le nom ou enlever le focus
                pass
            elif len(self.menu_human_name) < 12:
                try:
                    char = chr(symbol)
                    if char.isalnum():
                        if (modifiers & arcade.key.MOD_SHIFT) or self.key_is_caps:
                            self.menu_human_name += char.upper()
                        else:
                            self.menu_human_name += char.lower()
                except ValueError:
                    pass
            return

        # --- PRIORITÉ 3 : CHAT PENDANT LE DÉBAT ---
        if self.chat_input.active:
            if symbol == arcade.key.ESCAPE:
                self.chat_input.active = False
                return
            self.chat_input.handle_key_press(symbol, modifiers)
            return
    
        # --- RACCOURCIS GÉNÉRAUX ---
        if symbol == arcade.key.F:
            self.set_fullscreen(not self.fullscreen)
        elif symbol == arcade.key.CAPSLOCK:
            self.key_is_caps = not self.key_is_caps
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
        """Dessine le menu avec un espacement horizontal et vertical aéré."""
        if hasattr(self, 'menu_bg_sprite'):
            self.menu_bg_sprite.width = self.width
            self.menu_bg_sprite.height = self.height
            self.menu_bg_sprite.center_x = self.width / 2
            self.menu_bg_sprite.center_y = self.height / 2
            self.menu_background_list.draw()
            
        cx = self.width / 2
        cy = self.height / 2  
        y_temps = 270 
        y_ip = 210        

        # --- TITRE ET NOM ---
        arcade.draw_text("CONFIGURATION", cx, cy + 240, arcade.color.WHITE, 35, anchor_x="center", bold=True)
        arcade.draw_text(f"Nom : {self.menu_human_name}", cx, cy + 170, arcade.color.CYAN, 22, anchor_x="center")

        # --- RÉGLAGES (JOUEURS, LOUPS, IA) ---
        arcade.draw_text(f"Nombre de joueurs : {self.menu_num_players}", cx, cy + 90, arcade.color.WHITE, 20, anchor_x="center")
        self.btn_minus.draw()
        self.btn_plus.draw()

        arcade.draw_text(f"Nombre de Loups : {self.menu_num_wolves}", cx, cy + 50, arcade.color.RED, 20, anchor_x="center")
        self.btn_wolf_minus.draw()
        self.btn_wolf_plus.draw()

        diff_text = self.difficulty_levels[self.menu_diff_index]
        diff_color = [arcade.color.GREEN, arcade.color.WHITE, arcade.color.RED][self.menu_diff_index]
        arcade.draw_text(f"IA : {diff_text}", cx, cy + 10, diff_color, 20, anchor_x="center")
        self.btn_diff_prev.draw()
        self.btn_diff_next.draw()

        # --- RÔLE SOUHAITÉ ---
        current_role = self.available_roles[self.menu_role_index]
        role_name = "🎲 Aléatoire" if current_role == "ALEATOIRE" else current_role.value["name"]
        role_color = arcade.color.LIGHT_SKY_BLUE if current_role == "ALEATOIRE" else arcade.color.GOLD
        arcade.draw_text(f"Rôle souhaité : {role_name}", cx, cy - 40, role_color, 20, anchor_x="center")
        self.btn_role_prev.draw()
        self.btn_role_next.draw()

        # --- CHAOS ET TEMPS ---
        self.btn_chaos.color = arcade.color.DARK_RED if self.chaos_mode else arcade.color.GRAY
        self.btn_chaos.draw()

        color_ip = arcade.color.YELLOW if self.ip_input_active else arcade.color.WHITE
        cursor = "_" if self.ip_input_active and int(time.time() * 2) % 2 == 0 else ""
        
        arcade.draw_text(f"IP Serveur : {self.target_ip}{cursor}", cx, y_ip, color_ip, 18, anchor_x="center")

        # Vérification de sécurité pour éviter le crash
        if hasattr(self, 'btn_host') and hasattr(self.btn_host, 'draw'):
            self.btn_host.draw()
        if hasattr(self, 'btn_join') and hasattr(self.btn_join, 'draw'):
            self.btn_join.draw()

        arcade.draw_text(f"Temps du débat : {self.debate_duration_setup}s", 
                         cx, y_temps - 5, arcade.color.WHITE, 18, 
                         anchor_x="center", bold=True)
        
        for btn in self.setup_buttons:
            btn.draw()

        self.start_button.draw()

    def on_draw(self):
        """Fonction de rendu principale : organise l'ordre des calques."""
        self.clear()
    
        # 1. ÉTAT SETUP : Menu de configuration uniquement
        if self.current_state == GameState.SETUP:           
            self._draw_setup_menu()

            for btn in self.setup_buttons:
                btn.draw()
            return

        # 2. SÉCURITÉ : Vérification de l'existence du moteur
        if self.game_manager is None or self.human_player is None:
            return
    
        # 3. ÉTAPE DE JEU : Dessin par couches (du bas vers le haut)
        self._draw_background_layer()    # Fond et décor
        self._draw_game_elements()       # Sprites, indicateurs, croix
        self._draw_player_labels_layer() # Noms, rôles et badges
        self._draw_ui_overlay_layer()    # Log, status et bulles de chat
        self._draw_interactive_layer()   # Chat input et boutons (Priorité clic)

    def _draw_background_layer(self):
        """Dessine le décor de fond et le feu de camp parfaitement centrés."""
        if self.background_sprite:
            self.background_sprite.width = self.width
            self.background_sprite.height = self.height
            self.background_sprite.center_x = self.width / 2
            self.background_sprite.center_y = self.height / 2
            self.background_list.draw()
    
        if self.campfire_sprite:
            self.campfire_sprite.center_x = self.width / 2
            self.campfire_sprite.center_y = self.height / 2 - 100
            self.campfire_list.draw()

    def _draw_game_elements(self):
        """Dessine les avatars des joueurs et les indicateurs (Cupidon, morts)."""
        self.player_sprites.draw()
        if hasattr(self, 'cupid_indicators'):
            self.cupid_indicators.draw()

    def _draw_player_labels_layer(self):
        """Affiche les noms colorés et les rôles au-dessus des sprites."""
        human_is_wolf = (self.human_player.role and self.human_player.role.camp == Camp.LOUP)
        wolf_teammates = getattr(self.human_player, 'wolf_teammates', [])
    
        for player in self.game_manager.players:
            sprite = self.player_map.get(player.name)
            if sprite:
                color = arcade.color.WHITE
                if not player.is_alive:
                    color = arcade.color.RED
                elif human_is_wolf and (player.is_human or player.name in wolf_teammates):
                    color = arcade.color.YELLOW
            
            # Nom
            arcade.draw_text(f"{player.name}", sprite.center_x, sprite.center_y + 60, color, 12, anchor_x="center")
            # Rôle (si mort ou fin de partie)
            if self.current_state == GameState.GAME_OVER or player.is_human:
                arcade.draw_text(f"Role: {player.role.name}", sprite.center_x, sprite.center_y - 60, arcade.color.YELLOW_GREEN, 10, anchor_x="center")

    def _draw_interactive_layer(self):
        """Dessine les éléments avec lesquels l'utilisateur interagit (Boutons, Chat)."""
        # 1. Boutons d'action (Vote, Nuit)
        for btn in self.action_buttons:
            btn.draw()
            
        # 2. Champ de saisie (Chat) : Dessiné en DERNIER pour être au premier plan
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.draw()

        if self.current_state in [GameState.VOTING, GameState.NIGHT_HUMAN_ACTION, GameState.HUMAN_ACTION]:
            for btn in self.action_buttons:
                btn.draw()

    def _draw_ui_overlay_layer(self):
        """
        Dessine les panneaux d'information et les bulles de chat des IA.
        Ce calque se situe entre les joueurs et les boutons interactifs.
        """
        # 1. Dessiner le Journal de Bord (Historique à gauche)
        self.draw_log()

        # 2. Dessiner le Panneau de Statut (Loups vivants, Timer à droite)
        self.draw_status()
        # 3. Dessiner les bulles de texte au-dessus des têtes des IA qui parlent
        self.draw_localized_chat_bubble()

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
        """Logique : mis à jour à chaque image."""
    
        if self.current_state != GameState.SETUP:
            self._update_cupid_visuals()

        if self.current_state == GameState.SETUP:
            return

        # 3. GESTION DE LA NUIT IA
        if self.current_state == GameState.NIGHT_IA_ACTION:
            if not self.night_processing:
                self.night_processing = True 
                thread = threading.Thread(target=self._async_night_ai, daemon=True)
                thread.start()
        # 4. GESTION DU DÉBAT
        elif self.current_state == GameState.DEBATE:
            self._update_debate(delta_time) 
    
        # 5. GESTION DES VOTES
        elif self.current_state == GameState.VOTING:
            if self.game_manager.vote_counts:
                lynch_target_name = max(self.game_manager.vote_counts, key=self.game_manager.vote_counts.get)
                target_player = self.game_manager.get_player_by_name(lynch_target_name)
                lynch_message = self.game_manager._lynch_result(self.game_manager.get_alive_players())
                self.log_messages.append(lynch_message)
                self.current_state = GameState.RESULT

        # 6. GESTION DES RÉSULTATS ET PASSAGE À LA NUIT SUIVANTE
        elif self.current_state == GameState.RESULT:
            winner = self.game_manager.check_win_condition()
            if winner:
                self.log_messages.append(f"\n🎉 VICTOIRE des {winner.value} !")
                self.current_state = GameState.GAME_OVER
            else:
                self.night_processing = False 
                self._start_night_phase()

    def _handle_human_night_action_click(self, x, y):
        clicked_action_data = None
        for btn in self.action_buttons:
            if btn.check_click(x, y):
                clicked_action_data = btn.action
                break
    
        if not clicked_action_data:
            return

        role_type = self.human_player.role
    
        if role_type == Role.SORCIERE:
            self._logic_witch_action(clicked_action_data)
        
        if clicked_action_data == "TUER":
            self.action_buttons = [] 
            return 
            
        elif role_type == Role.VOYANTE:
            self._logic_seer_action(clicked_action_data)
        elif role_type == Role.SALVATEUR:
            self._logic_guardian_action(clicked_action_data)

        if not getattr(self, 'witch_choosing_target', False):
            self.current_state = GameState.NIGHT_IA_ACTION
            self.night_processing = False
        

    def _logic_seer_action(self, data):
        """Traite la révélation d'un rôle par la Voyante."""
        if ":" in data:
            _, target_name = data.split(":", 1)
            target = self.game_manager.get_player_by_name(target_name)
            if target:
                if self.sound_seer_power:
                    arcade.play_sound(self.sound_seer_power)
                self.log_messages.append(f"🕵️‍♀️ Révélation : {target.name} est **{target.role.name}** ({target.role.camp.value}).")

    def _logic_witch_action(self, data):
        """Gère le clic sur les boutons de la sorcière."""
        if data == "PASSER":
            self.log_messages.append("🧪 Sorcière : Vous gardez vos potions.")
            self.current_state = GameState.NIGHT_IA_ACTION
            self.night_processing = False

        elif data == "SAUVER":
            self.human_player.has_life_potion = False
            self.game_manager.witch_saved_someone = True 
            self.log_messages.append("💖 Sorcière : Vous avez utilisé la potion de vie.")
            self.current_state = GameState.NIGHT_IA_ACTION
            self.night_processing = False

        elif data == "TUER":
            self.witch_choosing_target = True
            self.log_messages.append("💀 Sorcière : Cliquez sur le joueur à éliminer.")
            self.action_buttons = []
            

    def _logic_guardian_action(self, data):
        """Définit la protection du Salvateur pour la nuit en cours."""
        if ":" in data:
            _, target_name = data.split(":", 1)
            self.game_manager.night_protected_target = target_name
            self.human_player.last_protected_target = target_name
            self.log_messages.append(f"🛡️ Le Salvateur protège **{target_name}**.")
    
    def _update_debate(self, delta_time):
        """Gère le cycle de vie du débat : temps global et alternance des orateurs."""
        self.debate_timer -= delta_time
    
        if self.current_speaker and not self.message_is_complete:
            self._process_message_typing()

        if self._is_debate_finished():
            self._end_debate_phase()
                
        elif (self.current_speaker is None or self.message_is_complete) and self.messages_generated < self.max_messages_per_debate: 
            self._start_new_ai_speech()

    def _is_debate_finished(self):
        """Vérifie si le débat doit s'arrêter immédiatement."""
    
        if self.debate_timer <= 0:
            return True
    
        if self.messages_generated >= self.max_messages_per_debate and self.message_is_complete:
            return True
        
        return False

    def _process_message_typing(self):
        """Ajoute les caractères un par un au message affiché."""
        self.typing_speed_counter += 1
        if self.typing_speed_counter >= self.typing_delay:
            current_len = len(self.current_message_display)
            if current_len < len(self.current_message_full):
                self.current_message_display += self.current_message_full[current_len]
            else:
                self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                self.message_is_complete = True
            self.typing_speed_counter = 0

    def _start_new_ai_speech(self):
        """Sélectionne une IA vivante pour générer un nouveau message de débat."""
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.message_is_complete = False 
    
        alive_ais = [p for p in self.game_manager.get_alive_players() if not p.is_human]
    
        if not alive_ais or self.messages_generated >= self.max_messages_per_debate:
            self._end_debate_phase()
            return
        
        if alive_ais:
            speaker = random.choice(alive_ais)
            debate_message = speaker.generate_debate_message(self.game_manager._get_public_status())
        
            self.current_speaker = speaker
            self.current_message_full = debate_message
        
            for listener in [p for p in alive_ais if p != speaker]:
                listener.receive_public_message(speaker.name, debate_message)
            
            self.messages_generated += 1

    def _end_debate_phase(self):
        """Nettoie l'état du débat et bascule vers la phase de vote."""
        if self.current_speaker and not self.message_is_complete:
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

    
    def draw_log(self):
        """Dessine le Journal de Bord (Historique Permanent) à GAUCHE."""
        LOG_X_START = 10
        LOG_WIDTH = self.width // 6
        LOG_HEIGHT = self.height - 40 
        
        arcade.draw_lbwh_rectangle_filled(
            LOG_X_START, 
            10,
            LOG_WIDTH, 
            LOG_HEIGHT, 
            (10, 10, 10, 140) 
        )
        
        x_pos = LOG_X_START + 10
        y_pos = self.height - 30 
        line_spacing = 70 
        
        arcade.draw_text("JOURNAL DE BORD:", x_pos, y_pos, arcade.color.ORANGE_RED, 14)
        y_pos -= 35 
        
        for msg in reversed(self.log_messages):
            if y_pos < 40: 
                break
            
            arcade.draw_text(
                msg, 
                x_pos, 
                y_pos, 
                arcade.color.LIGHT_GRAY, 
                11, 
                width=LOG_WIDTH - 20,
                multiline=True
            )
            y_pos -= line_spacing 
            
    def draw_status(self):
        """Dessine les compteurs (Loups, Timer) à DROITE, en haut."""
        
        PANEL_WIDTH = self.width // 3
        RIGHT_PANEL_START_X = self.width - PANEL_WIDTH

        phase_text = f"JOUR {self.game_manager.day}" if not self.night_processing else f"NUIT {self.game_manager.day}"
        arcade.draw_text(phase_text, RIGHT_PANEL_START_X + 20, self.height - 90, arcade.color.AQUA, 14, bold=True)
        
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
    game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    arcade.run()


if __name__ == "__main__":
    
    if not os.path.exists("context"):
        os.makedirs("context")
    
    if not os.path.exists("sounds"):
        os.makedirs("sounds")
        
    if not os.path.exists("images"):
        os.makedirs("images")
    if not os.path.exists("images/fond"):
        os.makedirs("images/fond")

    main()
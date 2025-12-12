# loup_garou_arcade.py

# -*- coding: utf-8 -*-
import arcade
import random
import time
from enum import Enum 
import math
import os
from dotenv import load_dotenv
load_dotenv() 

# Importation de vos classes de jeu
from game_core import GameManager, Player 
from enums_and_roles import Camp, NightAction 

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
            "DEFAULT": arcade.color.DARK_BLUE
        }
        
        base_action = self.text.split()[0]
        color = color_map.get(base_action, color_map.get(self.text.split('[')[0].strip(), color_map["DEFAULT"]))

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
        # CORRECTION de l'erreur de frappe: 'the' remplacé par 'self'
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

    def draw(self):
        color = arcade.color.WHITE if self.active else arcade.color.LIGHT_GRAY
        arcade.draw_lbwh_rectangle_filled(self.x, self.y, self.width, self.height, color)
        
        cursor = ("|" if self.active and int(time.time() * 2) % 2 == 0 else "")
        arcade.draw_text(self.text + cursor, 
                         self.x + 5, self.y + 5, 
                         arcade.color.BLACK, 14)
        
        if self.send_button:
            self.send_button.draw()

    def handle_key_press(self, symbol):
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


# --- Paramètres de la Fenêtre & États ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

class GameState(Enum):
    SETUP = 1 
    NIGHT_HUMAN_ACTION = 2 
    NIGHT_IA_ACTION = 3    
    DEBATE = 4
    HUMAN_ACTION = 5    
    VOTING = 6
    RESULT = 7
    GAME_OVER = 8


class LoupGarouGame(arcade.Window):
    
    def __init__(self, width, height, title, human_name="Humain_Lucie"):
        
        super().__init__(width, height, title)
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        # 1. Initialisation du Moteur de Jeu
        self.game_manager = GameManager(human_player_name=human_name)
        self.human_player = self.game_manager.human_player
        
        # 2. Variables d'Affichage et Log
        self.log_messages = [] 
        self.player_sprites = arcade.SpriteList()
        self.player_map = {} 
        self.action_buttons = []
        
        # 3. Gestion du Temps et Vitesse d'écriture (Débat)
        self.debate_timer = 60 
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 
        self.typing_delay = 5           
        self.messages_generated = 0           
        self.max_messages_per_debate = 10     
        self.message_is_complete = False 
        
        # 4. INITIALISATION DU CHAT INPUT (Déplacé à droite)
        
        PANEL_WIDTH = SCREEN_WIDTH // 3 
        INPUT_HEIGHT = 30
        
        input_x = SCREEN_WIDTH - PANEL_WIDTH - 10 
        input_y = 5 
        input_width = PANEL_WIDTH - 100 
        
        self.chat_input = ChatInput(input_x, input_y, input_width, INPUT_HEIGHT, self)
        
        self.chat_input.send_button = MenuButton(
            input_x + input_width + 50, 
            input_y + INPUT_HEIGHT / 2, 
            90, 
            INPUT_HEIGHT, 
            "Envoyer", 
            None
        )
        
        self.start_button = MenuButton(
            SCREEN_WIDTH / 2, 
            SCREEN_HEIGHT / 2, 
            300, 
            60, 
            "COMMENCER LA PARTIE", 
            "start_game"
        )
        
        # Initialisation des Sprites
        self._setup_sprites()
        
        # Commencer le jeu
        self.start_game_loop()

    
    def _setup_sprites(self):
        """
        Crée les représentations visuelles des joueurs en chargeant des images.
        Nécessite des images dans le dossier 'images/'.
        """
        
        IMAGE_DIR = "images"
        if not os.path.isdir(IMAGE_DIR):
            print(f"ATTENTION : Le dossier '{IMAGE_DIR}' n'existe pas. Utilisation de ronds par défaut.")
            return self._setup_circle_sprites() 


        num_players = len(self.game_manager.players)
        center_x = SCREEN_WIDTH / 2
        center_y = SCREEN_HEIGHT / 2
        angle_step = 360 / num_players
        
        available_images = [f for f in os.listdir(IMAGE_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
        random.shuffle(available_images)
        
        SPRITE_SCALE = 0.1
        
        for i, player in enumerate(self.game_manager.players):
            angle = i * angle_step
            rad_angle = math.radians(angle)
            x = center_x + 250 * math.cos(rad_angle)
            y = center_y + 250 * math.sin(rad_angle)
            
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
        center_x = SCREEN_WIDTH / 2
        center_y = SCREEN_HEIGHT / 2
        angle_step = 360 / num_players
        for i, player in enumerate(self.game_manager.players):
            angle = i * angle_step
            rad_angle = math.radians(angle)
            x = center_x + 250 * math.cos(rad_angle)
            y = center_y + 250 * math.sin(rad_angle)
            color = arcade.color.GREEN 
            sprite = arcade.SpriteCircle(50, color, center_x=x, center_y=y)
            self.player_sprites.append(sprite)
            self.player_map[player.name] = sprite

    def start_game_loop(self):
        """Initialise le jeu en état de SETUP, sans déclencher la nuit."""
        self.log_messages.append("--- Initialisation de la Partie ---")
        self.log_messages.append(f"Ton rôle est: {self.human_player.role.name}")
        
        if self.human_player.role and self.human_player.role.camp == Camp.LOUP:
            if self.human_player.wolf_teammates:
                teammates_str = ", ".join(self.human_player.wolf_teammates)
                self.log_messages.append(f"🐺 **TU ES LOUP-GAROU** ! Tes coéquipiers sont : {teammates_str}")
            else:
                 self.log_messages.append("🐺 **TU ES LOUP-GAROU** ! Tu es le seul loup de la partie.")
        
        self.current_state = GameState.SETUP 
        self.log_messages.append(f"\nCliquez sur 'COMMENCER LA PARTIE' pour lancer la Nuit 1.")

    def on_mouse_press(self, x, y, button, modifiers):
        """Gère le clic de la souris."""
        
        if self.current_state == GameState.SETUP:
            if self.start_button.check_click(x, y):
                if self.human_player.role.night_action in [NightAction.INVESTIGATE, NightAction.POTION]:
                    self.current_state = GameState.NIGHT_HUMAN_ACTION
                    self.log_messages.append(f"\nJOUR 1 : La NUIT tombe. Exécute ton action de {self.human_player.role.name}.")
                else:
                    self.current_state = GameState.NIGHT_IA_ACTION
                    self.log_messages.append(f"\nJOUR 1 : La NUIT tombe.")
                return 
                
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
        
        elif self.current_state == GameState.NIGHT_HUMAN_ACTION:
             self._handle_human_night_action_click(x, y)


    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (y compris la saisie du chat)."""
        
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.handle_key_press(symbol)
        
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
        
        human_is_wolf = (self.human_player.role and self.human_player.role.camp == Camp.LOUP)
        wolf_teammates = self.human_player.wolf_teammates
        
        # Dessiner les joueurs
        for player in self.game_manager.players:
             sprite = self.player_map.get(player.name)
             if sprite:
                 color = arcade.color.WHITE
                 
                 # --- GESTION DE LA MORT PAR TRANSPARENCE (ALPHA) ---
                 if not player.is_alive:
                     color = arcade.color.RED # Nom en rouge
                     sprite.alpha = 100 # Rendre le sprite semi-transparent (mort)
                 else:
                     sprite.alpha = 255 # Rendre le sprite opaque (vivant)
                     
                 # Mise en couleur des Loups alliés
                 if human_is_wolf and player.name in wolf_teammates:
                     color = arcade.color.YELLOW
                 
                 # Dessiner le nom et le statut
                 arcade.draw_text(
                     f"{player.name} ({'IA' if not player.is_human else 'H'})",
                     sprite.center_x, sprite.center_y + 60, color, 12, anchor_x="center"
                 )
                 
                 if self.current_state == GameState.GAME_OVER or player.is_human:
                     role_text = f"Role: {player.role.name}"
                     arcade.draw_text(role_text, sprite.center_x, sprite.center_y - 60, arcade.color.YELLOW_GREEN, 10, anchor_x="center")

        self.player_sprites.draw()
        
        # --- DESSINER LE CHAT LOCALISÉ ---
        self.draw_localized_chat_bubble()

        # AFFICHAGE DE LA LOGIQUE 
        self.draw_log()
        self.draw_status()
        
        
        # Dessiner les boutons d'Action/Vote
        for btn in self.action_buttons:
            btn.draw()
            
        # Afficher les boutons de nuit si nécessaire (et s'ils ne sont pas déjà affichés)
        if self.current_state == GameState.NIGHT_HUMAN_ACTION and not self.action_buttons:
            self._display_human_night_action_buttons()
        
        # Dessiner le champ de chat si en mode DEBATE (Input Humain)
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.draw()
            
        # AFFICHER LE BOUTON DE DÉMARRAGE si en SETUP
        if self.current_state == GameState.SETUP:
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
                
                # Largeur réduite et position ajustée pour éviter le chevauchement
                CHAT_WIDTH = 120 
                TEXT_X = sprite.center_x - CHAT_WIDTH / 2 + 5
                TEXT_Y = sprite.center_y - 90 
                
                # Le texte est dessiné directement sans fond de bulle
                arcade.draw_text(
                    f"{display_text}{cursor}", 
                    TEXT_X, 
                    TEXT_Y, 
                    arcade.color.LIGHT_YELLOW, # Couleur standard et visible
                    12, 
                    width=CHAT_WIDTH - 10,
                    multiline=True,
                    anchor_x="left",
                )
                
                # Indication visuelle de frappe
                if is_typing:
                    arcade.draw_text("...", sprite.center_x + 40, sprite.center_y + 40, arcade.color.AZURE, 18)


    def on_update(self, delta_time):
        """Logique : appelé à chaque image pour mettre à jour l'état."""
        
        if self.current_state in [GameState.SETUP, GameState.NIGHT_HUMAN_ACTION]:
            return

        if self.current_state == GameState.NIGHT_IA_ACTION:
             night_message = self.game_manager._night_phase() 
             self.log_messages.append(night_message)
             
             self.current_state = GameState.DEBATE
             self.debate_timer = 60 
             self.messages_generated = 0 
             self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")

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
                 self.log_messages.append(f"\nJOUR {self.game_manager.day + 1} : La NUIT tombe.") 
                 if self.human_player.is_alive and self.human_player.role.night_action in [NightAction.INVESTIGATE, NightAction.POTION]:
                     self.current_state = GameState.NIGHT_HUMAN_ACTION
                 else:
                     self.current_state = GameState.NIGHT_IA_ACTION

    
    # --- LOGIQUE D'ACTION HUMAINE DE NUIT ---

    def _display_human_night_action_buttons(self):
        """Prépare les boutons d'action de nuit pour la Voyante/Sorcière humaine."""
        
        self.action_buttons = []
        alive = self.game_manager.get_alive_players()
        role_name = self.human_player.role.name
        
        button_y = 50 
        button_width = 150
        button_height = 40
        
        targets = [p for p in alive if p != self.human_player]
        targets_msg = ""

        if role_name == "Voyante":
            action = "ENQUÊTER"
            targets_msg = "Choisis qui enquêter (Voyante) :"
            
            start_x = SCREEN_WIDTH / 2 - (len(targets) * (button_width + 10) / 2) + 50
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
            
            x_start = SCREEN_WIDTH / 2 - 150
            if self.human_player.has_kill_potion:
                 self.action_buttons.append(MenuButton(x_start, button_y, 140, button_height, "TUER [Potion Mort]", "TUER"))
                 x_start += 150
            if self.human_player.has_life_potion:
                 self.action_buttons.append(MenuButton(x_start, button_y, 140, button_height, "SAUVER [Potion Vie]", "SAUVER"))
                 x_start += 150
                 
            self.action_buttons.append(MenuButton(x_start, button_y, 100, button_height, "PASSER", "PASSER"))
            
            self.log_messages.append(f"-> {targets_msg}")
            return
            
        else:
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
        
        if self.human_player.role.name == "Voyante" and ":" in clicked_action_data:
            action_type, target_name = clicked_action_data.split(":", 1)
            target = next((p for p in self.game_manager.players if p.name == target_name), None)
            
            if action_type == "ENQUÊTER" and target:
                target_role = target.role.name
                target_camp = target.role.camp.value
                self.log_messages.append(f"🕵️‍♀️ Révélation : {target.name} est un(e) **{target_role}** ({target_camp}).")
                self.current_state = GameState.NIGHT_IA_ACTION
                return
                
        elif self.human_player.role.name == "Sorcière" and clicked_action_data in ["TUER", "SAUVER", "PASSER"]:
            
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
        
        CENTER_X = SCREEN_WIDTH / 2 
        start_x = CENTER_X - (len(voting_targets) * (button_width + 10) / 2)
        
        for i, target in enumerate(voting_targets):
            x = start_x + (i * (button_width + 10))
            btn = MenuButton(
                x, button_y, button_width, button_height, 
                f"Voter {target.name}", target.name 
            )
            self.action_buttons.append(btn)
            
        self.log_messages.append(f"-> {self.human_player.name}, choisis ta victime (CLIC) :")


    # --- MÉTHODES D'AFFICHAGE (SANS UNDERSCORE) ---
    
    def draw_log(self):
        """Dessine le Journal de Bord (Historique Permanent) à GAUCHE."""
        LOG_X_START = 10
        LOG_WIDTH = SCREEN_WIDTH // 3 
        LOG_HEIGHT = SCREEN_HEIGHT - 40 
        
        arcade.draw_lbwh_rectangle_filled(
            LOG_X_START, 
            10, # Bottom Y position
            LOG_WIDTH, 
            LOG_HEIGHT, 
            (20, 20, 20, 180) 
        )
        
        x_pos = LOG_X_START + 10
        y_pos = SCREEN_HEIGHT - 30 
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
                width=LOG_WIDTH - 20,
                multiline=True
            )
            y_pos -= line_spacing 
            
    def draw_status(self):
        """Dessine les compteurs (Loups, Timer) à DROITE, en haut."""
        
        PANEL_WIDTH = SCREEN_WIDTH // 3
        RIGHT_PANEL_START_X = SCREEN_WIDTH - PANEL_WIDTH
        
        arcade.draw_text(
            f"Loups Vivants : {self.game_manager.wolves_alive}",
            RIGHT_PANEL_START_X + 20, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16
        )
        
        if self.current_state in [GameState.DEBATE, GameState.VOTING, GameState.HUMAN_ACTION]:
             arcade.draw_text(
                f"Temps Restant : {int(self.debate_timer)}s",
                RIGHT_PANEL_START_X + 20, SCREEN_HEIGHT - 60, arcade.color.YELLOW, 14
            )
        
        if self.current_state == GameState.NIGHT_HUMAN_ACTION:
             arcade.draw_text(
                f"ACTION NOCTURNE REQUISE ({self.human_player.role.name})",
                RIGHT_PANEL_START_X + 20, SCREEN_HEIGHT - 200, arcade.color.ORANGE, 16
            )

# --- Lancement du Jeu ---

def main():
    """Fonction principale pour lancer l'application Arcade."""
    game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    arcade.run()


if __name__ == "__main__":
    
    if not os.path.exists("context"):
        os.makedirs("context")
        for i in range(1, 10):
            with open(f"context/perso_placeholder_{i}.txt", "w", encoding="utf-8") as f:
                f.write(f"Tu es l'IA {i}. Ton rôle est d'être un joueur de Loup Garou. Réponds de manière concise.")

    main()
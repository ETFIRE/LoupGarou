# loup_garou_arcade.py

# -*- coding: utf-8 -*-
import arcade
import random
import time
from enum import Enum 
import math

# IMPORTATION ET CHARGEMENT FORCÉ DE L'ENVIRONNEMENT
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
        arcade.draw_lbwh_rectangle_filled(
            self.center_x - self.width / 2, 
            self.center_y - self.height / 2, 
            self.width, 
            self.height, 
            arcade.color.RED_DEVIL if self.text.startswith("Voter") else arcade.color.DARK_GREEN
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

    def draw(self):
        # Dessiner le fond du champ de saisie
        color = arcade.color.WHITE if self.active else arcade.color.LIGHT_GRAY
        arcade.draw_lbwh_rectangle_filled(self.x, self.y, self.width, self.height, color)
        
        # Dessiner le texte saisi avec curseur
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
            
            # 1. Ajouter au log public
            self.game.log_messages.append(f"🗣️ {self.game.human_player.name} : {message}")
            
            # 2. ENVOYER LE MESSAGE AUX IA (stockage de l'historique)
            alive_ais = [p for p in self.game.game_manager.get_alive_players() if not p.is_human]
            for listener in alive_ais:
                listener.receive_public_message(self.game.human_player.name, message)
            
            # 3. Réinitialiser et maintenir l'activation
            self.text = ""
            self.game.current_speaker = None 
            
    def check_click(self, x, y):
        # Activation/Désactivation du champ de saisie
        is_in_input = (self.x < x < self.x + self.width and self.y < y < self.y + self.height)
        
        # Gérer le clic sur le bouton Envoyer
        if self.send_button and self.send_button.check_click(x, y):
             self.send_message()
        else:
            # Sinon, on active si on est sur la zone, on désactive sinon
            self.active = is_in_input


# --- Paramètres de la Fenêtre & États ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

class GameState(Enum):
    SETUP = 1
    NIGHT_IA_ACTION = 2 
    HUMAN_ACTION = 3    
    DEBATE = 4
    VOTING = 5
    RESULT = 6
    GAME_OVER = 7


class LoupGarouGame(arcade.Window):
    
    def __init__(self, width, height, title, human_name="Humain_Lucie"):
        
        super().__init__(width, height, title)
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        # 1. Initialisation du Moteur de Jeu
        self.game_manager = GameManager(human_player_name=human_name)
        # L'instance du joueur humain est maintenant disponible via GameManager
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
        self.typing_delay = 1 
        self.messages_generated = 0           
        self.max_messages_per_debate = 10     
        
        # 4. INITIALISATION DU CHAT INPUT 
        input_x = 20
        input_y = 5 
        input_width = SCREEN_WIDTH - 220 
        input_height = 30
        self.chat_input = ChatInput(input_x, input_y, input_width, input_height, self)
        
        # Assignation du bouton Envoyer à ChatInput
        self.chat_input.send_button = MenuButton(
            input_x + input_width + 60, input_y + input_height / 2, 100, input_height, "Envoyer", None
        )
        
        # Initialisation des Sprites
        self._setup_sprites()
        
        # Commencer le jeu
        self.start_game_loop()

    
    def _setup_sprites(self):
        """Crée les représentations visuelles des joueurs."""
        num_players = len(self.game_manager.players)
        center_x = SCREEN_WIDTH / 2
        center_y = SCREEN_HEIGHT / 2
        angle_step = 360 / num_players
        for i, player in enumerate(self.game_manager.players):
            angle = i * angle_step
            rad_angle = math.radians(angle)
            x = center_x + 250 * math.cos(rad_angle)
            y = center_y + 250 * math.sin(rad_angle)
            color = arcade.color.GREEN if player.is_alive else arcade.color.RED_BROWN
            sprite = arcade.SpriteCircle(50, color, center_x=x, center_y=y)
            self.player_sprites.append(sprite)
            self.player_map[player.name] = sprite

    def start_game_loop(self):
        """Commence la première phase du jeu."""
        self.log_messages.append("--- Initialisation de la Partie ---")
        self.log_messages.append(f"Ton rôle est: {self.human_player.role.name}")
        
        # --- NOUVEAU: INFORMER LE LOUP HUMAIN DE SES COÉQUIPIERS ---
        if self.human_player.role.camp == Camp.LOUP:
            if self.human_player.wolf_teammates:
                teammates_str = ", ".join(self.human_player.wolf_teammates)
                self.log_messages.append(f"🐺 **TU ES LOUP-GAROU** ! Tes coéquipiers sont : {teammates_str}")
            else:
                 self.log_messages.append("🐺 **TU ES LOUP-GAROU** ! Tu es le seul loup de la partie.")
        # --- FIN NOUVEAU ---
        
        self.current_state = GameState.NIGHT_IA_ACTION
        self.log_messages.append(f"JOUR 1 : La NUIT tombe.")

    def on_mouse_press(self, x, y, button, modifiers):
        """Gère le clic de la souris."""
        if self.current_state == GameState.HUMAN_ACTION:
            for btn in self.action_buttons:
                if btn.check_click(x, y):
                    voted_player_name = btn.action
                    self.log_messages.append(f"🗳️ {self.human_player.name} vote pour {voted_player_name}")
                    self.game_manager.register_human_vote(voted_player_name)
                    self.action_buttons = [] 
                    self.current_state = GameState.VOTING
                    break
                    
        elif self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.check_click(x, y)


    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (y compris la saisie du chat)."""
        
        # 1. Gérer la saisie si on est en mode DEBATE
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.handle_key_press(symbol)
        
        # 2. Gérer le SKIP
        elif symbol == arcade.key.SPACE:
            if self.current_state == GameState.DEBATE:
                self.debate_timer = 0 
                if self.current_speaker:
                    self.current_message_display = self.current_message_full
                    self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                self.current_speaker = None
                self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")


    def on_draw(self):
        """Affichage : appelé à chaque image pour dessiner."""
        self.clear()
        
        # Dessiner les joueurs et leurs noms
        for player in self.game_manager.players:
             sprite = self.player_map.get(player.name)
             if sprite:
                 color = arcade.color.WHITE
                 if not player.is_alive:
                     color = arcade.color.RED
                     sprite.color = arcade.color.DARK_RED 
                 else:
                     sprite.color = arcade.color.GREEN 
                 arcade.draw_text(
                     f"{player.name} ({'IA' if not player.is_human else 'H'})",
                     sprite.center_x, sprite.center_y + 60, color, 12, anchor_x="center"
                 )
                 if self.current_state == GameState.GAME_OVER or player.is_human:
                     role_text = f"Role: {player.role.name}"
                     arcade.draw_text(role_text, sprite.center_x, sprite.center_y - 60, arcade.color.YELLOW_GREEN, 10, anchor_x="center")

        self.player_sprites.draw()
        self.draw_log()
        self.draw_status()
        
        
        # Dessiner les boutons de vote
        for btn in self.action_buttons:
            btn.draw()
        
        # Dessiner le champ de chat si en mode DEBATE
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.draw()


    def on_update(self, delta_time):
        """Logique : appelé à chaque image pour mettre à jour l'état."""
        
        # 1. EXÉCUTION DE LA LOGIQUE DE NUIT
        if self.current_state == GameState.NIGHT_IA_ACTION:
             night_message = self.game_manager._night_phase() 
             self.log_messages.append(night_message)
             
             self.current_state = GameState.DEBATE
             self.debate_timer = 60 
             self.messages_generated = 0 
             self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")

        # 2. GESTION DU DÉBAT
        elif self.current_state == GameState.DEBATE:
            self._update_debate(delta_time) 
        
        # 3. GESTION DU VOTE
        elif self.current_state == GameState.VOTING:
            # L'appel à _lynch_result se fait ici
            lynch_message = self.game_manager._lynch_result(self.game_manager.get_alive_players()) 
            self.log_messages.append(lynch_message)
            self.current_state = GameState.RESULT
        
        # 4. GESTION DU RÉSULTAT ET TRANSITION
        elif self.current_state == GameState.RESULT:
            winner = self.game_manager.check_win_condition()
            if winner:
                 self.log_messages.append(f"\n🎉 VICTOIRE des {winner.value} ! Fin de la partie.")
                 self.current_state = GameState.GAME_OVER
            else:
                 self.current_state = GameState.NIGHT_IA_ACTION
                 self.log_messages.append(f"\nJOUR {self.game_manager.day} : La NUIT tombe.")

    
    # --- MÉTHODES DE LOGIQUE DE JEU INTERNE (UTILISENT UNDERSCORE) ---
    
    def _update_debate(self, delta_time):
        """Gère le temps et la parole pendant la phase de débat."""
        
        self.debate_timer -= delta_time
        
        # --- GESTION DE LA VITESSE D'ÉCRITURE ---
        if self.current_message_display != self.current_message_full:
            self.typing_speed_counter += 1
            if self.typing_speed_counter >= self.typing_delay:
                current_len = len(self.current_message_display)
                if current_len < len(self.current_message_full):
                    self.current_message_display += self.current_message_full[current_len]
                else:
                    # AJOUT AU LOG À LA FIN DE LA FRAPPE
                    self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                    self.current_speaker = None 
                self.typing_speed_counter = 0

        # --- TRANSITION VERS LA PHASE DE VOTE ---
        if (self.debate_timer <= 0 or self.messages_generated >= self.max_messages_per_debate) and self.current_state == GameState.DEBATE:
            
            # S'assurer que le dernier message est loggé même si on sort du timer
            if self.current_speaker is not None:
                 self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                 self.current_speaker = None

            self.log_messages.append("\n🗳️ FIN DU DÉBAT. PLACE AU VOTE.")
            self.messages_generated = 0 
            
            if self.human_player.is_alive:
                self.enter_human_voting_state() 
                self.current_state = GameState.HUMAN_ACTION
            else:
                self.current_state = GameState.VOTING
                
        # --- LOGIQUE DE PRISE DE PAROLE (IA) ---
        elif self.current_speaker is None and self.current_state == GameState.DEBATE and self.messages_generated < self.max_messages_per_debate: 
            
            alive_ais = [p for p in self.game_manager.get_alive_players() if not p.is_human]
            if alive_ais:
                speaker = random.choice(alive_ais)
                
                # NOTE: Utilisation correcte de _get_public_status() de GameManager
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
        
        start_x = SCREEN_WIDTH / 2 - (len(voting_targets) * (button_width + 10) / 2) + 50
        
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
        # --- LOGIQUE DE DESSIN DU LOG AMÉLIORÉE (CORRECTIF FINAL VISUEL) ---
        LOG_X_START = 10
        LOG_WIDTH = SCREEN_WIDTH // 3 
        LOG_HEIGHT = SCREEN_HEIGHT - 40 
        
        # 1. Dessiner le fond sombre (semi-transparent)
        arcade.draw_lbwh_rectangle_filled(
            LOG_X_START, 
            10, # Bottom Y position
            LOG_WIDTH, 
            LOG_HEIGHT, 
            (20, 20, 20, 180) 
        )
        
        # 2. Paramètres de police robustes
        x_pos = LOG_X_START + 10
        y_pos = SCREEN_HEIGHT - 30 
        line_spacing = 30 # ESPACEMENT SÛR 
        font_size = 14 
        
        # Titre
        arcade.draw_text("JOURNAL DE BORD:", x_pos, y_pos, arcade.color.ORANGE_RED, 14)
        y_pos -= 30 # Drop après le titre
        
        # 3. Afficher le message en cours de frappe (Si actif)
        if self.current_speaker is not None:
            cursor = ("|" if int(time.time() * 2) % 2 == 0 else "")
            
            arcade.draw_text(
                f"💬 {self.current_speaker.name}: {self.current_message_display}{cursor}", 
                x_pos, 
                y_pos, 
                arcade.color.AZURE, # Bleu pour la frappe
                font_size, 
                width=LOG_WIDTH - 20,
                multiline=True
            )
            y_pos -= line_spacing # Décale l'historique d'une ligne
        
        # 4. Afficher l'historique permanent (du plus récent au plus ancien, de haut en bas)
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
        arcade.draw_text(
            f"Loups Vivants : {self.game_manager.wolves_alive}",
            SCREEN_WIDTH - 200, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16
        )
        if self.current_state in [GameState.DEBATE, GameState.VOTING, GameState.HUMAN_ACTION]:
             arcade.draw_text(
                f"Temps Restant : {int(self.debate_timer)}s",
                SCREEN_WIDTH - 200, SCREEN_HEIGHT - 60, arcade.color.YELLOW, 14
            )


# --- Lancement du Jeu ---

def main():
    """Fonction principale pour lancer l'application Arcade."""
    game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    arcade.run()


if __name__ == "__main__":
    import os
    if not os.path.exists("context"):
        os.makedirs("context")
        for i in range(1, 10):
            with open(f"context/perso_{i}.txt", "w", encoding="utf-8") as f:
                f.write(f"Tu es l'IA {i}. Ton rôle est d'être un joueur de Loup Garou. Réponds de manière concise.")

    main()
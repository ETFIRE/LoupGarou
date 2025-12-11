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
        self.action = action # Le nom du joueur ciblé

    def draw(self):
        # Utilisation de draw_lbwh_rectangle_filled pour la compatibilité
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


# --- Paramètres de la Fenêtre ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

# --- États du Jeu ---
class GameState(Enum):
    SETUP = 1
    NIGHT_IA_ACTION = 2 
    HUMAN_ACTION = 3    # NOUVEL ÉTAT : Attente de l'input humain (Vote)
    DEBATE = 4
    VOTING = 5          # Déclenche la collecte des votes IA (après l'humain)
    RESULT = 6
    GAME_OVER = 7


class LoupGarouGame(arcade.Window):
    
    def __init__(self, width, height, title, human_name="Humain_Lucie"):
        
        super().__init__(width, height, title)
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        # 1. Initialisation du Moteur de Jeu
        self.game_manager = GameManager(human_player_name=human_name)
        self.human_player = next((p for p in self.game_manager.players if p.is_human), None)
        
        # 2. Variables d'Affichage et Log
        self.log_messages = [] 
        self.player_sprites = arcade.SpriteList()
        self.player_map = {} 
        self.action_buttons = [] # Pour stocker les boutons de vote/action
        
        # 3. Gestion du Temps et Vitesse d'écriture (Débat)
        self.debate_timer = GameManager.DEBATE_TIME_LIMIT
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 
        self.typing_delay = 3 

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
        self.current_state = GameState.NIGHT_IA_ACTION
        self.log_messages.append(f"JOUR 1 : La NUIT tombe.")

    def on_mouse_press(self, x, y, button, modifiers):
        """Gère le clic de la souris, principalement pour le vote humain."""
        if self.current_state == GameState.HUMAN_ACTION:
            for btn in self.action_buttons:
                if btn.check_click(x, y):
                    # Le joueur humain a voté!
                    voted_player_name = btn.action
                    self.log_messages.append(f"🗳️ {self.human_player.name} vote pour {voted_player_name}")
                    
                    # Enregistrer le vote dans le GameManager et collecter les votes IA
                    self.game_manager.register_human_vote(voted_player_name)
                    
                    # Passer à l'état de résolution du lynchage
                    self.action_buttons = [] 
                    self.current_state = GameState.VOTING # VOTING déclenchera le lynchage dans on_update
                    break

    def on_draw(self):
        """Affichage : appelé à chaque image pour dessiner."""
        self.clear()
        
        # Mettre à jour la couleur des sprites (vivant/mort)
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
        self._draw_log()
        self._draw_status()
        self._draw_typing_message()
        
        # Dessiner les boutons d'action (actifs seulement en mode HUMAN_ACTION)
        for btn in self.action_buttons:
            btn.draw()

    def on_update(self, delta_time):
        """Logique : appelé à chaque image pour mettre à jour l'état."""
        
        # 1. EXÉCUTION DE LA LOGIQUE DE NUIT
        if self.current_state == GameState.NIGHT_IA_ACTION:
             night_message = self.game_manager._night_phase()
             self.log_messages.append(night_message)
             
             self.current_state = GameState.DEBATE
             self.debate_timer = GameManager.DEBATE_TIME_LIMIT 
             self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")

        # 2. GESTION DU DÉBAT
        elif self.current_state == GameState.DEBATE:
            self._update_debate(delta_time)
        
        # 3. GESTION DU VOTE (Déclenché par le clic humain OU par la fin du débat si l'humain est mort)
        elif self.current_state == GameState.VOTING:
            
            # Résoudre le lynchage et obtenir le message du résultat
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
                 # Nouvelle nuit
                 self.current_state = GameState.NIGHT_IA_ACTION
                 self.log_messages.append(f"\nJOUR {self.game_manager.day} : La NUIT tombe.")


    # --- LOGIQUE DE DÉBAT, DESSIN, ETC. ---
    
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
                    self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                    self.current_speaker = None
                self.typing_speed_counter = 0

        # --- TRANSITION VERS LA PHASE DE VOTE (Déclenché par le temps) ---
        if self.debate_timer <= 0 and self.current_state == GameState.DEBATE:
            
            if self.current_speaker is not None:
                 self.log_messages.append(f"🗣️ {self.current_speaker.name}: {self.current_message_full}")
                 self.current_speaker = None

            self.log_messages.append("\n🗳️ FIN DU DÉBAT. PLACE AU VOTE.")
            
            if self.human_player.is_alive:
                self._enter_human_voting_state() 
                self.current_state = GameState.HUMAN_ACTION # ARRET : Attendre le clic
            else:
                self.current_state = GameState.VOTING # Vote IA automatique
                
        # --- LOGIQUE DE PRISE DE PAROLE (IA) ---
        elif self.current_speaker is None and self.current_state == GameState.DEBATE: 
            
            alive_ais = [p for p in self.game_manager.get_alive_players() if not p.is_human]
            if alive_ais:
                speaker = random.choice(alive_ais)
                
                debate_message = speaker.generate_debate_message(self.game_manager._get_public_status())
                
                self.current_speaker = speaker
                self.current_message_full = debate_message
                self.current_message_display = ""
                
                for listener in [p for p in alive_ais if p != speaker]:
                    listener.receive_public_message(speaker.name, debate_message)

    def _enter_human_voting_state(self):
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


    def _draw_log(self):
        y_pos = SCREEN_HEIGHT - 30
        arcade.draw_text("JOURNAL DE BORD:", 20, y_pos, arcade.color.ORANGE_RED, 14)
        y_pos -= 20
        for msg in self.log_messages[-15:]:
            arcade.draw_text(msg, 20, y_pos, arcade.color.LIGHT_GRAY, 10)
            y_pos -= 15
            
    def _draw_status(self):
        arcade.draw_text(
            f"Loups Vivants : {self.game_manager.wolves_alive}",
            SCREEN_WIDTH - 200, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16
        )
        if self.current_state in [GameState.DEBATE, GameState.VOTING, GameState.HUMAN_ACTION]:
             arcade.draw_text(
                f"Temps Restant : {int(self.debate_timer)}s",
                SCREEN_WIDTH - 200, SCREEN_HEIGHT - 60, arcade.color.YELLOW, 14
            )

    def _draw_typing_message(self):
        if self.current_speaker and self.current_message_display != self.current_message_full:
            arcade.draw_text(
                f"💬 {self.current_speaker.name} tape...",
                SCREEN_WIDTH / 2, 50, arcade.color.AZURE, 16, anchor_x="center"
            )
            arcade.draw_text(
                self.current_message_display,
                SCREEN_WIDTH / 2, 30, arcade.color.LIGHT_GRAY, 12, anchor_x="center"
            )


    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (ex: pour skipper le débat)."""
        
        if symbol == arcade.key.SPACE:
            if self.current_state == GameState.DEBATE:
                self.debate_timer = 0 
                self.current_message_full = self.current_message_display 
                self.current_speaker = None
                self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")


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
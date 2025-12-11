# loup_garou_arcade.py (FINAL)

# -*- coding: utf-8 -*-
"""
Interface graphique principale du jeu Loup Garou IA
Utilise Arcade pour l'affichage et l'interaction
"""
import arcade
import random
import time
from enum import Enum 
import math
from typing import Optional, List
import os

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
        self.send_button = None # Doit être assigné après l'init du jeu

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
            
            # CORRECTION ICI : Remplacement de arcade.key.is_printable
            else:
                # Tente de convertir le symbole en caractère et vérifie si c'est un caractère imprimable
                try:
                    char = chr(symbol)
                    if char.isprintable(): # isprintable() est une méthode string standard de Python
                        # Limiter la longueur du message
                        if len(self.text) < 80: 
                            self.text += char
                except ValueError:
                    # Si le symbole ne correspond pas à un caractère, on l'ignore (c'est une touche de contrôle)
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
            
            # 3. Réinitialiser et libérer la parole
            self.text = ""
            self.active = False
            self.game.current_speaker = None 
            
    def check_click(self, x, y):
        # Activation/Désactivation du champ de saisie
        is_in_input = (self.x < x < self.x + self.width and self.y < y < self.y + self.height)
        self.active = is_in_input
        
        # Gérer le clic sur le bouton Envoyer
        if self.send_button and self.send_button.check_click(x, y):
            self.send_message()


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

class PlayerSprite(arcade.SpriteCircle):
    """Sprite représentant un joueur dans le cercle de discussion"""
    
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
        self.action_buttons = []
        
        # 3. Gestion du Temps et Vitesse d'écriture (Débat)
        self.debate_timer = GameManager.DEBATE_TIME_LIMIT
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 
        self.typing_delay = 3 

        # 4. INITIALISATION DU CHAT INPUT (CORRECTION)
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

    # ... (les méthodes _setup_sprites et start_game_loop restent les mêmes) ...
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
                    
        # GESTION DU CLIC SUR LE CHAMP DE CHAT EN MODE DÉBAT
        elif self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.check_click(x, y)


    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (y compris la saisie du chat)."""
        
        # Gérer la saisie si on est en mode DEBATE
        if self.current_state == GameState.DEBATE and self.human_player.is_alive:
            self.chat_input.handle_key_press(symbol)
        
        # Gérer le SKIP (Reste comme avant)
        elif symbol == arcade.key.SPACE:
            if self.current_state == GameState.DEBATE:
                self.debate_timer = 0 
                self.current_message_full = self.current_message_display 
                self.current_speaker = None
                self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")


    def on_draw(self):
        """Affichage : appelé à chaque image pour dessiner."""
        self.clear()
        
        # Dessiner les joueurs et leurs noms (Logique omise pour concision, mais fonctionne)
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
             self.debate_timer = GameManager.DEBATE_TIME_LIMIT 
             self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")

        # 2. GESTION DU DÉBAT
        elif self.current_state == GameState.DEBATE:
            self._update_debate(delta_time)
        
        # 3. GESTION DU VOTE (Déclenché par le clic humain OU si l'humain est mort)
        elif self.current_state == GameState.VOTING:
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
            self.player.name,
            self.center_x, self.center_y + 60,
            color, 14,
            anchor_x="center", anchor_y="center",
            bold=self.player.is_human
        )
        if self.current_state in [GameState.DEBATE, GameState.VOTING, GameState.HUMAN_ACTION]:
             arcade.draw_text(
                f"Temps Restant : {int(self.debate_timer)}s",
                SCREEN_WIDTH - 200, SCREEN_HEIGHT - 60, arcade.color.YELLOW, 14
            )

class DialogueMessage:
    """Représente un message dans le chat"""
    
    def __init__(self, speaker: str, message: str, timestamp: float = None):
        self.speaker = speaker
        self.message = message
        self.timestamp = timestamp or time.time()
        self.display_time = 30  # Secondes d'affichage
        self.alpha = 255
    
    def update(self, delta_time: float):
        """Gère le fondu des anciens messages"""
        age = time.time() - self.timestamp
        if age > self.display_time - 5:
            self.alpha = max(0, int(255 * (1 - (age - (self.display_time - 5)) / 5)))
    
    def is_expired(self) -> bool:
        """Vérifie si le message a expiré"""
        return time.time() - self.timestamp > self.display_time

class UIButton:
    """Bouton d'interface utilisateur"""
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str, 
                 action=None, enabled=True):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.action = action
        self.enabled = enabled
        self.is_hovered = False
    
    def contains_point(self, x: float, y: float) -> bool:
        """Vérifie si un point est dans le bouton"""
        return (self.x - self.width/2 <= x <= self.x + self.width/2 and
                self.y - self.height/2 <= y <= self.y + self.height/2)
    
    def draw(self):
        """Dessine le bouton"""
        # Couleur du bouton
        if not self.enabled:
            color = (100, 100, 100)
            border_color = (80, 80, 80)
        elif self.is_hovered:
            color = COLOR_BUTTON_HOVER
            border_color = (80, 180, 255)
        else:
            color = COLOR_BUTTON
            border_color = (30, 100, 160)
        
        # Rectangle du bouton
        arcade.draw_rectangle_filled(
            self.x, self.y, self.width, self.height, color
        )
        arcade.draw_rectangle_outline(
            self.x, self.y, self.width, self.height, border_color, 2
        )
        
        # Texte du bouton
        text_color = COLOR_TEXT if self.enabled else (150, 150, 150)
        arcade.draw_text(
            self.text,
            self.x, self.y,
            text_color, 16,
            anchor_x="center", anchor_y="center",
            bold=True
        )
    
    def on_click(self):
        """Exécute l'action du bouton"""
        if self.enabled and self.action:
            self.action()

# ============================================================================
# FENÊTRE PRINCIPALE
# ============================================================================

class LoupGarouGame(arcade.Window):
    """Fenêtre principale du jeu Loup Garou"""
    
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(COLOR_BACKGROUND)
        
        # Initialisation du jeu
        self.game = GameManager()
        self.human_player = self.game.get_human_player()
        
        # États
        self.current_phase = GamePhase.NUIT
        self.selected_player: Optional[PlayerSprite] = None
        
        # Interface
        self.player_sprites: List[PlayerSprite] = []
        self.player_sprites_list = arcade.SpriteList()  # SpriteList pour le rendu
        self.dialogue_messages: List[DialogueMessage] = []
        self.game_log: List[str] = []
        self.typing_message = ""
        self.is_typing = False
        self.cursor_visible = True
        self.cursor_timer = 0
        
        # Boutons
        self.vote_button: Optional[UIButton] = None
        self.send_button: Optional[UIButton] = None
        self.skip_button: Optional[UIButton] = None
        
        # Timers
        self.phase_timer = 0
        self.phase_durations = {
            GamePhase.NUIT: 30,
            GamePhase.DEBAT: 120,
            GamePhase.VOTE: 60,
            GamePhase.RESULTAT: 10
        }
        
        # Animation
        self.current_speaker: Optional[PlayerSprite] = None
        self.displayed_message = ""
        self.full_message = ""
        self.char_index = 0
        self.type_speed = 0.05  # Secondes par caractère
        self.type_timer = 0
        
        # Initialisation
        self._setup_sprites()
        self._setup_ui()
        self._start_game()
        
    # ============================================================================
    # INITIALISATION
    # ============================================================================
    
    def _setup_sprites(self):
        """Crée les sprites des joueurs en cercle"""
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        circle_radius = 280
        num_players = len(self.game.players)
        
        for i, player in enumerate(self.game.players):
            # Calcul de la position en cercle
            angle = (2 * math.pi * i) / num_players - math.pi/2
            x = center_x + circle_radius * math.cos(angle)
            y = center_y + circle_radius * math.sin(angle)
            
            # Création du sprite
            sprite = PlayerSprite(player)
            sprite.center_x = x
            sprite.center_y = y
            
            # Ajouter aux deux listes
            self.player_sprites.append(sprite)
            self.player_sprites_list.append(sprite)
    
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Bouton de vote
        self.vote_button = UIButton(
            SCREEN_WIDTH - 150, 180, 200, 50, "🗳️ VOTER",
            action=self._cast_vote,
            enabled=False
        )
        
        # Bouton d'envoi de message
        self.send_button = UIButton(
            SCREEN_WIDTH - 150, 120, 200, 50, "💬 PARLER",
            action=self._start_typing,
            enabled=True
        )
        
        # Bouton de skip
        self.skip_button = UIButton(
            SCREEN_WIDTH - 150, 60, 200, 50, "⏩ PASSER",
            action=self._skip_phase,
            enabled=True
        )
    
    def _start_game(self):
        """Démarre la partie"""
        self._add_log("=== DÉBUT DE LA PARTIE ===")
        self._add_log(f"Bienvenue {self.human_player.name}!")
        self._add_log(f"Votre rôle: {self.human_player.role.name}")
        self._add_log(f"Camp: {self.human_player.role.camp.value}")
        
        self._add_dialogue("Maître du jeu", "La nuit tombe sur le village...")
        self._start_night_phase()
    
    # ============================================================================
    # GESTION DES PHASES
    # ============================================================================
    
    def _start_night_phase(self):
        """Démarre la phase de nuit"""
        self.current_phase = GamePhase.NUIT
        self.phase_timer = self.phase_durations[GamePhase.NUIT]
        self.game.day += 1
        
        self._add_log(f"\n🌙 NUIT {self.game.day}")
        self._add_dialogue("Système", f"La nuit {self.game.day} commence...")
        
        # Exécuter les actions de nuit
        self.game.night_phase()
        
        # Mettre à jour les sprites
        for sprite in self.player_sprites:
            # Trouver le joueur correspondant
            for player in self.game.players:
                if player.name == sprite.player.name:
                    sprite.player = player
                    # Mettre à jour la couleur si le joueur est mort
                    if not player.is_alive:
                        sprite.color = COLOR_PLAYER_DEAD
                    break
    
    def _start_debate_phase(self):
        """Démarre la phase de débat"""
        self.current_phase = GamePhase.DEBAT
        self.phase_timer = self.phase_durations[GamePhase.DEBAT]
        
        self._add_log("\n💬 DÉBAT DU JOUR")
        self._add_dialogue("Système", "Le jour se lève! La discussion commence.")
        
        # Activer le bouton de discussion
        if self.send_button:
            self.send_button.enabled = True
        
        # Lancer un premier message IA
        self._schedule_ai_message()
    
    def _start_voting_phase(self):
        """Démarre la phase de vote"""
        self.current_phase = GamePhase.VOTE
        self.phase_timer = self.phase_durations[GamePhase.VOTE]
        
        self._add_log("\n🗳️ PHASE DE VOTE")
        self._add_dialogue("Système", "Le débat est terminé. Place au vote!")
        
        # Activer le bouton de vote
        if self.vote_button:
            self.vote_button.enabled = True
        
        # Désélectionner tout joueur
        self._deselect_all()
    
    def _show_voting_result(self):
        """Affiche le résultat du vote"""
        self.current_phase = GamePhase.RESULTAT
        self.phase_timer = self.phase_durations[GamePhase.RESULTAT]
        
        # Exécuter le lynchage
        eliminated = self.game.execute_lynching()
        
        if eliminated:
            self._add_log(f"🔥 {eliminated.name} a été lynché!")
            self._add_dialogue("Système", 
                f"{eliminated.name} ({eliminated.role.name}) a été lynché par le village!")
            
            # Mettre à jour le sprite
            for sprite in self.player_sprites:
                if sprite.player.name == eliminated.name:
                    sprite.player = eliminated
                    sprite.color = COLOR_PLAYER_DEAD
        
        # Vérifier la victoire
        winner = self.game.check_win_condition()
        if winner:
            self._end_game(winner)
            return
        
        # Passer à la nuit suivante
        arcade.schedule(self._start_night_phase, 3)
    
    def _end_game(self, winner: Camp):
        """Termine la partie"""
        self.current_phase = GamePhase.FIN
        
        self._add_log(f"\n🎉 VICTOIRE DES {winner.value.upper()}!")
        self._add_dialogue("Système", 
            f"La partie est terminée! Victoire des {winner.value}!")
        
        # Afficher tous les rôles
        self._add_log("\n📜 RÔLES DES JOUEURS:")
        for player in self.game.players:
            self._add_log(f"  {player.name}: {player.role.name} ({player.role.camp.value})")
    
    def _skip_phase(self):
        """Passe à la phase suivante"""
        if self.current_phase == GamePhase.NUIT:
            self._start_debate_phase()
        elif self.current_phase == GamePhase.DEBAT:
            self._start_voting_phase()
        elif self.current_phase == GamePhase.VOTE:
            self._show_voting_result()
    
    # ============================================================================
    # INTERACTION IA
    # ============================================================================
    
    def _schedule_ai_message(self):
        """Programme un message d'une IA aléatoire"""
        if self.current_phase != GamePhase.DEBAT:
            return
        
        alive_players = self.game.get_alive_players()
        alive_ais = [p for p in alive_players 
                    if not p.is_human and p != getattr(self.current_speaker, 'player', None)]
        
        if not alive_ais:
            return
        
        # Choisir une IA au hasard
        speaker = random.choice(alive_ais)
        
        # Trouver son sprite
        speaker_sprite = next((s for s in self.player_sprites 
                              if s.player.name == speaker.name), None)
        
        if speaker_sprite:
            # Générer le message
            message = speaker.generate_debate_message(self.game._get_public_status())
            
            # Commencer l'affichage
            self.current_speaker = speaker_sprite
            self.full_message = message
            self.displayed_message = ""
            self.char_index = 0
            self.type_timer = 0
            
            # Diffuser aux autres IA
            for ai in [p for p in alive_ais if p != speaker]:
                ai.receive_public_message(speaker.name, message)
            
            # Marquer l'interaction
            speaker_sprite.last_interaction = time.time()
    
    # ============================================================================
    # INTERACTION HUMAINE
    # ============================================================================
    
    def _start_typing(self):
        """Active le mode saisie de message"""
        if self.current_phase == GamePhase.DEBAT:
            self.is_typing = True
            self.typing_message = ""
            self.cursor_visible = True
            self.cursor_timer = 0
    
    def _send_human_message(self):
        """Envoie le message du joueur humain"""
        if not self.typing_message.strip():
            self.is_typing = False
            return
        
        # Ajouter au dialogue
        self._add_dialogue(self.human_player.name, self.typing_message)
        
        # Diffuser aux IA
        alive_players = self.game.get_alive_players()
        for ai in [p for p in alive_players if not p.is_human]:
            ai.receive_public_message(self.human_player.name, self.typing_message)
        
        # Réinitialiser
        self.typing_message = ""
        self.is_typing = False
        
        # Programmer une réponse IA
        arcade.schedule(lambda dt: self._schedule_ai_message(), 1)
    
    def _cast_vote(self):
        """Le joueur humain vote"""
        if not self.selected_player or not self.selected_player.player.is_alive:
            self._add_dialogue("Système", "Vous devez sélectionner un joueur vivant!")
            return
        
        if self.selected_player.player == self.human_player:
            self._add_dialogue("Système", "Vous ne pouvez pas voter pour vous-même!")
            return
        
        # Enregistrer le vote
        target_name = self.selected_player.player.name
        
        # Collecter tous les votes
        vote_counts = self.game.voting_phase(target_name)
        
        # Mettre à jour l'affichage
        for sprite in self.player_sprites:
            sprite.vote_count = vote_counts.get(sprite.player.name, 0)
        
        self._add_log(f"🗳️ {self.human_player.name} vote contre {target_name}")
        
        # Désactiver le bouton de vote
        if self.vote_button:
            self.vote_button.enabled = False
        
        # Afficher le résultat après un délai
        arcade.schedule(self._show_voting_result, 3)
    
    def _select_player(self, sprite: PlayerSprite):
        """Sélectionne un joueur"""
        if not sprite.player.is_alive:
            return
        
        if sprite.player == self.human_player:
            return
        
        # Désélectionner l'ancien
        self._deselect_all()
        
        # Sélectionner le nouveau
        sprite.is_selected = True
        self.selected_player = sprite
        
        # Activer le bouton de vote si en phase de vote
        if self.current_phase == GamePhase.VOTE and self.vote_button:
            self.vote_button.enabled = True
        
        self._add_dialogue("Système", f"Sélectionné: {sprite.player.name}")
    
    def _deselect_all(self):
        """Désélectionne tous les joueurs"""
        for sprite in self.player_sprites:
            sprite.is_selected = False
        self.selected_player = None
        
        if self.vote_button:
            self.vote_button.enabled = False
    
    # ============================================================================
    # MÉTHODES D'AFFICHAGE
    # ============================================================================
    
    def _add_dialogue(self, speaker: str, message: str):
        """Ajoute un message au dialogue"""
        self.dialogue_messages.append(DialogueMessage(speaker, message))
        
        # Limiter à 20 messages
        while len(self.dialogue_messages) > 20:
            self.dialogue_messages.pop(0)
    
    def _add_log(self, message: str):
        """Ajoute un message au journal"""
        self.game_log.append(message)
        print(f"[LOG] {message}")
        
        # Limiter à 15 messages
        while len(self.game_log) > 15:
            self.game_log.pop(0)
    
    # ============================================================================
    # MÉTHODES DE DESSIN
    # ============================================================================
    
    # def _draw_background(self):
    #     """Dessine le fond avec effet de profondeur"""
    #     # Dégradé de fond
    #     for i in range(SCREEN_HEIGHT // 20):
    #         alpha = 100 - i * 3
    #         if alpha > 0:
    #             # Utiliser draw_lrtb_rectangle_filled
    #                 top = SCREEN_HEIGHT - i * 20          # Position haute (plus grande)
    #                 bottom = SCREEN_HEIGHT - (i + 1) * 20
    #                 arcade.draw_lrtb_rectangle_filled(
    #                 0,  # left
    #                 SCREEN_WIDTH,  # right
    #                 top,  # top
    #                 bottom,  # bottom
    #                 (20 + i, 30 + i, 50 + i, alpha)
    #             )
        
    #     # Étoiles (effet décoratif)
    #     arcade.draw_text(
    #         "✦" * 50,
    #         SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
    #         (255, 255, 255, 50), 30,
    #         anchor_x="center", align="center",
    #         width=SCREEN_WIDTH
    #     )
    
    def _draw_background(self):
        """Dessine le fond avec effet de profondeur"""
        # Dégradé de fond - version ultra-simple avec polygon
        for i in range(SCREEN_HEIGHT // 20):
            alpha = 100 - i * 3
            if alpha > 0:
                # Points du rectangle (polygon)
                left = 0
                right = SCREEN_WIDTH
                bottom = SCREEN_HEIGHT - (i + 1) * 20  # Position basse
                top = bottom + 20                      # Position haute
                
                # draw_polygon_filled fonctionne toujours
                points = [
                    (left, bottom),
                    (right, bottom),
                    (right, top),
                    (left, top)
                ]
                arcade.draw_polygon_filled(
                    points, 
                    (20 + i, 30 + i, 50 + i, alpha)
                )
        
        # Étoiles
        arcade.draw_text(
            "✦" * 50,
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100,
            (255, 255, 255, 50), 30,
            anchor_x="center", align="center",
            width=SCREEN_WIDTH
        )
    # def _draw_sidebar(self):
    #     """Dessine la barre latérale droite"""
    #     sidebar_width = 300
    #     sidebar_x = SCREEN_WIDTH - sidebar_width // 2
        
    #     # Fond de la sidebar
    #     arcade.draw_rectangle_filled(
    #         sidebar_x, SCREEN_HEIGHT // 2,
    #         sidebar_width, SCREEN_HEIGHT,
    #         COLOR_SIDEBAR
    #     )
        
    #     # Titre
    #     arcade.draw_text(
    #         "📊 STATUT DE LA PARTIE",
    #         sidebar_x, SCREEN_HEIGHT - 40,
    #         arcade.color.GOLD, 20,
    #         anchor_x="center", bold=True
    #     )
        
    #     # Informations
    #     y_offset = SCREEN_HEIGHT - 100
        
    #     # Phase actuelle
    #     phase_text = f"Phase: {self.current_phase.value}"
    #     arcade.draw_text(
    #         phase_text,
    #         sidebar_x - 120, y_offset,
    #         arcade.color.LIGHT_BLUE, 16
    #     )
    #     y_offset -= 30
        
    #     # Timer
    #     timer_text = f"Temps: {int(self.phase_timer)}s"
    #     arcade.draw_text(
    #         timer_text,
    #         sidebar_x - 120, y_offset,
    #         arcade.color.YELLOW, 16
    #     )
    #     y_offset -= 40
        
    #     # Jour
    #     day_text = f"Jour: {self.game.day}"
    #     arcade.draw_text(
    #         day_text,
    #         sidebar_x - 120, y_offset,
    #         arcade.color.WHITE, 18, bold=True
    #     )
    #     y_offset -= 40
        
    #     # Statistiques
    #     alive = self.game.get_alive_players()
    #     wolves = sum(1 for p in alive if p.role.camp == Camp.LOUP)
    #     villagers = sum(1 for p in alive if p.role.camp == Camp.VILLAGEOIS)
        
    #     arcade.draw_text(
    #         f"Joueurs vivants: {len(alive)}",
    #         sidebar_x - 120, y_offset,
    #         arcade.color.WHITE, 14
    #     )
    #     y_offset -= 25
        
    #     arcade.draw_text(
    #         f"Loups-Garous: {wolves}",
    #         sidebar_x - 120, y_offset,
    #         arcade.color.RED, 14
    #     )
    #     y_offset -= 25
        
    #     arcade.draw_text(
    #         f"Villageois: {villagers}",
    #         sidebar_x - 120, y_offset,
    #         arcade.color.GREEN, 14
    #     )
    #     y_offset -= 40
        
    #     # Votre rôle
    #     if self.human_player:
    #         role_text = f"Votre rôle: {self.human_player.role.name}"
    #         arcade.draw_text(
    #             role_text,
    #             sidebar_x - 120, y_offset,
    #             arcade.color.CYAN, 14
    #         )
    #         y_offset -= 25
            
    #         camp_text = f"Camp: {self.human_player.role.camp.value}"
    #         arcade.draw_text(
    #             camp_text,
    #             sidebar_x - 120, y_offset,
    #             arcade.color.LIGHT_CYAN, 14
    #         )
    

    
    def _draw_dialogue_panel(self):
        """Dessine le panneau de dialogue"""
        panel_width = 400
        panel_x = panel_width // 2 + 20
        panel_y = SCREEN_HEIGHT - 100
        
        # Titre
        arcade.draw_text(
            "💬 DISCUSSION EN DIRECT",
            panel_x, panel_y,
            arcade.color.LIGHT_BLUE, 18, bold=True
        )
        
        # Messages
        y_offset = panel_y - 40
        for msg in self.dialogue_messages[-8:]:  # 8 derniers messages
            # Couleur du nom du speaker
            if msg.speaker == self.human_player.name:
                name_color = COLOR_HUMAN
            elif any(p.name == msg.speaker and p.role.camp == Camp.LOUP
                    for p in self.game.players):
                name_color = COLOR_WOLF
            else:
                name_color = COLOR_TEXT
            
            # Nom du speaker
            arcade.draw_text(
                f"{msg.speaker}:",
                panel_x - 180, y_offset,
                name_color, 12, bold=True,
                width=100, align="right"
            )
            
            # Message
            arcade.draw_text(
                msg.message,
                panel_x - 70, y_offset,
                (msg.alpha, msg.alpha, msg.alpha), 12,
                width=350
            )
            
            y_offset -= 25
    
    def _draw_game_log(self):
        """Dessine le journal d'événements"""
        log_x = 20
        log_y = 200
        
        # Titre
        arcade.draw_text(
            "📜 JOURNAL DES ÉVÉNEMENTS",
            log_x, log_y,
            arcade.color.ORANGE, 16, bold=True
        )
        
        # Messages
        y_offset = log_y - 30
        for msg in self.game_log[-10:]:  # 10 derniers messages
            arcade.draw_text(
                f"• {msg}",
                log_x, y_offset,
                COLOR_LOG, 12
            )
            y_offset -= 20
    
    def _draw_game_info(self):
        """Dessine les informations du jeu en haut"""
        # Titre principal
        title = f"🎭 LOUP GAROU IA - {self.human_player.name}"
        arcade.draw_text(
            title,
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30,
            arcade.color.GOLD, 24,
            anchor_x="center", bold=True
        )
        
        # Sous-titre
        subtitle = f"Phase: {self.current_phase.value} | Jour {self.game.day}"
        arcade.draw_text(
            subtitle,
            SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60,
            arcade.color.LIGHT_BLUE, 18,
            anchor_x="center"
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
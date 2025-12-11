# # -*- coding: utf-8 -*-
# import arcade
# import random
# import time
# from enum import Enum # Garder Enum pour GameState
# import math

# # --- Importations du projet ---
# from game_core import GameManager, Player # N'importe plus Camp ou NightAction de game_core
# from enums_and_roles import Camp, NightAction # Les vrais emplacements des Enums
# # ChatAgent n'est plus nécessaire ici car il est instancié dans GameManager

# from dotenv import load_dotenv
# load_dotenv()

# # --- Paramètres de la Fenêtre ---
# SCREEN_WIDTH = 1000
# SCREEN_HEIGHT = 700
# SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

# # --- États du Jeu ---
# class GameState(Enum):
#     SETUP = 1
#     NIGHT = 2
#     DEBATE = 3
#     VOTING = 4
#     RESULT = 5
#     GAME_OVER = 6


# class LoupGarouGame(arcade.Window):
    
#     def __init__(self, width, height, title, human_name="Humain_Lucie"):
        
#         super().__init__(width, height, title)
#         arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

#         # 1. Initialisation du Moteur de Jeu
#         self.game_manager = GameManager(human_player_name=human_name)
#         self.current_state = GameState.SETUP
        
#         # 2. Variables d'Affichage
#         self.log_messages = [] # Pour stocker les messages du débat et les actions
#         self.player_sprites = arcade.SpriteList()
#         self.player_map = {} # Pour lier le joueur au sprite (utile plus tard)
        
#         # 3. Gestion du Temps et Vitesse d'écriture (Débat)
#         self.debate_timer = GameManager.DEBATE_TIME_LIMIT
#         self.current_speaker = None
#         self.current_message_full = ""
#         self.current_message_display = ""
#         self.typing_speed_counter = 0 # Pour simuler la vitesse d'écriture
#         self.typing_delay = 3 # Afficher 1 caractère toutes les 3 frames (à ajuster)

#         # Initialisation des Sprites (simple cercle pour l'instant)
#         self._setup_sprites()
        
#         # Commencer le jeu
#         self.start_game_loop()

#     def _setup_sprites(self):
#         """Crée les représentations visuelles des joueurs."""
        
#         num_players = len(self.game_manager.players)
#         radius = 50  # Taille du cercle
#         center_x = SCREEN_WIDTH / 2
#         center_y = SCREEN_HEIGHT / 2
        
#         # Disposition en cercle (simple représentation)
#         angle_step = 360 / num_players
        
#         for i, player in enumerate(self.game_manager.players):
#             angle = i * angle_step
#             rad_angle = math.radians(angle)
#             # Calcul des coordonnées sur un cercle (simple trigonométrie)
#             x = center_x + 250 * math.cos(angle)
#             y = center_y + 250 * math.sin(angle)
            
#             # Représentation simple (un cercle de couleur)
#             color = arcade.color.GREEN if player.is_alive else arcade.color.RED_BROWN
#             sprite = arcade.SpriteCircle(radius, color, center_x=x, center_y=y)
            
#             self.player_sprites.append(sprite)
#             self.player_map[player.name] = sprite
            
#     def start_game_loop(self):
#         """Commence la première phase du jeu (Nuit) après le setup."""
#         self.log_messages.append("--- Initialisation de la Partie ---")
#         self.log_messages.append(f"Joueurs : {len(self.game_manager.players)}")
#         self.current_state = GameState.NIGHT
#         self.game_manager.day = 1
#         self.log_messages.append(f"JOUR 1 : La NUIT tombe.")


#     # --- BOUCLE DE JEU ARCADES ---

#     def on_draw(self):
#         """Affichage : appelé à chaque image pour dessiner."""
#         self.clear()
        
#         # Dessiner les joueurs
#         self.player_sprites.draw()
        
#         # Dessiner le nom et l'état des joueurs
#         for player in self.game_manager.players:
#              sprite = self.player_map.get(player.name)
#              if sprite:
#                  color = arcade.color.WHITE
#                  # Si le joueur est mort, afficher en rouge
#                  if not player.is_alive:
#                      color = arcade.color.RED
                 
#                  # Affichage du nom au-dessus du sprite
#                  arcade.draw_text(
#                      f"{player.name} ({'IA' if not player.is_human else 'H'})",
#                      sprite.center_x, sprite.center_y + 60, color, 12, anchor_x="center"
#                  )
                 
#                  # Affichage du rôle si le jeu est terminé ou si c'est l'humain
#                  if self.current_state == GameState.GAME_OVER or player.is_human:
#                      role_text = f"Role: {player.role.name}"
#                      arcade.draw_text(role_text, sprite.center_x, sprite.center_y - 60, arcade.color.YELLOW_GREEN, 10, anchor_x="center")

#         # Afficher le Log de Discussion (à gauche)
#         self._draw_log()

#         # Afficher le Compteur Loup (en haut à droite)
#         self._draw_status()
        
#         # Afficher le message de l'IA en train d'écrire
#         self._draw_typing_message()

#     def on_update(self, delta_time):
#         """Logique : appelé à chaque image pour mettre à jour l'état."""
        
#         # Si on est en mode débat, on simule le temps et la parole
#         if self.current_state == GameState.DEBATE:
#             self._update_debate(delta_time)
            
#         # Si le débat est terminé, passer au vote
#         elif self.current_state == GameState.VOTING:
#             self.game_manager._day_phase() # Exécute le vote et le lynchage
#             self.current_state = GameState.RESULT
            
#         # Si c'est la nuit, exécuter les actions de nuit (simple pour l'instant)
#         elif self.current_state == GameState.NIGHT:
#              # Simuler le passage de la nuit (dans un jeu réel, attendre l'input humain)
#              self.game_manager._night_phase()
#              self.current_state = GameState.DEBATE
#              self.debate_timer = GameManager.DEBATE_TIME_LIMIT # Réinitialiser le timer
#              self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")


#     # --- Méthodes de Dessin Spécifiques ---

#     def _draw_log(self):
#         """Dessine les derniers messages de discussion."""
#         y_pos = SCREEN_HEIGHT - 30
#         arcade.draw_text("JOURNAL DE BORD:", 20, y_pos, arcade.color.ORANGE_RED, 14)
#         y_pos -= 20
        
#         # Afficher les 15 derniers messages
#         for msg in self.log_messages[-15:]:
#             arcade.draw_text(msg, 20, y_pos, arcade.color.LIGHT_GRAY, 10)
#             y_pos -= 15
            
#     def _draw_status(self):
#         """Affiche les compteurs de jeu."""
        
#         # Compteur Loups Garous
#         arcade.draw_text(
#             f"Loups Vivants : {self.game_manager.wolves_alive}",
#             SCREEN_WIDTH - 200, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16
#         )
        
#         # Timer de Débat
#         if self.current_state in [GameState.DEBATE, GameState.VOTING]:
#              arcade.draw_text(
#                 f"Temps Restant : {int(self.debate_timer)}s",
#                 SCREEN_WIDTH - 200, SCREEN_HEIGHT - 60, arcade.color.YELLOW, 14
#             )

#     def _draw_typing_message(self):
#         """Affiche le message en cours d'écriture (simule l'IA)."""
#         if self.current_speaker and self.current_message_display != self.current_message_full:
#             arcade.draw_text(
#                 f"💬 {self.current_speaker.name} tape...",
#                 SCREEN_WIDTH / 2, 50, arcade.color.AZURE, 16, anchor_x="center"
#             )
#             arcade.draw_text(
#                 self.current_message_display,
#                 SCREEN_WIDTH / 2, 30, arcade.color.LIGHT_GRAY, 12, anchor_x="center"
#             )


#     # --- Logique de Débat (Contrainte de Temps) ---

#     def _update_debate(self, delta_time):
#         """Gère le temps et la parole pendant la phase de débat."""
        
#         self.debate_timer -= delta_time
        
#         # Logique d'écriture (vitesse d'écriture des LLM)
#         if self.current_message_display != self.current_message_full:
#             self.typing_speed_counter += 1
#             if self.typing_speed_counter >= self.typing_delay:
#                 # Ajoute un caractère
#                 current_len = len(self.current_message_display)
#                 if current_len < len(self.current_message_full):
#                     self.current_message_display += self.current_message_full[current_len]
#                 else:
#                     # Message terminé, l'ajouter au log
#                     self.log_messages.append(f"{self.current_speaker.name}: {self.current_message_full}")
#                     self.current_speaker = None
#                 self.typing_speed_counter = 0

#         # Si le timer est écoulé, on passe au vote
#         if self.debate_timer <= 0 and self.current_state == GameState.DEBATE:
#             self.current_state = GameState.VOTING
#             self.log_messages.append("\n🗳️ FIN DU DÉBAT. DÉBUT DU VOTE.")
        
#         # Si personne ne parle, choisir un nouvel orateur
#         elif self.current_speaker is None and self.debate_timer > 0:
#             alive_ais = [p for p in self.game_manager.get_alive_players() if not p.is_human]
#             if alive_ais:
#                 speaker = random.choice(alive_ais)
#                 # Générer le message de l'IA
#                 debate_message = speaker.generate_debate_message(self.game_manager._get_public_status())
                
#                 # Mettre en place la simulation de la frappe
#                 self.current_speaker = speaker
#                 self.current_message_full = debate_message
#                 self.current_message_display = ""
                
#                 # Envoyer le message aux autres IA
#                 for listener in [p for p in alive_ais if p != speaker]:
#                     listener.receive_public_message(speaker.name, debate_message)


#     # --- Gestion de l'Input Humain (Touches) ---

#     def on_key_press(self, symbol, modifiers):
#         """Gère les entrées clavier (ex: pour skipper le débat)."""
        
#         # Possibilité de skipper les délibérations
#         if symbol == arcade.key.SPACE:
#             if self.current_state == GameState.DEBATE:
#                 self.debate_timer = 0 # Fin immédiate du débat
#                 self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")
#             elif self.current_state == GameState.NIGHT:
#                 # Si c'est la nuit, on passe immédiatement à l'étape suivante (pour le test)
#                 self.current_state = GameState.DEBATE


# # --- Lancement du Jeu ---

# def main():
#     """Fonction principale pour lancer l'application Arcade."""
#     # NOTE: Assurez-vous que les fichiers de contexte existent dans le dossier 'context'
#     game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
#     arcade.run()


# if __name__ == "__main__":
#     # Pour le test, assure-toi d'avoir tes 9 fichiers de contexte
#     # et que GameManager._setup_players fonctionne correctement
#     main()










# -*- coding: utf-8 -*-
"""
Interface graphique principale du jeu Loup Garou IA
Utilise Arcade pour l'affichage et l'interaction
"""
import arcade
import random
import time
import math
from typing import Optional, List
import os

# Importations locales
from game_core import GameManager
from enums_and_roles import Camp, GamePhase

# ============================================================================
# CONSTANTES
# ============================================================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800
SCREEN_TITLE = "🎭 Loup Garou IA - Édition Interactive"
FPS = 60

# Couleurs personnalisées
COLOR_BACKGROUND = (15, 25, 45)
COLOR_SIDEBAR = (30, 40, 70, 200)
COLOR_PLAYER_ALIVE = (70, 130, 180)
COLOR_PLAYER_DEAD = (100, 100, 100)
COLOR_WOLF = (180, 50, 50)
COLOR_VILLAGER = (50, 150, 50)
COLOR_HUMAN = (0, 200, 255)
COLOR_SELECTED = (255, 215, 0)
COLOR_BUTTON = (40, 120, 180)
COLOR_BUTTON_HOVER = (60, 160, 220)
COLOR_TEXT = (240, 240, 240)
COLOR_LOG = (200, 200, 200)
COLOR_DIALOGUE = (220, 220, 180)

# ============================================================================
# CLASSES D'INTERFACE
# ============================================================================

class PlayerSprite(arcade.SpriteCircle):
    """Sprite représentant un joueur dans le cercle de discussion"""
    
    def __init__(self, player, radius=45):
        # Déterminer la couleur en fonction du statut
        if not player.is_alive:
            color = COLOR_PLAYER_DEAD
        elif player.is_human:
            color = COLOR_HUMAN
        elif player.role.camp == Camp.LOUP:
            color = COLOR_WOLF
        else:
            color = COLOR_PLAYER_ALIVE
            
        super().__init__(radius, color)
        self.player = player
        self.name = player.name
        self.is_selected = False
        self.vote_count = 0
        self.pulse_timer = 0
        self.last_interaction = 0
        
    def update(self, delta_time: float = 1/60):
        """Animation du sprite"""
        self.pulse_timer += delta_time
        self.last_interaction += delta_time
        
        # Effet de pulsation si sélectionné
        if self.is_selected:
            pulse = math.sin(self.pulse_timer * 5) * 3
            self.scale = 1.0 + pulse * 0.1
        else:
            self.scale = 1.0
            
        # Effet de clignotement si vient de parler
        if time.time() - self.last_interaction < 2:
            alpha = int(200 + 55 * math.sin(self.pulse_timer * 8))
            self.alpha = alpha
        else:
            self.alpha = 255
    
    def draw_info(self):
        """Dessine les informations du joueur autour du sprite"""
        # Nom du joueur
        color = COLOR_TEXT
        if not self.player.is_alive:
            color = (150, 150, 150)
        elif self.player.is_human:
            color = COLOR_HUMAN
            
        arcade.draw_text(
            self.player.name,
            self.center_x, self.center_y + 60,
            color, 14,
            anchor_x="center", anchor_y="center",
            bold=self.player.is_human
        )
        
        # Statut (vivant/mort)
        status = "💀" if not self.player.is_alive else "❤️"
        status_color = arcade.color.RED if not self.player.is_alive else arcade.color.GREEN
        arcade.draw_text(
            status,
            self.center_x, self.center_y + 40,
            status_color, 20,
            anchor_x="center", anchor_y="center"
        )
        
        # Rôle (visible seulement si mort ou si c'est l'humain)
        if not self.player.is_alive or self.player.is_human:
            role_text = self.player.role.name
            arcade.draw_text(
                role_text,
                self.center_x, self.center_y - 60,
                arcade.color.LIGHT_GOLDENROD_YELLOW, 12,
                anchor_x="center", anchor_y="center"
            )
        
        # Compteur de votes (pendant le vote)
        if self.vote_count > 0:
            arcade.draw_circle_filled(
                self.center_x + 35, self.center_y + 35,
                15, arcade.color.DARK_RED
            )
            arcade.draw_text(
                str(self.vote_count),
                self.center_x + 35, self.center_y + 35,
                arcade.color.WHITE, 12,
                anchor_x="center", anchor_y="center"
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
        """Dessine le message en cours de frappe par une IA"""
        if not self.current_speaker or not self.displayed_message:
            return
        
        # Bulle de dialogue
        bubble_x = self.current_speaker.center_x
        bubble_y = self.current_speaker.center_y + 100
        
        # Dessiner la bulle
        arcade.draw_rectangle_filled(
            bubble_x, bubble_y, 300, 80,
            (20, 20, 20, 220)
        )
        arcade.draw_rectangle_outline(
            bubble_x, bubble_y, 300, 80,
            arcade.color.LIGHT_GRAY, 2
        )
        
        # Pointe de la bulle
        arcade.draw_triangle_filled(
            self.current_speaker.center_x, self.current_speaker.center_y + 70,
            self.current_speaker.center_x - 15, self.current_speaker.center_y + 50,
            self.current_speaker.center_x + 15, self.current_speaker.center_y + 50,
            (20, 20, 20, 220)
        )
        
        # Nom du speaker
        arcade.draw_text(
            f"{self.current_speaker.player.name} parle...",
            bubble_x - 140, bubble_y + 25,
            arcade.color.LIGHT_GREEN, 12,
            width=280, align="center"
        )
        
        # Message
        arcade.draw_text(
            self.displayed_message,
            bubble_x - 140, bubble_y - 10,
            arcade.color.WHITE, 12,
            width=280
        )
    
    def _draw_input_field(self):
        """Dessine le champ de saisie pour le joueur humain"""
        field_x = SCREEN_WIDTH // 2
        field_y = 80
        
        # Fond du champ
        arcade.draw_rectangle_filled(
            field_x, field_y, 600, 60,
            (30, 30, 30, 240)
        )
        arcade.draw_rectangle_outline(
            field_x, field_y, 600, 60,
            arcade.color.LIGHT_BLUE, 2
        )
        
        # Instructions
        arcade.draw_text(
            "Tapez votre message (Entrée = envoyer, Échap = annuler):",
            field_x - 290, field_y + 20,
            arcade.color.LIGHT_GRAY, 12
        )
        
        # Texte saisi
        cursor = "|" if self.cursor_visible else ""
        display_text = f"{self.typing_message}{cursor}"
        arcade.draw_text(
            display_text,
            field_x - 290, field_y - 10,
            arcade.color.WHITE, 16,
            width=580
        )
    
    # ============================================================================
    # BOUCLE DE JEU ARCADES
    # ============================================================================
    
    def on_draw(self):
        """Dessine tout à l'écran"""
        self.clear()
        
        # Fond avec effet de profondeur
        self._draw_background()
        
        # Cercle central des joueurs - utiliser la SpriteList
        self.player_sprites_list.draw()
        
        # Dessiner les infos des joueurs
        for sprite in self.player_sprites:
            sprite.draw_info()
        
        # Interface utilisateur
        self._draw_sidebar()
        self._draw_dialogue_panel()
        self._draw_game_log()
        self._draw_game_info()
        
        # Message en cours de frappe (IA)
        if self.current_speaker and self.displayed_message:
            self._draw_typing_message()
        
        # Saisie du joueur humain
        if self.is_typing:
            self._draw_input_field()
        
        # Boutons
        if self.vote_button:
            self.vote_button.draw()
        if self.send_button:
            self.send_button.draw()
        if self.skip_button:
            self.skip_button.draw()
    
    def on_update(self, delta_time: float):
        """Met à jour la logique du jeu"""
        # Mettre à jour les sprites
        self.player_sprites_list.update()
        for sprite in self.player_sprites:
            sprite.update(delta_time)
        
        # Mettre à jour les messages
        for msg in self.dialogue_messages[:]:
            msg.update(delta_time)
            if msg.is_expired():
                self.dialogue_messages.remove(msg)
        
        # Mettre à jour le timer de phase
        if self.current_phase not in [GamePhase.FIN, GamePhase.RESULTAT]:
            self.phase_timer -= delta_time
            if self.phase_timer <= 0:
                self._skip_phase()
        
        # Mettre à jour l'animation de frappe
        if self.current_speaker and self.char_index < len(self.full_message):
            self.type_timer += delta_time
            if self.type_timer >= self.type_speed:
                self.type_timer = 0
                self.displayed_message += self.full_message[self.char_index]
                self.char_index += 1
                
                # Si le message est complet, programmer le suivant
                if self.char_index >= len(self.full_message):
                    arcade.schedule(lambda dt: self._schedule_ai_message(), 2)
        
        # Mettre à jour le curseur (clignotement)
        if self.is_typing:
            self.cursor_timer += delta_time
            if self.cursor_timer >= 0.5:
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible
        
        # Mettre à jour l'état des boutons
        if self.send_button:
            self.send_button.enabled = (self.current_phase == GamePhase.DEBAT)
        
        if self.skip_button:
            self.skip_button.enabled = (self.current_phase not in [GamePhase.FIN, GamePhase.RESULTAT])
    
    # ============================================================================
    # GESTION DES ÉVÉNEMENTS
    # ============================================================================
    
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        """Gère les clics de souris"""
        # Vérifier les boutons UI
        if self.vote_button and self.vote_button.contains_point(x, y):
            self.vote_button.on_click()
            return
        
        if self.send_button and self.send_button.contains_point(x, y):
            self.send_button.on_click()
            return
        
        if self.skip_button and self.skip_button.contains_point(x, y):
            self.skip_button.on_click()
            return
        
        # Vérifier les clics sur les joueurs
        for sprite in self.player_sprites:
            distance = math.sqrt((x - sprite.center_x)**2 + (y - sprite.center_y)**2)
            if distance <= sprite.width // 2:
                self._select_player(sprite)
                return
        
        # Si clic ailleurs, désélectionner
        self._deselect_all()
    
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        """Gère le mouvement de la souris"""
        # Mettre à jour l'état de survol des boutons
        if self.vote_button:
            self.vote_button.is_hovered = self.vote_button.contains_point(x, y)
        
        if self.send_button:
            self.send_button.is_hovered = self.send_button.contains_point(x, y)
        
        if self.skip_button:
            self.skip_button.is_hovered = self.skip_button.contains_point(x, y)
    
    def on_key_press(self, symbol: int, modifiers: int):
        """Gère les pressions de touches"""
        # Mode saisie de message
        if self.is_typing:
            if symbol == arcade.key.ENTER:
                self._send_human_message()
            elif symbol == arcade.key.ESCAPE:
                self.is_typing = False
                self.typing_message = ""
            elif symbol == arcade.key.BACKSPACE:
                self.typing_message = self.typing_message[:-1]
            elif 32 <= symbol <= 126:  # Caractères imprimables
                char = chr(symbol)
                if modifiers & arcade.key.MOD_SHIFT:
                    char = char.upper()
                self.typing_message += char
            return
        
        # Raccourcis globaux
        if symbol == arcade.key.SPACE:
            self._skip_phase()
        elif symbol == arcade.key.T and self.current_phase == GamePhase.DEBAT:
            self._start_typing()
        elif symbol == arcade.key.ESCAPE:
            self._deselect_all()

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main():
    """Fonction principale"""
    # Vérifier les fichiers de contexte
    if not os.path.exists("context"):
        os.makedirs("context")
        print("Création du dossier 'context'...")
        for i in range(1, 10):
            with open(f"context/perso_{i}.txt", "w", encoding="utf-8") as f:
                f.write(f"Tu es le joueur IA {i}. Tu as une personnalité unique. "
                       f"Dans le jeu Loup Garou, joue ton rôle naturellement.")
    
    # Lancer le jeu
    game = LoupGarouGame()
    arcade.run()

if __name__ == "__main__":
    main()
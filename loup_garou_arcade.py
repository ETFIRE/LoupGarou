# -*- coding: utf-8 -*-
import arcade
import random
import time
from enum import Enum # Garder Enum pour GameState
import math

# --- Importations du projet ---
from game_core import GameManager, Player # N'importe plus Camp ou NightAction de game_core
from enums_and_roles import Camp, NightAction # Les vrais emplacements des Enums
# ChatAgent n'est plus nécessaire ici car il est instancié dans GameManager

from dotenv import load_dotenv
load_dotenv()

# --- Paramètres de la Fenêtre ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
SCREEN_TITLE = "Loup Garou IA - Lucia Edition"

# --- États du Jeu ---
class GameState(Enum):
    SETUP = 1
    NIGHT = 2
    DEBATE = 3
    VOTING = 4
    RESULT = 5
    GAME_OVER = 6


class LoupGarouGame(arcade.Window):
    
    def __init__(self, width, height, title, human_name="Humain_Lucie"):
        
        super().__init__(width, height, title)
        arcade.set_background_color(arcade.color.DARK_BLUE_GRAY)

        # 1. Initialisation du Moteur de Jeu
        self.game_manager = GameManager(human_player_name=human_name)
        self.current_state = GameState.SETUP
        
        # 2. Variables d'Affichage
        self.log_messages = [] # Pour stocker les messages du débat et les actions
        self.player_sprites = arcade.SpriteList()
        self.player_map = {} # Pour lier le joueur au sprite (utile plus tard)
        
        # 3. Gestion du Temps et Vitesse d'écriture (Débat)
        self.debate_timer = GameManager.DEBATE_TIME_LIMIT
        self.current_speaker = None
        self.current_message_full = ""
        self.current_message_display = ""
        self.typing_speed_counter = 0 # Pour simuler la vitesse d'écriture
        self.typing_delay = 3 # Afficher 1 caractère toutes les 3 frames (à ajuster)

        # Initialisation des Sprites (simple cercle pour l'instant)
        self._setup_sprites()
        
        # Commencer le jeu
        self.start_game_loop()

    def _setup_sprites(self):
        """Crée les représentations visuelles des joueurs."""
        
        num_players = len(self.game_manager.players)
        radius = 50  # Taille du cercle
        center_x = SCREEN_WIDTH / 2
        center_y = SCREEN_HEIGHT / 2
        
        # Disposition en cercle (simple représentation)
        angle_step = 360 / num_players
        
        for i, player in enumerate(self.game_manager.players):
            angle = i * angle_step
            rad_angle = math.radians(angle)
            # Calcul des coordonnées sur un cercle (simple trigonométrie)
            x = center_x + 250 * math.cos(angle)
            y = center_y + 250 * math.sin(angle)
            
            # Représentation simple (un cercle de couleur)
            color = arcade.color.GREEN if player.is_alive else arcade.color.RED_BROWN
            sprite = arcade.SpriteCircle(radius, color, center_x=x, center_y=y)
            
            self.player_sprites.append(sprite)
            self.player_map[player.name] = sprite
            
    def start_game_loop(self):
        """Commence la première phase du jeu (Nuit) après le setup."""
        self.log_messages.append("--- Initialisation de la Partie ---")
        self.log_messages.append(f"Joueurs : {len(self.game_manager.players)}")
        self.current_state = GameState.NIGHT
        self.game_manager.day = 1
        self.log_messages.append(f"JOUR 1 : La NUIT tombe.")


    # --- BOUCLE DE JEU ARCADES ---

    def on_draw(self):
        """Affichage : appelé à chaque image pour dessiner."""
        self.clear()
        
        # Dessiner les joueurs
        self.player_sprites.draw()
        
        # Dessiner le nom et l'état des joueurs
        for player in self.game_manager.players:
             sprite = self.player_map.get(player.name)
             if sprite:
                 color = arcade.color.WHITE
                 # Si le joueur est mort, afficher en rouge
                 if not player.is_alive:
                     color = arcade.color.RED
                 
                 # Affichage du nom au-dessus du sprite
                 arcade.draw_text(
                     f"{player.name} ({'IA' if not player.is_human else 'H'})",
                     sprite.center_x, sprite.center_y + 60, color, 12, anchor_x="center"
                 )
                 
                 # Affichage du rôle si le jeu est terminé ou si c'est l'humain
                 if self.current_state == GameState.GAME_OVER or player.is_human:
                     role_text = f"Role: {player.role.name}"
                     arcade.draw_text(role_text, sprite.center_x, sprite.center_y - 60, arcade.color.YELLOW_GREEN, 10, anchor_x="center")

        # Afficher le Log de Discussion (à gauche)
        self._draw_log()

        # Afficher le Compteur Loup (en haut à droite)
        self._draw_status()
        
        # Afficher le message de l'IA en train d'écrire
        self._draw_typing_message()

    def on_update(self, delta_time):
        """Logique : appelé à chaque image pour mettre à jour l'état."""
        
        # Si on est en mode débat, on simule le temps et la parole
        if self.current_state == GameState.DEBATE:
            self._update_debate(delta_time)
            
        # Si le débat est terminé, passer au vote
        elif self.current_state == GameState.VOTING:
            self.game_manager._day_phase() # Exécute le vote et le lynchage
            self.current_state = GameState.RESULT
            
        # Si c'est la nuit, exécuter les actions de nuit (simple pour l'instant)
        elif self.current_state == GameState.NIGHT:
             # Simuler le passage de la nuit (dans un jeu réel, attendre l'input humain)
             self.game_manager._night_phase()
             self.current_state = GameState.DEBATE
             self.debate_timer = GameManager.DEBATE_TIME_LIMIT # Réinitialiser le timer
             self.log_messages.append(f"\n☀️ Jour {self.game_manager.day} : Le débat commence !")


    # --- Méthodes de Dessin Spécifiques ---

    def _draw_log(self):
        """Dessine les derniers messages de discussion."""
        y_pos = SCREEN_HEIGHT - 30
        arcade.draw_text("JOURNAL DE BORD:", 20, y_pos, arcade.color.ORANGE_RED, 14)
        y_pos -= 20
        
        # Afficher les 15 derniers messages
        for msg in self.log_messages[-15:]:
            arcade.draw_text(msg, 20, y_pos, arcade.color.LIGHT_GRAY, 10)
            y_pos -= 15
            
    def _draw_status(self):
        """Affiche les compteurs de jeu."""
        
        # Compteur Loups Garous
        arcade.draw_text(
            f"Loups Vivants : {self.game_manager.wolves_alive}",
            SCREEN_WIDTH - 200, SCREEN_HEIGHT - 30, arcade.color.WHITE, 16
        )
        
        # Timer de Débat
        if self.current_state in [GameState.DEBATE, GameState.VOTING]:
             arcade.draw_text(
                f"Temps Restant : {int(self.debate_timer)}s",
                SCREEN_WIDTH - 200, SCREEN_HEIGHT - 60, arcade.color.YELLOW, 14
            )

    def _draw_typing_message(self):
        """Affiche le message en cours d'écriture (simule l'IA)."""
        if self.current_speaker and self.current_message_display != self.current_message_full:
            arcade.draw_text(
                f"💬 {self.current_speaker.name} tape...",
                SCREEN_WIDTH / 2, 50, arcade.color.AZURE, 16, anchor_x="center"
            )
            arcade.draw_text(
                self.current_message_display,
                SCREEN_WIDTH / 2, 30, arcade.color.LIGHT_GRAY, 12, anchor_x="center"
            )


    # --- Logique de Débat (Contrainte de Temps) ---

    def _update_debate(self, delta_time):
        """Gère le temps et la parole pendant la phase de débat."""
        
        self.debate_timer -= delta_time
        
        # Logique d'écriture (vitesse d'écriture des LLM)
        if self.current_message_display != self.current_message_full:
            self.typing_speed_counter += 1
            if self.typing_speed_counter >= self.typing_delay:
                # Ajoute un caractère
                current_len = len(self.current_message_display)
                if current_len < len(self.current_message_full):
                    self.current_message_display += self.current_message_full[current_len]
                else:
                    # Message terminé, l'ajouter au log
                    self.log_messages.append(f"{self.current_speaker.name}: {self.current_message_full}")
                    self.current_speaker = None
                self.typing_speed_counter = 0

        # Si le timer est écoulé, on passe au vote
        if self.debate_timer <= 0 and self.current_state == GameState.DEBATE:
            self.current_state = GameState.VOTING
            self.log_messages.append("\n🗳️ FIN DU DÉBAT. DÉBUT DU VOTE.")
        
        # Si personne ne parle, choisir un nouvel orateur
        elif self.current_speaker is None and self.debate_timer > 0:
            alive_ais = [p for p in self.game_manager.get_alive_players() if not p.is_human]
            if alive_ais:
                speaker = random.choice(alive_ais)
                # Générer le message de l'IA
                debate_message = speaker.generate_debate_message(self.game_manager._get_public_status())
                
                # Mettre en place la simulation de la frappe
                self.current_speaker = speaker
                self.current_message_full = debate_message
                self.current_message_display = ""
                
                # Envoyer le message aux autres IA
                for listener in [p for p in alive_ais if p != speaker]:
                    listener.receive_public_message(speaker.name, debate_message)


    # --- Gestion de l'Input Humain (Touches) ---

    def on_key_press(self, symbol, modifiers):
        """Gère les entrées clavier (ex: pour skipper le débat)."""
        
        # Possibilité de skipper les délibérations
        if symbol == arcade.key.SPACE:
            if self.current_state == GameState.DEBATE:
                self.debate_timer = 0 # Fin immédiate du débat
                self.log_messages.append("\n⏩ DÉBAT SKIPPÉ PAR L'HUMAIN.")
            elif self.current_state == GameState.NIGHT:
                # Si c'est la nuit, on passe immédiatement à l'étape suivante (pour le test)
                self.current_state = GameState.DEBATE


# --- Lancement du Jeu ---

def main():
    """Fonction principale pour lancer l'application Arcade."""
    # NOTE: Assurez-vous que les fichiers de contexte existent dans le dossier 'context'
    game = LoupGarouGame(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    arcade.run()


if __name__ == "__main__":
    # Pour le test, assure-toi d'avoir tes 9 fichiers de contexte
    # et que GameManager._setup_players fonctionne correctement
    main()
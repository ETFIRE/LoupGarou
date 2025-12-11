import pygame
import sys
from game import Game

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
FPS = 30


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Loup Garou IA")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 24)

    # Contexte système de base (à enrichir)
    system_context = (
        "Tu participes à un jeu du Loup Garou. "
        "Tu dois débattre, accuser, défendre et parfois mentir."
    )

    game = Game(system_context=system_context)
    game.setup_new_game(human_name="Joueur", human_choose_role=False)

    running = True
    phase = "debate"       # "debate" ou "vote"
    debate_logs = []       # texte à afficher (débat ou résultat de vote)

    while running:
        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Touche ESPACE = passer à la phase suivante
                elif event.key == pygame.K_SPACE:
                    if phase == "debate":
                        # Lancer un débat : chaque IA parle une fois
                        debate_logs = game.debate_phase()
                        phase = "vote"
                    elif phase == "vote":
                        # Lancer la phase de vote
                        eliminated, votes = game.voting_phase()
                        game.current_day += 1
                        phase = "debate"

                        # Message de résultat simple
                        vote_summary = ", ".join(
                            f"{name}: {count}" for name, count in votes.items()
                        )
                        debate_logs = [
                            f"{eliminated} est éliminé !",
                            f"Votes: {vote_summary}",
                        ]

                        # Vérifier fin de partie
                        if game.is_game_over():
                            running = False

        # Affichage
        screen.fill((30, 30, 30))

        header_lines = [
            f"Jour: {game.current_day}",
            f"Phase: {phase}",
            f"Loups encore en vie (secret): {game.count_alive_wolves()}",
            "SPACE = continuer | ESC = quitter",
        ]

        y = 20
        for line in header_lines:
            txt_surface = font.render(line, True, (255, 255, 255))
            screen.blit(txt_surface, (20, y))
            y += 30

        # Afficher le log de débat / votes
        for log_line in debate_logs:
            # On coupe la ligne pour éviter de sortir de l'écran
            txt_surface = font.render(log_line[:110], True, (200, 200, 200))
            screen.blit(txt_surface, (20, y))
            y += 24
            if y > SCREEN_HEIGHT - 30:
                break

        pygame.display.flip()
        clock.tick(FPS)

    # Fin de partie : reset mémoires IA
    game.reset_all_llm_memory()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

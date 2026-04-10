"""Small demo for the No Greater Joy night-order engine."""

from botc.game_state import create_game_state, waking_steps_for_night
from botc.scripts.no_greater_joy import choose_five_player_setup


def main() -> None:
    """Print the first-night and other-nights wake order for one setup."""

    setup = choose_five_player_setup()
    game_state = create_game_state(setup)

    print("First night wake order:")
    for step in waking_steps_for_night(game_state, first_night=True):
        print(f"- {step.role_name}: {step.reason}")

    print()
    print("Other nights wake order:")
    for step in waking_steps_for_night(game_state, first_night=False):
        print(f"- {step.role_name}: {step.reason}")


if __name__ == "__main__":
    main()

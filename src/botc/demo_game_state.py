"""Small demo for creating a game state from a generated setup."""

from botc.game_state import assign_hidden_drunk, create_game_state
from botc.scripts.no_greater_joy import choose_five_player_setup


def main() -> None:
    """Print a small game-state snapshot to the terminal."""

    setup = choose_five_player_setup(include_baron=True)
    game_state = create_game_state(setup)

    if setup.needs_drunk_assignment:
        first_townsfolk_seat = next(
            player.seat
            for player in game_state.players
            if player.role_in_bag.category == "Townsfolk"
        )
        assign_hidden_drunk(game_state, first_townsfolk_seat)

    print(f"Script: {game_state.script_name}")
    print(f"Phase: {game_state.phase}")
    print()

    for player in game_state.players:
        reminders = ", ".join(player.reminder_tokens) if player.reminder_tokens else "none"
        print(
            f"Seat {player.seat + 1}: {player.name} | "
            f"{player.role_in_bag.name} ({player.role_in_bag.category}) | "
            f"alive={player.is_alive} | reminders={reminders}"
        )


if __name__ == "__main__":
    main()

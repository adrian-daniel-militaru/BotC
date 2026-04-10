"""Small demo for generating a No Greater Joy 5-player setup."""

from botc.scripts.no_greater_joy import choose_five_player_setup


def main() -> None:
    """Print a random 5-player setup to the terminal."""

    setup = choose_five_player_setup()

    print("Generated No Greater Joy setup:")
    for role in setup.bag_roles:
        print(f"- {role.name} ({role.category})")

    if setup.needs_drunk_assignment:
        print()
        print("Storyteller note: one player must later be assigned as the hidden Drunk.")


if __name__ == "__main__":
    main()

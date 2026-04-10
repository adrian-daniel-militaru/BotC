"""Core game-state models for a small BotC training game."""

from dataclasses import dataclass, field
from typing import Callable

from botc.scripts.no_greater_joy import Role, SetupResult


MISREGISTRATION_TOKENS = {"Is the Drunk", "Is Poisoned"}


@dataclass
class PlayerState:
    """One player's current visible and hidden state."""

    seat: int
    name: str
    role_in_bag: Role
    actual_role: Role
    is_alive: bool = True
    reminder_tokens: list[str] = field(default_factory=list)
    memory: list[str] = field(default_factory=list)


@dataclass
class GameState:
    """A small snapshot of the game during setup or play."""

    script_name: str
    players: list[PlayerState]
    hidden_drunk_seat: int | None = None
    day_number: int = 1
    phase: str = "setup"
    scarlet_woman_became_demon_today: bool = False
    sage_killed_by_demon_tonight: bool = False
    investigator_info_given: bool = False
    investigator_info_summary: str | None = None
    empath_info_given: bool = False
    empath_info_summary: str | None = None
    clockmaker_info_given: bool = False
    clockmaker_info_summary: str | None = None
    imp_kill_resolved: bool = False
    imp_kill_summary: str | None = None


def create_game_state(
    setup: SetupResult,
    player_names: list[str] | None = None,
    script_name: str = "No Greater Joy",
) -> GameState:
    """Turn a generated setup into a seated game state."""

    if player_names is None:
        player_names = [f"Player {index + 1}" for index in range(len(setup.bag_roles))]

    if len(player_names) != len(setup.bag_roles):
        raise ValueError("Player name count must match the number of seats in the setup.")

    players = [
        PlayerState(
            seat=index,
            name=player_names[index],
            role_in_bag=setup.bag_roles[index],
            actual_role=setup.actual_roles[index],
        )
        for index in range(len(setup.bag_roles))
    ]

    return GameState(
        script_name=script_name,
        players=players,
    )


def assign_hidden_drunk(game_state: GameState, seat: int) -> None:
    """Attach the hidden Drunk reminder to a Townsfolk seat."""

    player = game_state.players[seat]
    if player.role_in_bag.category != "Townsfolk":
        raise ValueError("The hidden Drunk can only be assigned to a Townsfolk seat.")

    if game_state.hidden_drunk_seat is not None:
        old_player = game_state.players[game_state.hidden_drunk_seat]
        old_player.reminder_tokens = [
            token for token in old_player.reminder_tokens if token != "Is the Drunk"
        ]

    game_state.hidden_drunk_seat = seat
    if "Is the Drunk" not in player.reminder_tokens:
        player.reminder_tokens.append("Is the Drunk")


def remove_token_from_all_players(game_state: GameState, token_name: str) -> None:
    """Remove a token from every player seat."""

    for player in game_state.players:
        player.reminder_tokens = [token for token in player.reminder_tokens if token != token_name]

    if token_name == "Is the Drunk":
        game_state.hidden_drunk_seat = None


def set_unique_token(game_state: GameState, seat: int, token_name: str) -> None:
    """Place a unique token on one seat, moving it from any previous seat."""

    remove_token_from_all_players(game_state, token_name)
    if token_name not in game_state.players[seat].reminder_tokens:
        game_state.players[seat].reminder_tokens.append(token_name)

    if token_name == "Is the Drunk":
        game_state.hidden_drunk_seat = seat


def role_is_in_play(game_state: GameState, role_name: str) -> bool:
    """Return whether the given actual role is in play."""

    return any(player.actual_role.name == role_name for player in game_state.players)


def shown_role_is_misled(game_state: GameState, role_name: str) -> bool:
    """Return whether a shown role is currently drunk or poisoned."""

    return any(
        player.role_in_bag.name == role_name
        and any(token in MISREGISTRATION_TOKENS for token in player.reminder_tokens)
        for player in game_state.players
    )


def shown_role_is_in_play(game_state: GameState, role_name: str) -> bool:
    """Return whether a shown role currently exists at any seat."""

    return any(player.role_in_bag.name == role_name for player in game_state.players)


def kill_player(game_state: GameState, seat: int) -> None:
    """Mark a player dead and attach the Dead reminder token."""

    player = game_state.players[seat]
    player.is_alive = False


def revive_player(game_state: GameState, seat: int) -> None:
    """Mark a player alive again for testing or correction."""

    player = game_state.players[seat]
    player.is_alive = True


@dataclass(frozen=True)
class NightStep:
    """One role wake or reminder step in the night order."""

    role_name: str
    reason: str
    wake_condition: Callable[[GameState], bool]


def _alive_player_with_role(game_state: GameState, role_name: str) -> bool:
    """Return whether an alive player with the actual role exists."""

    return any(
        player.actual_role.name == role_name and player.is_alive
        for player in game_state.players
    )


def _first_night_skip_evil_info(game_state: GameState) -> bool:
    """Current MVP always skips evil info for 5-6 players without Toymaker."""

    return False


FIRST_NIGHT_ORDER: tuple[NightStep, ...] = (
    NightStep(
        role_name="Evil Info",
        reason="Skipped for 5-6 players without Toymaker.",
        wake_condition=_first_night_skip_evil_info,
    ),
    NightStep(
        role_name="Investigator",
        reason="Learns that one of two players is a particular Minion.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Investigator"),
    ),
    NightStep(
        role_name="Empath",
        reason="Learns how many living neighbors are evil.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Empath"),
    ),
    NightStep(
        role_name="Clockmaker",
        reason="Learns the distance between Demon and Minion.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Clockmaker"),
    ),
    NightStep(
        role_name="Chambermaid",
        reason="Chooses 2 alive players and learns how many woke tonight due to their ability.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Chambermaid"),
    ),
)


OTHER_NIGHTS_ORDER: tuple[NightStep, ...] = (
    NightStep(
        role_name="Scarlet Woman",
        reason="Learns if she became the Demon today.",
        wake_condition=lambda game_state: game_state.scarlet_woman_became_demon_today,
    ),
    NightStep(
        role_name="Imp",
        reason="Chooses a player to kill.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Imp"),
    ),
    NightStep(
        role_name="Sage",
        reason="Wakes only if killed by the Demon tonight.",
        wake_condition=lambda game_state: game_state.sage_killed_by_demon_tonight,
    ),
    NightStep(
        role_name="Empath",
        reason="Learns how many living neighbors are evil.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Empath"),
    ),
    NightStep(
        role_name="Chambermaid",
        reason="Chooses 2 alive players and learns how many woke tonight due to their ability.",
        wake_condition=lambda game_state: _alive_player_with_role(game_state, "Chambermaid"),
    ),
)


def night_order_for_phase(game_state: GameState, first_night: bool) -> tuple[NightStep, ...]:
    """Return the relevant night order list for the current night."""

    return FIRST_NIGHT_ORDER if first_night else OTHER_NIGHTS_ORDER


def waking_steps_for_night(game_state: GameState, first_night: bool) -> list[NightStep]:
    """Return the roles that should actually wake this night."""

    return [
        step
        for step in night_order_for_phase(game_state, first_night)
        if step.wake_condition(game_state)
    ]


def living_neighbor_seats(game_state: GameState, seat: int) -> tuple[int | None, int | None]:
    """Return the nearest living neighbor seats to the left and right."""

    player_count = len(game_state.players)
    if player_count <= 1:
        return (None, None)

    left_seat = None
    right_seat = None

    for offset in range(1, player_count):
        candidate = (seat - offset) % player_count
        if game_state.players[candidate].is_alive:
            left_seat = candidate
            break

    for offset in range(1, player_count):
        candidate = (seat + offset) % player_count
        if game_state.players[candidate].is_alive:
            right_seat = candidate
            break

    return (left_seat, right_seat)


def seat_is_evil(game_state: GameState, seat: int) -> bool:
    """Return whether a seat belongs to an evil player."""

    return game_state.players[seat].actual_role.category in {"Minion", "Demon"}


def clockmaker_distance(game_state: GameState) -> int | None:
    """Return the shortest clockwise/counterclockwise seat distance between Demon and Minion."""

    demon_seat = None
    minion_seat = None
    for player in game_state.players:
        if player.actual_role.category == "Demon":
            demon_seat = player.seat
        elif player.actual_role.category == "Minion":
            minion_seat = player.seat

    if demon_seat is None or minion_seat is None:
        return None

    seat_count = len(game_state.players)
    raw_distance = abs(demon_seat - minion_seat)
    return min(raw_distance, seat_count - raw_distance)


def max_clockmaker_distance(game_state: GameState) -> int:
    """Return the largest sensible Clockmaker value for the current player count."""

    return max(1, len(game_state.players) // 2)

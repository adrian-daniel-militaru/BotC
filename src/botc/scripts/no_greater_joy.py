"""Role definitions for the No Greater Joy Teensyville script."""

import random
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Role:
    """A single role that can appear in a Blood on the Clocktower script."""

    name: str
    category: str


@dataclass(frozen=True)
class SetupResult:
    """A generated setup plus any hidden storyteller work still to do."""

    bag_roles: tuple[Role, ...]
    actual_roles: tuple[Role, ...]
    needs_drunk_assignment: bool = False


NO_GREATER_JOY_NAME: Final[str] = "No Greater Joy"

FIVE_PLAYER_SETUP: Final[dict[str, int]] = {
    "Townsfolk": 3,
    "Outsider": 0,
    "Minion": 1,
    "Demon": 1,
}

FIVE_PLAYER_SETUP_WITH_BARON: Final[dict[str, int]] = {
    "Townsfolk": 1,
    "Outsider": 2,
    "Minion": 1,
    "Demon": 1,
}

NO_GREATER_JOY_ROLES: Final[tuple[Role, ...]] = (
    Role(name="Clockmaker", category="Townsfolk"),
    Role(name="Investigator", category="Townsfolk"),
    Role(name="Empath", category="Townsfolk"),
    Role(name="Chambermaid", category="Townsfolk"),
    Role(name="Artist", category="Townsfolk"),
    Role(name="Sage", category="Townsfolk"),
    Role(name="Drunk", category="Outsider"),
    Role(name="Klutz", category="Outsider"),
    Role(name="Scarlet Woman", category="Minion"),
    Role(name="Baron", category="Minion"),
    Role(name="Imp", category="Demon"),
)

ROLE_BY_NAME: Final[dict[str, Role]] = {role.name: role for role in NO_GREATER_JOY_ROLES}

if len(ROLE_BY_NAME) != len(NO_GREATER_JOY_ROLES):
    raise ValueError("No Greater Joy role list contains duplicate role names.")


def _roles_in_category(category: str) -> list[Role]:
    """Return all No Greater Joy roles in the requested category."""

    return [role for role in NO_GREATER_JOY_ROLES if role.category == category]


def choose_five_player_setup(
    include_baron: bool | None = None,
    rng: random.Random | None = None,
) -> SetupResult:
    """Build a legal random 5-player No Greater Joy setup.

    If ``include_baron`` is:
    - ``True``: the minion will be Baron and the setup will include 2 Outsiders
    - ``False``: the minion will be Scarlet Woman and the setup will include 0 Outsiders
    - ``None``: Baron is chosen randomly between the two legal minions

    If ``Drunk`` is selected, it is replaced in the bag with a random Townsfolk.
    The returned setup records that the storyteller still needs to choose which
    player is actually the Drunk later.
    """

    if rng is None:
        rng = random.Random()

    if include_baron is None:
        include_baron = rng.choice([True, False])

    minion_name = "Baron" if include_baron else "Scarlet Woman"
    setup_counts = FIVE_PLAYER_SETUP_WITH_BARON if include_baron else FIVE_PLAYER_SETUP

    chosen_roles: list[Role] = []
    chosen_roles.extend(rng.sample(_roles_in_category("Townsfolk"), setup_counts["Townsfolk"]))
    chosen_roles.extend(rng.sample(_roles_in_category("Outsider"), setup_counts["Outsider"]))
    chosen_roles.append(ROLE_BY_NAME[minion_name])
    chosen_roles.extend(rng.sample(_roles_in_category("Demon"), setup_counts["Demon"]))

    slots = [{"bag_role": role, "actual_role": role} for role in chosen_roles]

    needs_drunk_assignment = any(slot["actual_role"].name == "Drunk" for slot in slots)
    if needs_drunk_assignment:
        townsfolk_already_in_bag = {
            slot["bag_role"].name for slot in slots if slot["bag_role"].category == "Townsfolk"
        }
        available_shown_townsfolk = [
            role
            for role in _roles_in_category("Townsfolk")
            if role.name not in townsfolk_already_in_bag
        ]
        shown_townsfolk = rng.choice(available_shown_townsfolk)
        for slot in slots:
            if slot["actual_role"].name == "Drunk":
                slot["bag_role"] = shown_townsfolk

    rng.shuffle(slots)
    return SetupResult(
        bag_roles=tuple(slot["bag_role"] for slot in slots),
        actual_roles=tuple(slot["actual_role"] for slot in slots),
        needs_drunk_assignment=needs_drunk_assignment,
    )

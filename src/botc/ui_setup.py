"""Simple Tkinter UI for testing No Greater Joy setup generation."""

import math
import tkinter as tk
from tkinter import ttk

from botc.game_state import (
    GameState,
    assign_hidden_drunk,
    clockmaker_distance,
    create_game_state,
    kill_player,
    living_neighbor_seats,
    max_clockmaker_distance,
    remove_token_from_all_players,
    role_is_in_play,
    revive_player,
    seat_is_evil,
    set_unique_token,
    shown_role_is_in_play,
    shown_role_is_misled,
)
from botc.scripts.no_greater_joy import SetupResult, choose_five_player_setup


class SetupApp:
    """Small desktop app for generating and viewing 5-player setups."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BotC Setup Tester")
        self.root.geometry("980x620")
        self.root.minsize(900, 560)

        self.force_baron = tk.BooleanVar(value=False)
        self.status_text = tk.StringVar(value="Click 'Generate setup' to begin.")
        self.selected_player_index: int | None = None
        self.current_setup: SetupResult | None = None
        self.game_state: GameState | None = None
        self.player_name_vars: list[tk.StringVar] = []
        self.selected_token_name: str | None = None
        self.dragging_token_name: str | None = None
        self.dragging_from_player_index: int | None = None
        self.drag_preview_items: tuple[int, int] | None = None
        self.seat_positions: dict[int, tuple[float, float, float]] = {}
        self.phase_button_text = tk.StringVar(value="Start First Night")
        self.investigator_minion_choice = tk.StringVar(value="")
        self.empath_choice = tk.StringVar(value="")
        self.clockmaker_choice = tk.StringVar(value="")
        self.clockmaker_button_values: list[str] = []

        self._build_layout()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(container, text="No Greater Joy Setup Tester")
        title.pack(anchor="w")

        description = ttk.Label(
            container,
            text="Generate a legal 5-player setup and inspect the bag roles.",
        )
        description.pack(anchor="w", pady=(4, 12))

        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(0, 12))

        ttk.Checkbutton(
            controls,
            text="Force Baron setup",
            variable=self.force_baron,
        ).pack(side="left")

        ttk.Button(
            controls,
            text="Generate setup",
            command=self.generate_setup,
        ).pack(side="right")

        content = ttk.Frame(container)
        content.pack(fill="both", expand=True)

        left_panel = ttk.Frame(content)
        left_panel.pack(side="left", fill="both", expand=True)

        right_panel = ttk.Frame(content, width=280)
        right_panel.pack(side="right", fill="y", padx=(16, 0))
        right_panel.pack_propagate(False)

        ttk.Label(left_panel, text="Player circle").pack(anchor="w")

        self.circle_canvas = tk.Canvas(
            left_panel,
            width=700,
            height=420,
            bg="#f7f3e9",
            highlightthickness=1,
            highlightbackground="#c9bda8",
        )
        self.circle_canvas.pack(fill="both", expand=True)
        self.circle_canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.circle_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.circle_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        ttk.Label(right_panel, text="Player names").pack(anchor="w")

        self.names_frame = ttk.Frame(right_panel)
        self.names_frame.pack(fill="x", pady=(6, 16))

        self.phase_button = ttk.Button(
            right_panel,
            textvariable=self.phase_button_text,
            command=self.advance_phase,
        )
        self.phase_button.pack(fill="x", pady=(0, 8))

        self.execute_button = ttk.Button(
            right_panel,
            text="Execute Selected Player",
            command=self.execute_selected_player,
        )
        self.execute_button.pack(fill="x", pady=(0, 8))

        ttk.Button(
            right_panel,
            text="Clear selected reminder",
            command=self.clear_selected_reminder,
        ).pack(fill="x")

        ttk.Label(right_panel, text="Night order").pack(anchor="w", pady=(16, 0))
        self.night_order_list = tk.Listbox(right_panel, height=10, exportselection=False)
        self.night_order_list.pack(fill="both", expand=True, pady=(6, 0))

        self.investigator_panel = ttk.Frame(right_panel)
        ttk.Label(self.investigator_panel, text="Investigator info").pack(anchor="w", pady=(16, 0))
        self.investigator_info_text = tk.StringVar(value="No Investigator info to assign right now.")
        ttk.Label(
            self.investigator_panel,
            textvariable=self.investigator_info_text,
            wraplength=250,
            justify="left",
        ).pack(fill="x", pady=(6, 6))
        self.confirm_investigator_button = ttk.Button(
            self.investigator_panel,
            text="Confirm Player Info",
            command=self.confirm_investigator_info,
        )
        self.confirm_investigator_button.pack(fill="x")
        self.investigator_minion_picker = ttk.Combobox(
            self.investigator_panel,
            textvariable=self.investigator_minion_choice,
            state="disabled",
            values=("Baron", "Scarlet Woman"),
        )
        self.investigator_minion_picker.pack(fill="x", pady=(6, 0))
        self.investigator_panel.pack(fill="x")

        self.imp_panel = ttk.Frame(right_panel)
        ttk.Label(self.imp_panel, text="Imp kill").pack(anchor="w", pady=(16, 0))
        self.imp_info_text = tk.StringVar(value="No Imp action to resolve right now.")
        ttk.Label(
            self.imp_panel,
            textvariable=self.imp_info_text,
            wraplength=250,
            justify="left",
        ).pack(fill="x", pady=(6, 6))
        self.confirm_imp_button = ttk.Button(
            self.imp_panel,
            text="Confirm Player Info",
            command=self.confirm_imp_kill,
        )
        self.confirm_imp_button.pack(fill="x")
        self.imp_panel.pack(fill="x")

        self.empath_panel = ttk.Frame(right_panel)
        ttk.Label(self.empath_panel, text="Empath info").pack(anchor="w", pady=(16, 0))
        self.empath_info_text = tk.StringVar(value="No Empath info to assign right now.")
        ttk.Label(
            self.empath_panel,
            textvariable=self.empath_info_text,
            wraplength=250,
            justify="left",
        ).pack(fill="x", pady=(6, 6))
        self.empath_buttons_frame = ttk.Frame(self.empath_panel)
        self.empath_buttons_frame.pack(fill="x")
        self.empath_buttons: list[tk.Button] = []
        for value in ("0", "1", "2"):
            button = tk.Button(
                self.empath_buttons_frame,
                text=value,
                command=lambda choice=value: self.select_empath_value(choice),
                relief="raised",
                bd=2,
                bg="#f3efe6",
                activebackground="#e2d4b7",
            )
            button.pack(side="left", expand=True, fill="x", padx=2)
            self.empath_buttons.append(button)
        self.confirm_empath_button = ttk.Button(
            self.empath_panel,
            text="Confirm Player Info",
            command=self.confirm_empath_info,
        )
        self.confirm_empath_button.pack(fill="x", pady=(6, 0))
        self.empath_panel.pack(fill="x")

        self.clockmaker_panel = ttk.Frame(right_panel)
        ttk.Label(self.clockmaker_panel, text="Clockmaker info").pack(anchor="w", pady=(16, 0))
        self.clockmaker_info_text = tk.StringVar(value="No Clockmaker info to assign right now.")
        ttk.Label(
            self.clockmaker_panel,
            textvariable=self.clockmaker_info_text,
            wraplength=250,
            justify="left",
        ).pack(fill="x", pady=(6, 6))
        self.clockmaker_buttons_frame = ttk.Frame(self.clockmaker_panel)
        self.clockmaker_buttons_frame.pack(fill="x")
        self.clockmaker_buttons: list[tk.Button] = []
        self.confirm_clockmaker_button = ttk.Button(
            self.clockmaker_panel,
            text="Confirm Player Info",
            command=self.confirm_clockmaker_info,
        )
        self.confirm_clockmaker_button.pack(fill="x", pady=(6, 0))
        self.clockmaker_panel.pack(fill="x")

        ttk.Label(right_panel, text="Selected player memory").pack(anchor="w", pady=(16, 0))
        self.memory_text = tk.StringVar(value="Select a player to inspect their memory.")
        ttk.Label(
            right_panel,
            textvariable=self.memory_text,
            wraplength=250,
            justify="left",
        ).pack(fill="x", pady=(6, 0))

        ttk.Label(
            container,
            textvariable=self.status_text,
            wraplength=940,
            justify="left",
        ).pack(fill="x", pady=(12, 0))

    def generate_setup(self) -> None:
        """Create and display a fresh random setup."""

        include_baron = True if self.force_baron.get() else None
        setup = choose_five_player_setup(include_baron=include_baron)
        self.selected_player_index = None
        self.selected_token_name = None
        self._show_setup(setup)

    def _show_setup(self, setup: SetupResult) -> None:
        """Render the generated setup in the player circle and status area."""

        self.current_setup = setup
        self.game_state = create_game_state(setup)
        self.player_name_vars = [tk.StringVar(value=player.name) for player in self.game_state.players]
        self._rebuild_clockmaker_buttons()
        self._build_player_name_inputs()
        self._refresh_night_order_panel()
        self._refresh_investigator_panel()
        self._refresh_imp_panel()
        self._refresh_empath_panel()
        self._refresh_clockmaker_panel()
        self._refresh_info_panel_visibility()
        self._refresh_phase_button()
        self._refresh_memory_panel()
        self._draw_player_circle()
        self._update_status_text()

    def _draw_player_circle(self) -> None:
        """Draw the generated roles as seats around a circle."""

        if self.current_setup is None or self.game_state is None:
            return

        self.circle_canvas.delete("all")
        self.seat_positions = {}

        canvas_width = int(self.circle_canvas.winfo_width() or 700)
        canvas_height = int(self.circle_canvas.winfo_height() or 420)
        interactive_width = canvas_width * 0.72
        center_x = interactive_width / 2
        center_y = canvas_height / 2
        radius = min(interactive_width, canvas_height) * 0.35
        seat_radius = 52
        show_first_night_markers = self.game_state.phase in {"setup", "first_night"}
        first_night_markers = self._wake_order_markers(first_night=True) if show_first_night_markers else {}
        other_night_markers = (
            self._wake_order_markers(first_night=False)
            if self.game_state.phase not in {"setup", "first_night"}
            else {}
        )

        self.circle_canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline="#d5cab8",
            width=2,
        )

        role_count = len(self.game_state.players)
        for index, player in enumerate(self.game_state.players):
            angle = (-math.pi / 2) + (2 * math.pi * index / role_count)
            x = center_x + math.cos(angle) * radius
            y = center_y + math.sin(angle) * radius

            outline = "#1e5eff" if self.selected_player_index == index else "#3b2f2f"
            outline_width = 4 if self.selected_player_index == index else 2

            self.circle_canvas.create_oval(
                x - seat_radius,
                y - seat_radius,
                x + seat_radius,
                y + seat_radius,
                fill=self._seat_color(player.role_in_bag.category),
                outline=outline,
                width=outline_width,
                tags=(f"seat-{index}", "seat"),
            )
            self.seat_positions[index] = (x, y, seat_radius)
            if not player.is_alive:
                self.circle_canvas.create_line(
                    x - seat_radius + 10,
                    y - seat_radius + 10,
                    x + seat_radius - 10,
                    y + seat_radius - 10,
                    fill="#5c4a4a",
                    width=3,
                )
                self.circle_canvas.create_line(
                    x - seat_radius + 10,
                    y + seat_radius - 10,
                    x + seat_radius - 10,
                    y - seat_radius + 10,
                    fill="#5c4a4a",
                    width=3,
                )

            self.circle_canvas.create_text(
                x,
                y - 10,
                text=player.name,
                font=("Segoe UI", 9, "bold"),
                width=96,
                tags=(f"seat-{index}", "seat"),
            )
            self.circle_canvas.create_text(
                x,
                y + 13,
                text=player.role_in_bag.name,
                width=86,
                justify="center",
                font=("Segoe UI", 9),
                tags=(f"seat-{index}", "seat"),
            )

            if index in first_night_markers:
                self._draw_wake_marker(
                    x=x - seat_radius - 18,
                    y=y,
                    number=first_night_markers[index],
                    fill="#d8ecff",
                    outline="#2f6fb5",
                    text_color="#184a82",
                )

            if index in other_night_markers:
                self._draw_wake_marker(
                    x=x + seat_radius + 18,
                    y=y,
                    number=other_night_markers[index],
                    fill="#ffd9d9",
                    outline="#b54848",
                    text_color="#7e1d1d",
                )

            for token_index, token_text in enumerate(player.reminder_tokens):
                reminder_x = center_x + math.cos(angle) * (radius - 88 - token_index * 30)
                reminder_y = center_y + math.sin(angle) * (radius - 88 - token_index * 30)
                self.circle_canvas.create_oval(
                    reminder_x - 22,
                    reminder_y - 22,
                    reminder_x + 22,
                    reminder_y + 22,
                    fill="#efe3b1",
                    outline="#7a5f1e",
                    width=2,
                    tags=(f"reminder-{index}-{token_index}", f"token-{token_text}", "reminder"),
                )
                self.circle_canvas.create_text(
                    reminder_x,
                    reminder_y,
                    text=token_text,
                    width=38,
                    justify="center",
                    font=("Segoe UI", 7, "bold"),
                    tags=(f"reminder-{index}-{token_index}", f"token-{token_text}", "reminder"),
                )

        self._draw_token_palette(canvas_width)

    def _draw_wake_marker(
        self,
        x: float,
        y: float,
        number: int,
        fill: str,
        outline: str,
        text_color: str,
    ) -> None:
        """Draw one wake-order marker next to a player seat."""

        radius = 14
        self.circle_canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            outline=outline,
            width=2,
        )
        self.circle_canvas.create_text(
            x,
            y,
            text=str(number),
            fill=text_color,
            font=("Segoe UI", 9, "bold"),
        )

    def _draw_token_palette(self, canvas_width: int) -> None:
        """Draw round draggable reminder tokens on the right side of the canvas."""

        palette_left = canvas_width * 0.76
        self.circle_canvas.create_text(
            palette_left,
            28,
            text="Reminder tokens",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )

        for index, token_name in enumerate(self._available_token_names()):
            token_x = palette_left + 52
            token_y = 95 + index * 86
            token_radius = 34
            outline = "#1e5eff" if self.selected_token_name == token_name else "#7a5f1e"
            width = 3 if self.selected_token_name == token_name else 2
            self.circle_canvas.create_oval(
                token_x - token_radius,
                token_y - token_radius,
                token_x + token_radius,
                token_y + token_radius,
                fill="#f6eed1",
                outline=outline,
                width=width,
                tags=(f"palette-{token_name}", "palette-token"),
            )
            self.circle_canvas.create_text(
                token_x,
                token_y,
                text=token_name,
                width=58,
                justify="center",
                font=("Segoe UI", 7, "bold"),
                tags=(f"palette-{token_name}", "palette-token"),
            )

    def on_canvas_press(self, event: tk.Event) -> None:
        """Start selecting or dragging seats and tokens."""

        if self.game_state is None:
            return

        clicked_items = self.circle_canvas.find_overlapping(
            event.x - 1,
            event.y - 1,
            event.x + 1,
            event.y + 1,
        )
        if not clicked_items:
            return

        tags = self.circle_canvas.gettags(clicked_items[-1])
        palette_tags = [tag for tag in tags if tag.startswith("palette-")]
        reminder_token_tags = [tag for tag in tags if tag.startswith("token-")]
        seat_tags = [tag for tag in tags if tag.startswith("seat-")]

        if palette_tags:
            token_name = palette_tags[0].replace("palette-", "", 1)
            self.selected_token_name = token_name
            self.dragging_token_name = token_name
            self.dragging_from_player_index = None
            self._draw_player_circle()
            self._create_drag_preview(event.x, event.y, token_name)
            self._update_status_text()
            return

        if "reminder" in tags and reminder_token_tags:
            token_name = reminder_token_tags[0].replace("token-", "", 1)
            self.selected_token_name = token_name
            self.dragging_token_name = token_name
            self.dragging_from_player_index = self._player_index_from_tags(tags)
            if self._token_is_unique(token_name):
                remove_token_from_all_players(self.game_state, token_name)
            elif self.dragging_from_player_index is not None:
                player = self.game_state.players[self.dragging_from_player_index]
                player.reminder_tokens = [token for token in player.reminder_tokens if token != token_name]
            self._draw_player_circle()
            self._create_drag_preview(event.x, event.y, token_name)
            self._update_status_text()
            return

        if seat_tags:
            self.selected_player_index = int(seat_tags[0].split("-")[1])
            self._refresh_memory_panel()
            self._refresh_investigator_panel()
            self._refresh_imp_panel()
            self._refresh_empath_panel()
            self._refresh_clockmaker_panel()
            self._update_status_text()
            self._draw_player_circle()

    def on_canvas_drag(self, event: tk.Event) -> None:
        """Move the drag preview while a token is being dragged."""

        if self.dragging_token_name is None:
            return

        self._move_drag_preview(event.x, event.y)
        self.status_text.set(f"Dragging '{self.dragging_token_name}' onto a player seat.")

    def on_canvas_release(self, event: tk.Event) -> None:
        """Drop a dragged token onto a legal seat when possible."""

        if self.dragging_token_name is None or self.game_state is None:
            return

        target_seat = self._seat_at_point(event.x, event.y)
        token_name = self.dragging_token_name
        self._clear_drag_preview()
        self.dragging_token_name = None

        if target_seat is not None:
            self.selected_player_index = target_seat
            if self._place_token_on_player(token_name, target_seat):
                self.selected_token_name = token_name
            else:
                if self.dragging_from_player_index is not None:
                    self._restore_dragged_token(token_name, self.dragging_from_player_index)
                    self.selected_player_index = self.dragging_from_player_index
                self.status_text.set(f"'{token_name}' cannot be placed on that seat.")
        elif self.dragging_from_player_index is not None:
            self._restore_dragged_token(token_name, self.dragging_from_player_index)
            self.selected_player_index = self.dragging_from_player_index

        self.dragging_from_player_index = None
        self._refresh_memory_panel()
        self._refresh_investigator_panel()
        self._refresh_imp_panel()
        self._refresh_empath_panel()
        self._refresh_clockmaker_panel()
        self._draw_player_circle()
        self._update_status_text()

    def _build_player_name_inputs(self) -> None:
        """Create editable player name fields for the current setup."""

        for child in self.names_frame.winfo_children():
            child.destroy()

        for index, name_var in enumerate(self.player_name_vars):
            row = ttk.Frame(self.names_frame)
            row.pack(fill="x", pady=2)

            ttk.Label(row, text=f"Seat {index + 1}", width=7).pack(side="left")
            entry = ttk.Entry(row, textvariable=name_var)
            entry.pack(side="left", fill="x", expand=True)
            entry.bind("<KeyRelease>", self.on_name_change)

    def on_name_change(self, event: tk.Event) -> None:
        """Refresh the player circle when a seat name changes."""

        if self.game_state is None:
            return

        for index, name_var in enumerate(self.player_name_vars):
            self.game_state.players[index].name = name_var.get()

        self._refresh_memory_panel()
        self._draw_player_circle()
        self._update_status_text()

    def clear_selected_reminder(self) -> None:
        """Remove the active reminder from the selected player, if possible."""

        if self.selected_player_index is None or self.game_state is None:
            self.status_text.set("Select a player seat first.")
            return

        player = self.game_state.players[self.selected_player_index]
        if not player.reminder_tokens:
            self.status_text.set("The selected player has no removable reminder token yet.")
            return

        token_to_remove = player.reminder_tokens[-1]
        player.reminder_tokens.pop()
        if self._token_is_unique(token_to_remove):
            remove_token_from_all_players(self.game_state, token_to_remove)
        self.selected_token_name = token_to_remove
        self._refresh_night_order_panel()
        self._refresh_investigator_panel()
        self._refresh_imp_panel()
        self._refresh_empath_panel()
        self._refresh_clockmaker_panel()
        self._refresh_phase_button()
        self._refresh_memory_panel()
        self._draw_player_circle()
        self._update_status_text()

    def _available_token_names(self) -> list[str]:
        """Return the reminder tokens that should be available right now."""

        if self.game_state is None:
            return []

        tokens: list[str] = []
        if self.current_setup and self.current_setup.needs_drunk_assignment:
            tokens.append("Is the Drunk")
        if shown_role_is_in_play(self.game_state, "Investigator"):
            tokens.extend(["Correct Minion", "Wrong Minion"])
        if role_is_in_play(self.game_state, "Imp"):
            tokens.append("Dead")
        if role_is_in_play(self.game_state, "Scarlet Woman"):
            tokens.append("Is the Demon")
        return tokens

    @staticmethod
    def _token_is_unique(token_name: str) -> bool:
        """Return whether only one copy of the token should exist on the board."""

        return token_name in {"Is the Drunk", "Correct Minion", "Wrong Minion", "Is the Demon"}

    def _place_token_on_player(self, token_name: str, player_index: int) -> bool:
        """Place the given reminder token on a player if the seat is legal."""

        if self.game_state is None:
            return False

        player = self.game_state.players[player_index]

        if token_name == "Is the Drunk":
            if player.role_in_bag.category != "Townsfolk":
                return False
            assign_hidden_drunk(self.game_state, player_index)
            return True

        if token_name == "Correct Minion":
            investigator_is_misled = shown_role_is_misled(self.game_state, "Investigator")
            if not investigator_is_misled and player.actual_role.category != "Minion":
                return False
            set_unique_token(self.game_state, player_index, token_name)
            return True

        if token_name == "Wrong Minion":
            investigator_is_misled = shown_role_is_misled(self.game_state, "Investigator")
            if not investigator_is_misled and player.actual_role.category == "Minion":
                return False
            set_unique_token(self.game_state, player_index, token_name)
            return True

        if token_name == "Dead":
            if token_name not in player.reminder_tokens:
                player.reminder_tokens.append(token_name)
            return True

        if token_name == "Is the Demon":
            if player.actual_role.name != "Scarlet Woman":
                return False
            set_unique_token(self.game_state, player_index, token_name)
            return True

        return False

    def _restore_dragged_token(self, token_name: str, player_index: int) -> None:
        """Put a dragged token back where it came from after an invalid drop."""

        if self.game_state is None:
            return

        if token_name == "Is the Drunk":
            assign_hidden_drunk(self.game_state, player_index)
        elif token_name in {"Correct Minion", "Wrong Minion", "Is the Demon"}:
            set_unique_token(self.game_state, player_index, token_name)
        elif token_name not in self.game_state.players[player_index].reminder_tokens:
            self.game_state.players[player_index].reminder_tokens.append(token_name)

    def _create_drag_preview(self, x: float, y: float, token_name: str) -> None:
        """Create a floating token preview on the canvas."""

        self._clear_drag_preview()
        oval_id = self.circle_canvas.create_oval(
            x - 22,
            y - 22,
            x + 22,
            y + 22,
            fill="#efe3b1",
            outline="#7a5f1e",
            width=2,
            dash=(3, 2),
        )
        text_id = self.circle_canvas.create_text(
            x,
            y,
            text=token_name,
            width=42,
            justify="center",
            font=("Segoe UI", 7, "bold"),
        )
        self.drag_preview_items = (oval_id, text_id)

    def _move_drag_preview(self, x: float, y: float) -> None:
        """Move the floating drag preview token."""

        if self.drag_preview_items is None:
            return

        oval_id, text_id = self.drag_preview_items
        self.circle_canvas.coords(oval_id, x - 22, y - 22, x + 22, y + 22)
        self.circle_canvas.coords(text_id, x, y)

    def _clear_drag_preview(self) -> None:
        """Remove the floating drag preview token."""

        if self.drag_preview_items is None:
            return

        for item_id in self.drag_preview_items:
            self.circle_canvas.delete(item_id)
        self.drag_preview_items = None

    def _seat_at_point(self, x: float, y: float) -> int | None:
        """Return the player seat under the given point, if any."""

        for player_index, (seat_x, seat_y, seat_radius) in self.seat_positions.items():
            if (x - seat_x) ** 2 + (y - seat_y) ** 2 <= seat_radius**2:
                return player_index
        return None

    @staticmethod
    def _player_index_from_tags(tags: tuple[str, ...]) -> int | None:
        """Extract a player index from a canvas tag tuple."""

        reminder_tags = [tag for tag in tags if tag.startswith("reminder-")]
        if not reminder_tags:
            return None

        parts = reminder_tags[0].split("-")
        return int(parts[1]) if len(parts) >= 3 else None

    def _seat_with_token(self, token_name: str) -> int | None:
        """Return the seat currently holding a given reminder token."""

        if self.game_state is None:
            return None

        for player in self.game_state.players:
            if token_name in player.reminder_tokens:
                return player.seat
        return None

    def _refresh_memory_panel(self) -> None:
        """Show the selected player's stored memory for debugging and simulation."""

        if self.game_state is None or self.selected_player_index is None:
            self.memory_text.set("Select a player to inspect their memory.")
            return

        player = self.game_state.players[self.selected_player_index]
        if not player.memory:
            self.memory_text.set(f"{player.name} has no stored memory yet.")
            return

        self.memory_text.set("\n".join(f"- {entry}" for entry in player.memory))

    @staticmethod
    def _seat_color(category: str) -> str:
        """Return a distinct seat color for each role category."""

        colors = {
            "Townsfolk": "#d7e8ba",
            "Outsider": "#f2d9a0",
            "Minion": "#e7b0a8",
            "Demon": "#d98c8c",
        }
        return colors.get(category, "#dddddd")

    def _update_status_text(self) -> None:
        """Update the status area with the current selection and task state."""

        if self.current_setup is None or self.game_state is None:
            self.status_text.set("Click 'Generate setup' to begin.")
            return

        messages: list[str] = []

        if self.selected_player_index is not None:
            player = self.game_state.players[self.selected_player_index]
            messages.append(
                f"Selected {player.name}: {player.role_in_bag.name} ({player.role_in_bag.category})."
            )
        else:
            messages.append("Select a player seat to inspect it.")

        if self.selected_token_name is not None:
            messages.append(f"Selected token: {self.selected_token_name}.")
        elif self._available_token_names():
            messages.append("Drag a reminder token from the right onto a player seat.")

        if self.current_setup.needs_drunk_assignment:
            if self.game_state.hidden_drunk_seat is None:
                messages.append("Reminder pending: place 'Is the Drunk' on a Townsfolk seat.")
            else:
                drunk_name = self.game_state.players[self.game_state.hidden_drunk_seat].name
                messages.append(f"'Is the Drunk' is currently attached to {drunk_name}.")

        if self.game_state.phase == "setup":
            phase_label = "Setup"
        elif self.game_state.phase == "first_night":
            phase_label = "First Night"
        elif self.game_state.phase == "first_day":
            phase_label = "First Day"
        elif self.game_state.phase == "other_night":
            phase_label = self._current_night_label()
        elif self.game_state.phase == "other_day":
            phase_label = f"Day {self.game_state.day_number + 1}"
        else:
            phase_label = self.game_state.phase

        messages.append(f"Current phase: {phase_label}.")

        if self.selected_token_name == "Correct Minion":
            if shown_role_is_misled(self.game_state, "Investigator"):
                messages.append("The shown Investigator is drunk or poisoned, so 'Correct Minion' can be placed anywhere.")
            else:
                messages.append("Place 'Correct Minion' on the actual minion seat.")
        elif self.selected_token_name == "Wrong Minion":
            if shown_role_is_misled(self.game_state, "Investigator"):
                messages.append("The shown Investigator is drunk or poisoned, so 'Wrong Minion' can be placed anywhere.")
            else:
                messages.append("Place 'Wrong Minion' on any seat that is not the minion.")
        elif self.selected_token_name == "Dead":
            messages.append("Place 'Dead' on any seat that dies.")
        elif self.selected_token_name == "Is the Demon":
            messages.append("Place 'Is the Demon' only on the Scarlet Woman.")

        self.status_text.set(" ".join(messages))

    def advance_phase(self) -> None:
        """Advance the game through setup, nights, and days with one button."""

        if self.game_state is None:
            return

        next_phase = self.game_state.phase
        if self.game_state.phase == "setup":
            next_phase = "first_night"
        elif self.game_state.phase == "first_night":
            next_phase = "first_day"
        elif self.game_state.phase == "first_day":
            next_phase = "other_night"
        elif self.game_state.phase == "other_night":
            next_phase = "other_day"
        elif self.game_state.phase == "other_day":
            self.game_state.day_number += 1
            next_phase = "other_night"

        self.game_state.phase = next_phase
        if next_phase in {"first_night", "other_night"}:
            self.game_state.empath_info_given = False
            self.game_state.empath_info_summary = None
        if next_phase == "other_night":
            self.game_state.imp_kill_resolved = False
            self.game_state.imp_kill_summary = None

        self._refresh_night_order_panel()
        self._refresh_investigator_panel()
        self._refresh_imp_panel()
        self._refresh_empath_panel()
        self._refresh_info_panel_visibility()
        self._refresh_phase_button()
        self._draw_player_circle()
        self._update_status_text()

    def execute_selected_player(self) -> None:
        """Execute the currently selected player during a day phase."""

        if self.game_state is None or self.selected_player_index is None:
            self.status_text.set("Select a player seat first.")
            return

        if self.game_state.phase not in {"first_day", "other_day"}:
            self.status_text.set("You can only execute a player during a day phase.")
            return

        player = self.game_state.players[self.selected_player_index]
        if player.is_alive:
            kill_player(self.game_state, self.selected_player_index)
        else:
            revive_player(self.game_state, self.selected_player_index)
        self._refresh_night_order_panel()
        self._refresh_investigator_panel()
        self._refresh_imp_panel()
        self._refresh_empath_panel()
        self._refresh_phase_button()
        self._draw_player_circle()
        self._update_status_text()

    def _refresh_night_order_panel(self) -> None:
        """Show the current wake order in the side panel."""

        self.night_order_list.delete(0, tk.END)

        if self.game_state is None:
            return

        if self.game_state.phase == "first_night":
            active_steps = self._display_steps_for_phase(first_night=True)
            header = f"Current: {self._current_night_label()}"
        elif self.game_state.phase == "setup":
            active_steps = self._display_steps_for_phase(first_night=True)
            header = "Preview: First Night"
        elif self.game_state.phase == "first_day":
            active_steps = []
            header = "Current: First Day"
        elif self.game_state.phase == "other_day":
            active_steps = []
            header = f"Current: Day {self.game_state.day_number + 1}"
        else:
            active_steps = self._display_steps_for_phase(first_night=False)
            header = f"Current: {self._current_night_label()}"

        self.night_order_list.insert(tk.END, header)
        self.night_order_list.insert(tk.END, "")
        for index, step_name in enumerate(active_steps, start=1):
            suffix = ""
            if step_name == "Investigator" and self.game_state.investigator_info_given:
                suffix = " [done]"
            elif step_name == "Imp" and self.game_state.imp_kill_resolved:
                suffix = " [done]"
            elif step_name == "Empath" and self.game_state.empath_info_given:
                suffix = " [done]"
            elif step_name == "Clockmaker" and self.game_state.clockmaker_info_given:
                suffix = " [done]"
            self.night_order_list.insert(tk.END, f"{index}. {step_name}{suffix}")

    def _active_info_role(self) -> str | None:
        """Return the next information role that still needs handling."""

        if self.game_state is None:
            return None

        if (
            self.game_state.phase == "first_night"
            and shown_role_is_in_play(self.game_state, "Investigator")
            and not self.game_state.investigator_info_given
        ):
            return "Investigator"

        if (
            self.game_state.phase == "other_night"
            and role_is_in_play(self.game_state, "Imp")
            and not self.game_state.imp_kill_resolved
        ):
            return "Imp"

        if (
            self.game_state.phase in {"first_night", "other_night"}
            and shown_role_is_in_play(self.game_state, "Empath")
            and not self.game_state.empath_info_given
        ):
            return "Empath"

        if (
            self.game_state.phase == "first_night"
            and shown_role_is_in_play(self.game_state, "Clockmaker")
            and not self.game_state.clockmaker_info_given
        ):
            return "Clockmaker"
        return None

    def _refresh_info_panel_visibility(self) -> None:
        """Show only the current first-night info panel."""

        active_role = self._active_info_role()

        if active_role == "Investigator":
            if not self.investigator_panel.winfo_manager():
                self.investigator_panel.pack(fill="x")
            if self.imp_panel.winfo_manager():
                self.imp_panel.pack_forget()
            if self.empath_panel.winfo_manager():
                self.empath_panel.pack_forget()
            if self.clockmaker_panel.winfo_manager():
                self.clockmaker_panel.pack_forget()
        elif active_role == "Imp":
            if self.investigator_panel.winfo_manager():
                self.investigator_panel.pack_forget()
            if not self.imp_panel.winfo_manager():
                self.imp_panel.pack(fill="x")
            if self.empath_panel.winfo_manager():
                self.empath_panel.pack_forget()
            if self.clockmaker_panel.winfo_manager():
                self.clockmaker_panel.pack_forget()
        elif active_role == "Empath":
            if self.investigator_panel.winfo_manager():
                self.investigator_panel.pack_forget()
            if self.imp_panel.winfo_manager():
                self.imp_panel.pack_forget()
            if not self.empath_panel.winfo_manager():
                self.empath_panel.pack(fill="x")
            if self.clockmaker_panel.winfo_manager():
                self.clockmaker_panel.pack_forget()
        elif active_role == "Clockmaker":
            if self.investigator_panel.winfo_manager():
                self.investigator_panel.pack_forget()
            if self.imp_panel.winfo_manager():
                self.imp_panel.pack_forget()
            if self.empath_panel.winfo_manager():
                self.empath_panel.pack_forget()
            if not self.clockmaker_panel.winfo_manager():
                self.clockmaker_panel.pack(fill="x")
        else:
            if self.investigator_panel.winfo_manager():
                self.investigator_panel.pack_forget()
            if self.imp_panel.winfo_manager():
                self.imp_panel.pack_forget()
            if self.empath_panel.winfo_manager():
                self.empath_panel.pack_forget()
            if self.clockmaker_panel.winfo_manager():
                self.clockmaker_panel.pack_forget()

    def _refresh_investigator_panel(self) -> None:
        """Update the simple first-night Investigator workflow panel."""

        if self.game_state is None:
            self.investigator_info_text.set("No Investigator info to assign right now.")
            self.confirm_investigator_button.state(["disabled"])
            self.investigator_minion_picker.configure(state="disabled")
            self.investigator_minion_choice.set("")
            return

        investigator_active = (
            self.game_state.phase == "first_night"
            and shown_role_is_in_play(self.game_state, "Investigator")
        )
        investigator_seat = self._seat_for_display_step("Investigator", first_night=True)
        investigator_is_misled = shown_role_is_misled(self.game_state, "Investigator")

        if not investigator_active:
            if self.game_state.investigator_info_given and self.game_state.investigator_info_summary:
                self.investigator_info_text.set(self.game_state.investigator_info_summary)
            else:
                self.investigator_info_text.set("No Investigator info to assign right now.")
            self.confirm_investigator_button.state(["disabled"])
            self.investigator_minion_picker.configure(state="disabled")
            return

        if self.game_state.investigator_info_given and self.game_state.investigator_info_summary:
            self.investigator_info_text.set(self.game_state.investigator_info_summary)
            self.confirm_investigator_button.state(["disabled"])
            self.investigator_minion_picker.configure(state="disabled")
            return

        if investigator_seat is None:
            self.investigator_info_text.set("No Investigator seat is available right now.")
            self.confirm_investigator_button.state(["disabled"])
            self.investigator_minion_picker.configure(state="disabled")
            return

        if self.selected_player_index != investigator_seat:
            investigator_name = self.game_state.players[investigator_seat].name
            self.investigator_info_text.set(
                f"Select {investigator_name} to give and confirm the Investigator information."
            )
            self.confirm_investigator_button.state(["disabled"])
            self.investigator_minion_picker.configure(state="disabled")
            return

        correct_seat = self._seat_with_token("Correct Minion")
        wrong_seat = self._seat_with_token("Wrong Minion")
        if investigator_is_misled:
            self.investigator_minion_picker.configure(state="readonly")
            if not self.investigator_minion_choice.get():
                self.investigator_minion_choice.set("Baron")
        else:
            actual_minion_name = next(
                player.actual_role.name
                for player in self.game_state.players
                if player.actual_role.category == "Minion"
            )
            self.investigator_minion_choice.set(actual_minion_name)
            self.investigator_minion_picker.configure(state="disabled")

        if correct_seat is None or wrong_seat is None or correct_seat == wrong_seat:
            self.investigator_info_text.set(
                "Place one 'Correct Minion' token and one 'Wrong Minion' token, then confirm the information."
            )
            self.confirm_investigator_button.state(["!disabled"])
            return

        correct_name = self.game_state.players[correct_seat].name
        wrong_name = self.game_state.players[wrong_seat].name
        minion_name = self.investigator_minion_choice.get()
        self.investigator_info_text.set(
            f"Ready to tell the Investigator: either {correct_name} or {wrong_name} is the {minion_name}."
        )
        self.confirm_investigator_button.state(["!disabled"])

    def _refresh_imp_panel(self) -> None:
        """Update the other-night Imp kill workflow panel."""

        if self.game_state is None:
            self.imp_info_text.set("No Imp action to resolve right now.")
            self.confirm_imp_button.state(["disabled"])
            return

        imp_active = (
            self.game_state.phase == "other_night"
            and role_is_in_play(self.game_state, "Imp")
        )
        imp_seat = self._seat_for_display_step("Imp", first_night=False)

        if not imp_active:
            if self.game_state.imp_kill_resolved and self.game_state.imp_kill_summary:
                self.imp_info_text.set(self.game_state.imp_kill_summary)
            else:
                self.imp_info_text.set("No Imp action to resolve right now.")
            self.confirm_imp_button.state(["disabled"])
            return

        if self.game_state.imp_kill_resolved and self.game_state.imp_kill_summary:
            self.imp_info_text.set(self.game_state.imp_kill_summary)
            self.confirm_imp_button.state(["disabled"])
            return

        if imp_seat is None:
            self.imp_info_text.set("No Imp seat is available right now.")
            self.confirm_imp_button.state(["disabled"])
            return

        if self.selected_player_index != imp_seat:
            imp_name = self.game_state.players[imp_seat].name
            self.imp_info_text.set(
                f"Select {imp_name} to confirm the Imp kill for this night."
            )
            self.confirm_imp_button.state(["disabled"])
            return

        target_seat = self._seat_with_token("Dead")
        if target_seat is None:
            self.imp_info_text.set("Place the 'Dead' token on the living player the Imp kills tonight.")
            self.confirm_imp_button.state(["disabled"])
            return

        target = self.game_state.players[target_seat]
        if not target.is_alive:
            self.imp_info_text.set("Place the 'Dead' token on a living player for the Imp kill.")
            self.confirm_imp_button.state(["disabled"])
            return

        self.imp_info_text.set(f"Ready to kill {target.name} tonight.")
        self.confirm_imp_button.state(["!disabled"])

    def confirm_imp_kill(self) -> None:
        """Resolve the Imp kill for the current other night."""

        if self.game_state is None:
            return

        if self.game_state.phase != "other_night" or not role_is_in_play(self.game_state, "Imp"):
            self.status_text.set("The Imp is not acting right now.")
            return

        imp_seat = self._seat_for_display_step("Imp", first_night=False)
        if imp_seat is None or self.selected_player_index != imp_seat:
            self.status_text.set("Select the Imp seat before confirming player info.")
            return

        target_seat = self._seat_with_token("Dead")
        if target_seat is None:
            self.status_text.set("Place the Dead token on the player the Imp kills.")
            return

        target = self.game_state.players[target_seat]
        if not target.is_alive:
            self.status_text.set("Place the Dead token on a living player for the Imp kill.")
            return

        kill_player(self.game_state, target_seat)
        self.game_state.imp_kill_resolved = True
        self.game_state.imp_kill_summary = f"Imp killed {target.name} tonight."
        self._refresh_night_order_panel()
        self._refresh_imp_panel()
        self._refresh_empath_panel()
        self._refresh_info_panel_visibility()
        self._refresh_memory_panel()
        self._draw_player_circle()
        self.status_text.set(self.game_state.imp_kill_summary)

    def confirm_investigator_info(self) -> None:
        """Mark the current non-drunk Investigator information as given."""

        if self.game_state is None:
            return

        investigator_active = (
            self.game_state.phase == "first_night"
            and shown_role_is_in_play(self.game_state, "Investigator")
        )
        investigator_seat = self._seat_for_display_step("Investigator", first_night=True)
        correct_seat = self._seat_with_token("Correct Minion")
        wrong_seat = self._seat_with_token("Wrong Minion")

        if not investigator_active:
            self.status_text.set("Investigator info is not ready to be assigned right now.")
            return

        if investigator_seat is None or self.selected_player_index != investigator_seat:
            self.status_text.set("Select the Investigator seat before confirming player info.")
            return

        if correct_seat is None or wrong_seat is None or correct_seat == wrong_seat:
            self.status_text.set(
                "Place one Correct Minion token and one Wrong Minion token before confirming."
            )
            return

        if not self.investigator_minion_choice.get():
            self.status_text.set("Choose which Minion type the Investigator is being shown.")
            return

        correct_name = self.game_state.players[correct_seat].name
        wrong_name = self.game_state.players[wrong_seat].name
        minion_name = self.investigator_minion_choice.get()
        self.game_state.investigator_info_given = True
        self.game_state.investigator_info_summary = (
            f"Investigator info given: either {correct_name} or {wrong_name} is the {minion_name}."
        )
        memory_entry = (
            f"First night: either {correct_name} or {wrong_name} is the {minion_name}."
        )
        investigator_player = self.game_state.players[investigator_seat]
        if memory_entry not in investigator_player.memory:
            investigator_player.memory.append(memory_entry)
        self._refresh_night_order_panel()
        self._refresh_investigator_panel()
        self._refresh_info_panel_visibility()
        self._refresh_memory_panel()
        self.status_text.set(self.game_state.investigator_info_summary)

    def _refresh_empath_panel(self) -> None:
        """Update the first-night Empath workflow panel."""

        if self.game_state is None:
            self.empath_info_text.set("No Empath info to assign right now.")
            self.confirm_empath_button.state(["disabled"])
            self.empath_choice.set("")
            for button in self.empath_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        empath_active = (
            self.game_state.phase in {"first_night", "other_night"}
            and shown_role_is_in_play(self.game_state, "Empath")
        )
        empath_seat = self._seat_for_display_step("Empath", first_night=True)
        empath_is_misled = shown_role_is_misled(self.game_state, "Empath")

        if not empath_active:
            if self.game_state.empath_info_given and self.game_state.empath_info_summary:
                self.empath_info_text.set(self.game_state.empath_info_summary)
            else:
                self.empath_info_text.set("No Empath info to assign right now.")
            self.confirm_empath_button.state(["disabled"])
            self.empath_choice.set("")
            for button in self.empath_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        if self.game_state.empath_info_given and self.game_state.empath_info_summary:
            self.empath_info_text.set(self.game_state.empath_info_summary)
            self.confirm_empath_button.state(["disabled"])
            for button in self.empath_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        if empath_seat is None:
            self.empath_info_text.set("No Empath seat is available right now.")
            self.confirm_empath_button.state(["disabled"])
            for button in self.empath_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        if self.selected_player_index != empath_seat:
            empath_name = self.game_state.players[empath_seat].name
            self.empath_info_text.set(
                f"Select {empath_name} to give and confirm the Empath information."
            )
            self.confirm_empath_button.state(["disabled"])
            for button in self.empath_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        left_seat, right_seat = living_neighbor_seats(self.game_state, empath_seat)
        evil_neighbors = 0
        for neighbor_seat in (left_seat, right_seat):
            if neighbor_seat is not None and seat_is_evil(self.game_state, neighbor_seat):
                evil_neighbors += 1

        for index, button in enumerate(self.empath_buttons):
            if empath_is_misled or index == evil_neighbors:
                button.configure(state="normal")
            else:
                button.configure(state="disabled")

        if not self.empath_choice.get():
            self.empath_choice.set(str(evil_neighbors if not empath_is_misled else 0))

        left_name = self.game_state.players[left_seat].name if left_seat is not None else "nobody"
        right_name = self.game_state.players[right_seat].name if right_seat is not None else "nobody"
        if empath_is_misled:
            self.empath_info_text.set(
                f"Empath neighbors are {left_name} and {right_name}. The shown Empath is drunk or poisoned, so any value from 0 to 2 is allowed."
            )
        else:
            self.empath_info_text.set(
                f"Empath neighbors are {left_name} and {right_name}. The only legal value is {evil_neighbors}."
            )

        self.confirm_empath_button.state(["!disabled"])
        self._refresh_choice_button_styles()

    def select_empath_value(self, value: str) -> None:
        """Pick the value that will be shown to the Empath."""

        self.empath_choice.set(value)
        self._refresh_empath_panel()
        self._update_status_text()

    def confirm_empath_info(self) -> None:
        """Mark the current Empath information as given."""

        if self.game_state is None:
            return

        empath_active = (
            self.game_state.phase in {"first_night", "other_night"}
            and shown_role_is_in_play(self.game_state, "Empath")
        )
        empath_seat = self._seat_for_display_step("Empath", first_night=True)
        empath_is_misled = shown_role_is_misled(self.game_state, "Empath")

        if not empath_active or empath_seat is None or self.selected_player_index != empath_seat:
            self.status_text.set("Select the Empath seat before confirming player info.")
            return

        if self.empath_choice.get() not in {"0", "1", "2"}:
            self.status_text.set("Choose the value the Empath receives first.")
            return

        left_seat, right_seat = living_neighbor_seats(self.game_state, empath_seat)
        evil_neighbors = 0
        for neighbor_seat in (left_seat, right_seat):
            if neighbor_seat is not None and seat_is_evil(self.game_state, neighbor_seat):
                evil_neighbors += 1

        if not empath_is_misled and int(self.empath_choice.get()) != evil_neighbors:
            self.status_text.set("That is not the legal Empath value for the current living neighbors.")
            return

        self.game_state.empath_info_given = True
        self.game_state.empath_info_summary = (
            f"Empath info given: {self.empath_choice.get()} evil neighbor(s)."
        )
        memory_entry = (
            f"{self._current_night_label()}: you learned that you have "
            f"{self.empath_choice.get()} evil neighbor(s)."
        )
        empath_player = self.game_state.players[empath_seat]
        if memory_entry not in empath_player.memory:
            empath_player.memory.append(memory_entry)
        self._refresh_night_order_panel()
        self._refresh_empath_panel()
        self._refresh_info_panel_visibility()
        self._refresh_memory_panel()
        self.status_text.set(self.game_state.empath_info_summary)

    def _refresh_clockmaker_panel(self) -> None:
        """Update the first-night Clockmaker workflow panel."""

        if self.game_state is None:
            self.clockmaker_info_text.set("No Clockmaker info to assign right now.")
            self.confirm_clockmaker_button.state(["disabled"])
            self.clockmaker_choice.set("")
            for button in self.clockmaker_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        clockmaker_active = (
            self.game_state.phase == "first_night"
            and shown_role_is_in_play(self.game_state, "Clockmaker")
        )
        clockmaker_seat = self._seat_for_display_step("Clockmaker", first_night=True)
        clockmaker_is_misled = shown_role_is_misled(self.game_state, "Clockmaker")
        legal_distance = clockmaker_distance(self.game_state)
        max_distance = max_clockmaker_distance(self.game_state)

        if not clockmaker_active:
            if self.game_state.clockmaker_info_given and self.game_state.clockmaker_info_summary:
                self.clockmaker_info_text.set(self.game_state.clockmaker_info_summary)
            else:
                self.clockmaker_info_text.set("No Clockmaker info to assign right now.")
            self.confirm_clockmaker_button.state(["disabled"])
            self.clockmaker_choice.set("")
            for button in self.clockmaker_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        if self.game_state.clockmaker_info_given and self.game_state.clockmaker_info_summary:
            self.clockmaker_info_text.set(self.game_state.clockmaker_info_summary)
            self.confirm_clockmaker_button.state(["disabled"])
            for button in self.clockmaker_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        if clockmaker_seat is None or legal_distance is None:
            self.clockmaker_info_text.set("No Clockmaker seat is available right now.")
            self.confirm_clockmaker_button.state(["disabled"])
            for button in self.clockmaker_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        if self.selected_player_index != clockmaker_seat:
            clockmaker_name = self.game_state.players[clockmaker_seat].name
            self.clockmaker_info_text.set(
                f"Select {clockmaker_name} to give and confirm the Clockmaker information."
            )
            self.confirm_clockmaker_button.state(["disabled"])
            for button in self.clockmaker_buttons:
                button.configure(state="disabled")
            self._refresh_choice_button_styles()
            return

        for value, button in zip(self.clockmaker_button_values, self.clockmaker_buttons):
            numeric_value = int(value)
            if clockmaker_is_misled or numeric_value == legal_distance:
                button.configure(state="normal")
            else:
                button.configure(state="disabled")

        if not self.clockmaker_choice.get():
            self.clockmaker_choice.set(str(legal_distance if not clockmaker_is_misled else 1))

        if clockmaker_is_misled:
            self.clockmaker_info_text.set(
                f"The shown Clockmaker is drunk or poisoned, so any distance from 1 to {max_distance} is allowed."
            )
        else:
            self.clockmaker_info_text.set(
                f"The only legal Clockmaker value is {legal_distance}."
            )

        self.confirm_clockmaker_button.state(["!disabled"])
        self._refresh_choice_button_styles()

    def select_clockmaker_value(self, value: str) -> None:
        """Pick the value that will be shown to the Clockmaker."""

        self.clockmaker_choice.set(value)
        self._refresh_clockmaker_panel()
        self._update_status_text()

    def confirm_clockmaker_info(self) -> None:
        """Mark the current Clockmaker information as given."""

        if self.game_state is None:
            return

        clockmaker_active = (
            self.game_state.phase == "first_night"
            and shown_role_is_in_play(self.game_state, "Clockmaker")
        )
        clockmaker_seat = self._seat_for_display_step("Clockmaker", first_night=True)
        clockmaker_is_misled = shown_role_is_misled(self.game_state, "Clockmaker")
        legal_distance = clockmaker_distance(self.game_state)
        max_distance = max_clockmaker_distance(self.game_state)

        if not clockmaker_active or clockmaker_seat is None or self.selected_player_index != clockmaker_seat:
            self.status_text.set("Select the Clockmaker seat before confirming player info.")
            return

        valid_choices = {str(value) for value in range(1, max_distance + 1)}
        if self.clockmaker_choice.get() not in valid_choices:
            self.status_text.set("Choose the distance the Clockmaker receives first.")
            return

        if not clockmaker_is_misled and self.clockmaker_choice.get() != str(legal_distance):
            self.status_text.set("That is not the legal Clockmaker value for the current setup.")
            return

        self.game_state.clockmaker_info_given = True
        self.game_state.clockmaker_info_summary = (
            f"Clockmaker info given: {self.clockmaker_choice.get()} step(s)."
        )
        memory_entry = (
            f"First Night: you learned that the Demon is {self.clockmaker_choice.get()} "
            f"step(s) from its nearest Minion."
        )
        clockmaker_player = self.game_state.players[clockmaker_seat]
        if memory_entry not in clockmaker_player.memory:
            clockmaker_player.memory.append(memory_entry)
        self._refresh_night_order_panel()
        self._refresh_clockmaker_panel()
        self._refresh_info_panel_visibility()
        self._refresh_memory_panel()
        self.status_text.set(self.game_state.clockmaker_info_summary)

    def _rebuild_clockmaker_buttons(self) -> None:
        """Build Clockmaker value buttons for the current player count."""

        for child in self.clockmaker_buttons_frame.winfo_children():
            child.destroy()

        self.clockmaker_buttons = []
        self.clockmaker_button_values = []

        if self.game_state is None:
            return

        max_distance = max_clockmaker_distance(self.game_state)
        for value in range(1, max_distance + 1):
            value_text = str(value)
            button = tk.Button(
                self.clockmaker_buttons_frame,
                text=value_text,
                command=lambda choice=value_text: self.select_clockmaker_value(choice),
                relief="raised",
                bd=2,
                bg="#f3efe6",
                activebackground="#e2d4b7",
            )
            button.pack(side="left", expand=True, fill="x", padx=2)
            self.clockmaker_buttons.append(button)
            self.clockmaker_button_values.append(value_text)

    def _refresh_choice_button_styles(self) -> None:
        """Highlight the selected numeric choice for Empath and Clockmaker."""

        for value, button in zip(("0", "1", "2"), self.empath_buttons):
            is_selected = self.empath_choice.get() == value and button.cget("state") != "disabled"
            button.configure(
                relief="sunken" if is_selected else "raised",
                bg="#d9c39a" if is_selected else "#f3efe6",
            )

        for value, button in zip(self.clockmaker_button_values, self.clockmaker_buttons):
            is_selected = self.clockmaker_choice.get() == value and button.cget("state") != "disabled"
            button.configure(
                relief="sunken" if is_selected else "raised",
                bg="#d9c39a" if is_selected else "#f3efe6",
            )

    def _refresh_phase_button(self) -> None:
        """Update the single phase-advance button label."""

        if self.game_state is None:
            self.phase_button_text.set("Start First Night")
            return

        if self.game_state.phase == "setup":
            self.phase_button_text.set("Start First Night")
        elif self.game_state.phase == "first_night":
            self.phase_button_text.set("Start First Day")
        elif self.game_state.phase == "first_day":
            self.phase_button_text.set("Start Second Night")
        elif self.game_state.phase == "other_night":
            self.phase_button_text.set(f"Start Day {self.game_state.day_number + 1}")
        elif self.game_state.phase == "other_day":
            self.phase_button_text.set(f"Start Night {self.game_state.day_number + 1}")

    def _current_night_label(self) -> str:
        """Return the human-readable label for the current night."""

        if self.game_state is None:
            return "First Night"

        if self.game_state.phase == "first_night":
            return "First Night"

        if self.game_state.phase == "other_night":
            return f"Night {self.game_state.day_number + 1}"

        return "Night"

    def _wake_order_markers(self, first_night: bool) -> dict[int, int]:
        """Return wake-order numbers keyed by player seat."""

        if self.game_state is None:
            return {}

        markers: dict[int, int] = {}
        steps = self._display_steps_for_phase(first_night=first_night)
        for order_index, role_name in enumerate(steps, start=1):
            seat = self._seat_for_display_step(role_name, first_night=first_night)
            if seat is not None:
                markers[seat] = order_index
        return markers

    def _display_steps_for_phase(self, first_night: bool) -> list[str]:
        """Return the storyteller-facing role order for the current phase."""

        if self.game_state is None:
            return []

        if first_night:
            ordered_roles = ["Investigator", "Empath", "Clockmaker", "Chambermaid"]
        else:
            ordered_roles = []
            if self.game_state.scarlet_woman_became_demon_today:
                ordered_roles.append("Scarlet Woman")
            ordered_roles.extend(["Imp", "Sage", "Empath", "Chambermaid"])

        return [
            role_name
            for role_name in ordered_roles
            if self._seat_for_display_step(role_name, first_night=first_night) is not None
        ]

    def _seat_for_display_step(self, role_name: str, first_night: bool) -> int | None:
        """Return the seat that should receive the wake marker for a displayed step."""

        if self.game_state is None:
            return None

        if role_name == "Scarlet Woman":
            for player in self.game_state.players:
                if player.actual_role.name == "Scarlet Woman" and player.is_alive:
                    return player.seat
            return None

        if role_name == "Sage":
            for player in self.game_state.players:
                if player.role_in_bag.name == "Sage" and player.is_alive:
                    return player.seat
            return None

        for player in self.game_state.players:
            if player.role_in_bag.name == role_name and player.is_alive:
                return player.seat
        return None


def main() -> None:
    """Launch the small Tkinter setup tester."""

    root = tk.Tk()
    app = SetupApp(root)
    app.generate_setup()
    root.mainloop()


if __name__ == "__main__":
    main()

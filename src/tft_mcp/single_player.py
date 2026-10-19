"""Concrete adaptation of the installed Gym campaign for one controlled player.

GameSession owns copying, RNG/module isolation, native logs and publication. All
native construction and calls here run inside its simulator_scope.
"""

from copy import deepcopy
from types import SimpleNamespace

from Simulator.encoding.llm_observation import (
    legal_commands, mask_allows, remember_action, render_llm_text,
)
from Simulator.simulators.tft_simulator import TFTConfig
from Simulator.simulators.tft_single_player_simulator import TFT_Single_Player_Simulator

from tft_mcp.state import board_slots, freeze_unit, trait_records


class SinglePlayer:
    def __init__(self, seed):
        self.native = TFT_Single_Player_Simulator(TFTConfig(num_players=1))
        self.native.reset(seed=seed)
        self.terminal = False
        self.episode_outcome = None
        self.last_fight = None
        self._schedule = _campaign_schedule(self.native)
        # The renderer owns caches on this MCP view, never on the native class.
        # Ordinary deepcopy keeps these caches and all native graph aliases.
        self.view = SimpleNamespace(
            player_manager=self.player_manager,
            game_round=SimpleNamespace(current_round=self.game_round.current_round),
            possible_agents=["player_0"],
            max_actions_per_round=self.native.max_actions_per_round,
        )
        self._sync_view()
        render_llm_text(self.view, "player_0")

    @property
    def player_manager(self):
        return self.native.player_manager

    @property
    def game_round(self):
        return self.native.game_round

    @property
    def combat_ctx(self):
        return self.native.combat_ctx

    @property
    def actions_taken(self):
        return {"player_0": self.native.action_count}

    @property
    def max_actions_per_round(self):
        return self.native.max_actions_per_round

    def close(self):
        self.native.close()

    def campaign_schedule(self):
        return deepcopy(self._schedule)

    def observe(self):
        return {"terminal": self.terminal,
                "mask": [] if self.terminal else legal_commands(self.player_manager.action_handlers["player_0"]),
                "text": render_llm_text(self.view, "player_0")}

    def step(self, action):
        handler = self.player_manager.action_handlers["player_0"]
        if not mask_allows(handler, action):
            return {"accepted": False, "action": action, "mask": legal_commands(handler)}
        fight_round = self.game_round.current_round
        previous_reward = self.native.reward
        _, cumulative_reward, terminated, truncated, _ = self.native.step(action)
        reward = float(cumulative_reward - previous_reward)
        self.terminal = bool(terminated or truncated)
        advanced = self.game_round.current_round != fight_round
        if advanced:
            self.last_fight = _last_fight(self.game_round, fight_round, reward > 0)
        if self.terminal:
            self.episode_outcome = "won" if reward > 0 else "lost"
        self._sync_view()
        remember_action(self.view, "player_0", action, True, advanced or self.terminal or action[0] in (5, 6))
        return {"accepted": True, "terminal": self.terminal, "start_turn": advanced,
                "rewards": {"player_0": reward},
                "trace": [{"player_id": "player_0", "round": fight_round, "action": list(action)}]}

    def finish_round(self):
        round_number = self.game_round.current_round
        trace, reward = [], 0.0
        # Native pass consumes one action, just like every other decoded triple.
        for _ in range(self.max_actions_per_round):
            result = self.step([0, 0, 0])
            if not result["accepted"]:
                return result
            trace.extend(result["trace"])
            reward += result["rewards"]["player_0"]
            if self.terminal or self.game_round.current_round != round_number:
                return {**result, "trace": trace, "rewards": {"player_0": reward}}
        raise RuntimeError("Native campaign did not finish its planning phase.")

    def _sync_view(self):
        self.view.actions_taken = self.actions_taken
        self.view.terminations = {"player_0": self.terminal}
        self.view.truncations = {"player_0": False}
        self.view.game_round.current_round = (
            self.last_fight["round"] if self.terminal else self.game_round.current_round
        )


def _last_fight(game_round, round_number, won):
    enemy = game_round.last_opponent
    record = None
    if not game_round.last_was_minion and enemy is not None:
        board = [[freeze_unit(unit) for unit in column] for column in enemy.board]
        record = {"level": enemy.level, "board": board_slots({"board": board}, occupied_only=True),
                  "traits": trait_records({"composition": dict(enemy.team_composition),
                                           "tiers": dict(enemy.team_tiers)}, active_only=True)}
    return {"round": round_number, "kind": "minion" if game_round.last_was_minion else "combat",
            "won": won, "enemy": record}


def _campaign_schedule(native):
    leveling = native.game_round.leveling_system
    # The native constructor uses its initial generator, then switches to
    # battle_levels[1:] after the first combat via single_player_level_up().
    configs = [leveling.battle_generator.generator_config, *leveling.battle_levels[1:]]
    combat_index, schedule = 0, []
    for round_number, methods in enumerate(native.game_round.game_rounds):
        if round_number == 0:  # reset already ran the introductory carousel/fight.
            continue
        names = {method.__name__ for method in methods}
        combat = "combat_round" in names
        enemy = None
        if combat:
            config = configs[min(combat_index, len(configs) - 1)]
            combat_index += 1
            enemy = {"level": config["current_level"], "level_varies": config["extra_randomness"],
                     "max_cost": None if config["sample_from_pool"] else config["max_cost"],
                     "two_star_chance": config["two_star_unit_percentage"],
                     "three_star_chance": config["three_star_unit_percentage"],
                     "chosen": config["chosen"], "items_per_unit": config["num_items"],
                     "items_vary": config["extra_randomness"]}
        schedule.append({"round": round_number, "kind": "combat" if combat else "minion",
                         "carousel": "carousel_round" in names, "enemy": enemy})
    return schedule

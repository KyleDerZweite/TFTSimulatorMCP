"""Concrete simulator ownership and lifecycle, independent of MCP transport."""

from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from importlib import metadata
import json
import os
from pathlib import Path
import random
import tempfile
from functools import wraps
import sys
import threading
import uuid


from tft_mcp.comp_index import get_index
from tft_mcp.errors import SessionError

from tft_mcp.state import (
    freeze_unit, freeze_player, shop_slots, board_slots, bench_slots, inventory_slots, trait_records,
)

from tft_mcp.simulator_identity import (
    simulator_identity, simulator_defaults,
)


SIMULATOR_LOCK = threading.RLock()
MAX_PROGRESS_STEPS = 6000


def transactional(method):
    @wraps(method)
    def invoke(self, *args, **kwargs):
        with self.lifecycle_transaction(mutable=True):
            return method(self, *args, **kwargs)
    return invoke


class GameSession:
    def __init__(self, audit_path=None, native_root=None):
        self.audit_path = Path(audit_path).resolve() if audit_path else None
        self.native_root = Path(native_root).resolve() if native_root else (
            self.audit_path.parent / "native" if self.audit_path else None
        )
        self.game = None
        self.game_id = None
        self.state = "idle"
        self.outcome = None
        self.planning_budget = None
        self.baselines = {}
        self.native_dir = None
        self.baseline_rng = None
        self.python_rng = None
        self.module_state = None
        self.placements = {}
        self.terminal_snapshot = None
        self._records = None
        self._candidate_prepared = False
        self._native_snapshot = None
        self.public_final = {}
        self.sequence = 0
        self.server_id = uuid.uuid4().hex
        self.deliver_text = False
        self.last_reward = 0.0
        self.mode = "full"

    def search_champions(self, query='', cost=None, trait_id=None):
        from tft_mcp import champion_catalog
        if trait_id is not None and trait_id not in champion_catalog.origin_class_stats.tiers:
            raise SessionError('invalid_input', 'Unknown trait filter.', {'field': 'trait_id', 'value': trait_id})
        return champion_catalog.search_champions(query, cost, trait_id)

    def get_champion(self, champion_id):
        from tft_mcp import champion_catalog
        if champion_id not in champion_catalog.stats.BASE_CHAMPION_LIST:
            raise SessionError('unknown_champion', f'Unknown champion: {champion_id}.', {'champion_id': champion_id})
        return champion_catalog.get_champion(champion_id)

    def get_champion_pool(self, champion_id):
        """Visible-state pool estimate without reading hidden opponent holdings."""
        with SIMULATOR_LOCK:
            if self.game is None:
                raise SessionError('no_game', 'Start a game before inspecting player state.')
            from tft_mcp import champion_catalog
            from tft_mcp.state import champion_copies
            if champion_id not in champion_catalog.stats.BASE_CHAMPION_LIST:
                raise SessionError('unknown_champion', f'Unknown champion: {champion_id}.', {'champion_id': champion_id})
            try:
                pool_size = champion_catalog.pool_size(champion_id)
            except KeyError as error:
                raise SessionError('internal_error', 'Installed pool size is missing.', {'champion_id': champion_id}) from error
            visible = 0
            for player_id, player in self.game.player_manager.player_states.items():
                if self.mode == "single_player" and player_id != "player_0":
                    continue
                if player is None:
                    continue
                for column in player.board:
                    for unit in column:
                        visible += champion_copies(unit, champion_id)
                if player_id == 'player_0':
                    for unit in player.bench:
                        visible += champion_copies(unit, champion_id)
            return {'game_id': self.game_id, 'round': self.game.game_round.current_round,
                    'champion_id': champion_id, 'pool_size': pool_size, 'visible_copies': visible,
                    'remaining': max(0, pool_size - visible)}

    def search_comps_by_champions(self, champions, limit):
        return get_index().search_comps_by_champions(champions, limit)

    def search_comps_by_trait(self, trait, level, limit):
        return get_index().search_comps_by_trait(trait, level, limit)

    def search_champion_items(self, champion, items=None):
        return get_index().search_champion_items(champion, items)

    def search_traits(self, query=''):
        from tft_mcp import champion_catalog
        return champion_catalog.search_traits(query)

    def get_trait(self, trait_id):
        from tft_mcp import champion_catalog
        if trait_id not in champion_catalog.origin_class_stats.tiers:
            raise SessionError('unknown_trait', f'Unknown trait: {trait_id}.', {'trait_id': trait_id})
        return champion_catalog.get_trait(trait_id)

    def get_trait_champions(self, trait_id):
        from tft_mcp import champion_catalog
        if trait_id not in champion_catalog.origin_class_stats.tiers:
            raise SessionError('unknown_trait', f'Unknown trait: {trait_id}.', {'trait_id': trait_id})
        return champion_catalog.get_trait_champions(trait_id)

    def search_items(self, query="", kind=None):
        from tft_mcp.item_catalog import search_items

        if type(query) is not str:
            raise SessionError("invalid_input", "query must be a string.", {"field": "query", "value": query})
        if kind is not None and (type(kind) is not str or kind not in {"component", "equipment", "consumable"}):
            raise SessionError("invalid_input", "Unknown item kind.", {"field": "kind", "value": kind})
        return search_items(query, kind)

    def get_item(self, item_id):
        from Simulator.battle import item_stats
        from tft_mcp.item_catalog import get_item

        if type(item_id) is not str:
            raise SessionError("invalid_input", "item_id must be a string.", {"field": "item_id", "value": item_id})
        if item_id not in item_stats.items:
            raise SessionError("unknown_item", f"Unknown item: {item_id}", {"item_id": item_id})
        return get_item(item_id)

    def record(self, event, **fields):
        if self._records is None:
            with self.lifecycle_transaction():
                self.record(event, **fields)
            return
        self.sequence += 1
        self._records.append({"server_id": self.server_id, "sequence": self.sequence,
                              "event": event, **fields})

    def probe_audit(self):
        if self.audit_path is None:
            raise SessionError("log_unavailable", "Set TFT_MCP_AUDIT_PATH to a writable audit file.")
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            if self.audit_path.exists():
                self.audit_path.read_bytes()
            with tempfile.TemporaryFile(dir=self.audit_path.parent) as stream:
                stream.write(b"audit destination probe")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            raise SessionError("log_unavailable", "Audit log is unavailable.", {
                "path": str(self.audit_path), "error": str(error)}) from error

    def publish_audit(self):
        if self.audit_path is None:
            raise SessionError("log_unavailable", "Set TFT_MCP_AUDIT_PATH to a writable audit file.")
        temporary = None
        try:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            previous = self.audit_path.read_bytes() if self.audit_path.exists() else b""
            with tempfile.NamedTemporaryFile(dir=self.audit_path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(previous)
                for record in self._records:
                    stream.write((json.dumps(record, sort_keys=True) + "\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.audit_path)
            temporary = None
        except OSError as error:
            raise SessionError("log_unavailable", "Audit log is unavailable.", {
                "path": str(self.audit_path), "error": str(error)}) from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @contextmanager
    def simulator_scope(self, game=None, native_dir=None):
        """Contain core relative writes, output and legacy randomness."""
        import numpy as np
        from Simulator.battle import champion, origin_class

        with SIMULATOR_LOCK:
            previous_dir = Path.cwd()
            previous_python = random.getstate()
            previous_numpy = np.random.get_state()
            previous_modules = (origin_class.game_comp_tiers, origin_class.game_compositions,
                                champion.test_multiple, champion.log)
            if self.python_rng is not None:
                random.setstate(self.python_rng)
            if self.baseline_rng is not None:
                np.random.set_state(self.baseline_rng)
            if self.module_state is not None:
                (origin_class.game_comp_tiers, origin_class.game_compositions,
                 champion.test_multiple, champion.log) = self.module_state
            active = game if game is not None else self.game
            try:
                os.chdir(native_dir or self.native_dir)
                with redirect_stdout(sys.stderr):
                    if active is not None and hasattr(active, "combat_ctx"):
                        with active.combat_ctx.bind():
                            yield
                    else:
                        yield
            finally:
                self.python_rng = random.getstate()
                self.baseline_rng = np.random.get_state()
                self.module_state = (origin_class.game_comp_tiers, origin_class.game_compositions,
                                     champion.test_multiple, champion.log)
                random.setstate(previous_python)
                np.random.set_state(previous_numpy)
                (origin_class.game_comp_tiers, origin_class.game_compositions,
                 champion.test_multiple, champion.log) = previous_modules
                os.chdir(previous_dir)

    def prepare_candidate(self):
        if self._candidate_prepared:
            return
        candidate = deepcopy(self.__dict__)
        self.__dict__.update(candidate)
        self._candidate_prepared = True
        if self.game is not None:
            self._native_snapshot = {path.relative_to(self.native_dir): path.read_bytes()
                                     for path in self.native_dir.rglob("*") if path.is_file()}

    def restore_native(self, snapshot):
        """Return the per-game native directory to its accepted bytes."""
        for path in self.native_dir.rglob("*"):
            if path.is_file() and path.relative_to(self.native_dir) not in snapshot:
                path.unlink()
        for relative, data in snapshot.items():
            path = self.native_dir / relative
            if not path.is_file() or path.read_bytes() != data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)

    @contextmanager
    def lifecycle_transaction(self, mutable=False):
        """Keep candidate fields private under the lock until their audit commit."""
        with SIMULATOR_LOCK:
            if self._records is not None:
                if mutable:
                    self.prepare_candidate()
                yield
                return
            previous = dict(self.__dict__)
            try:
                self._records = []
                if mutable:
                    self.prepare_candidate()
                yield
                self.publish_audit()
                self._records = None
                self._candidate_prepared = False
                self._native_snapshot = None
            except Exception as error:
                diagnostic = self.native_dir if self.native_dir != previous["native_dir"] else None
                failed_id = self.game_id
                snapshot = self._native_snapshot
                self.__dict__.update(previous)
                if snapshot is not None:
                    try:
                        self.restore_native(snapshot)
                    except OSError as restore_error:
                        raise SessionError("log_unavailable", "Native simulator log could not be restored.", {
                            "path": str(self.native_dir), "error": str(restore_error),
                            "cause": str(error)}) from error
                if isinstance(error, SessionError):
                    if diagnostic is not None:
                        error.details.update(native_log_dir=str(diagnostic), failed_game_id=failed_id)
                    raise
                code = "log_unavailable" if isinstance(error, OSError) else "internal_error"
                raise SessionError(code, "Transaction failed; committed game is unchanged.", {
                    "error": str(error), "native_log_dir": str(diagnostic),
                    "failed_game_id": failed_id}) from error

    def get_game_status(self):
        with SIMULATOR_LOCK:
            capacity = self.game.max_actions_per_round if self.game and self.mode == "single_player" else 15
            return {
                "state": self.state,
                "game_id": self.game_id,
                "controlled_player_id": "player_0" if self.game else None,
                "round": self.game.game_round.current_round if self.game else None,
                "planning_budget": ({"capacity": capacity, "remaining": max(0, capacity - self.game.actions_taken["player_0"])}
                                    if self.state == "running" else None),
                "outcome": deepcopy(self.outcome),
            }

    def own_inspection(self, player_id="player_0"):
        if self.game is None:
            raise SessionError("no_game", "Start a game before inspecting player state.")
        if player_id != "player_0":
            raise SessionError("invalid_player", "Only the controlled player is available.", {
                "player_id": player_id, "supported_ids": ["player_0"]})
        if self.state == "terminal":
            if self.terminal_snapshot is None:
                raise SessionError("internal_error", "Terminal own-state snapshot is unavailable.", {
                    "player_id": player_id})
            return deepcopy(self.terminal_snapshot)
        return freeze_player(self.game.player_manager.player_states[player_id], self.game.game_round.current_round)

    def public_player(self, player_id, category):
        if self.game is None:
            raise SessionError("no_game", "Start a game before inspecting player state.")
        manager = self.game.player_manager
        supported = self._listed_player_ids()
        if player_id not in supported:
            raise SessionError("invalid_player", "Select a player_id from get_players.", {
                "player_id": player_id, "supported_ids": supported})
        player = manager.player_states.get(player_id)
        if player is None:
            raise SessionError("player_eliminated", f"This player's {category} is unavailable after removal. Use get_players for final public status.", {
                "player_id": player_id, "category": category})
        return player

    def get_players(self):
        with SIMULATOR_LOCK:
            if self.game is None:
                raise SessionError("no_game", "Start a game before inspecting players.")
            manager = self.game.player_manager
            players = []
            for player_id in self._listed_player_ids():
                player = manager.player_states.get(player_id)
                placement = self.placements.get(player_id)
                public = ({"health": player.health, "level": player.level} if player is not None
                          else self.public_final.get(player_id, {}))
                status = "alive"
                if placement == 1:
                    status = "winner"
                elif (placement is not None or player is None
                      or self.mode == "single_player" and self.game.episode_outcome == "lost"):
                    status = "eliminated"
                players.append({"player_id": player_id, "controlled": player_id == "player_0",
                                "status": status,
                                "health": public.get("health"), "level": public.get("level"), "placement": placement})
            return {"game_id": self.game_id, "players": players}

    def get_last_fight(self):
        with SIMULATOR_LOCK:
            if self.game is None:
                raise SessionError("no_game", "Start a game before inspecting the last fight.")
            if self.mode != "single_player":
                raise SessionError("invalid_input", "get_last_fight is only available in single_player mode.")
            fight = self.game.last_fight
            if fight is None:
                return {"game_id": self.game_id, "round": None, "kind": "none", "won": None, "enemy": None}
            return {"game_id": self.game_id, **deepcopy(fight)}

    def campaign_schedule(self):
        with SIMULATOR_LOCK:
            if self.game is None or self.mode != "single_player":
                return []
            return deepcopy(self.game.campaign_schedule())

    def _listed_player_ids(self):
        if self.mode == "single_player":
            return ["player_0"]
        return sorted(self.game.player_manager.player_ids)

    def get_board(self, player_id="player_0"):
        with SIMULATOR_LOCK:
            if player_id == "player_0":
                snapshot = self.own_inspection()
            else:
                player = self.public_player(player_id, "board")
                snapshot = {"board": [[freeze_unit(unit) for unit in column] for column in player.board],
                            "num_units_in_play": player.num_units_in_play, "max_units": player.max_units,
                            "round": self.game.game_round.current_round}
            return {"game_id": self.game_id, "player_id": player_id, "round": snapshot["round"],
                    "slots": board_slots(snapshot),
                    "num_units_in_play": snapshot["num_units_in_play"], "max_units": snapshot["max_units"]}

    def get_bench(self):
        with SIMULATOR_LOCK:
            snapshot = self.own_inspection()
            return {"game_id": self.game_id, "player_id": "player_0", "round": snapshot["round"],
                    "slots": bench_slots(snapshot)}

    def get_shop(self):
        with SIMULATOR_LOCK:
            snapshot = self.own_inspection()
            return {"game_id": self.game_id, "player_id": "player_0", "round": snapshot["round"],
                    "slots": shop_slots(snapshot)}

    def get_decision(self):
        """The simulator observation: full on the first read, then only what changed."""
        with SIMULATOR_LOCK:
            if self.game is None:
                raise SessionError("no_game", "Start a game before inspecting player state.")
            return self._public_observation()

    def get_items(self):
        with SIMULATOR_LOCK:
            snapshot = self.own_inspection()
            return {"game_id": self.game_id, "player_id": "player_0", "round": snapshot["round"],
                    "slots": inventory_slots(snapshot)}

    def get_economy(self):
        with SIMULATOR_LOCK:
            snapshot = self.own_inspection()
            return {"game_id": self.game_id, "player_id": "player_0", "round": snapshot["round"],
                    **{key: snapshot["economy"][key] for key in ("gold", "health", "level", "exp")},
                    "planning_budget": self.get_game_status()["planning_budget"]}

    def get_traits(self, player_id="player_0"):
        with SIMULATOR_LOCK:
            if player_id == "player_0":
                snapshot = self.own_inspection()
                traits = snapshot["traits"]
                round_number = snapshot["round"]
            else:
                player = self.public_player(player_id, "traits")
                traits = {"composition": player.team_composition, "tiers": player.team_tiers}
                round_number = self.game.game_round.current_round
            return {"game_id": self.game_id, "player_id": player_id, "round": round_number,
                    "traits": trait_records(traits)}

    def get_round(self):
        with SIMULATOR_LOCK:
            if self.game is None:
                raise SessionError("no_game", "Start a game before inspecting the round.")
            return {"game_id": self.game_id, "round": self.get_game_status()["round"]}

    @transactional
    def start_game(self, seed, mode="full"):
        if mode not in {"full", "single_player"}:
            raise SessionError("invalid_input", "mode must be full or single_player.", {"mode": mode})
        if type(seed) is not int or not 0 <= seed <= 2147483647:
            raise SessionError("invalid_input", "seed must be an integer from 0 through 2147483647.")
        if self.state != "idle":
            raise SessionError("game_active", "Close the active game before starting another.", {
                "game_id": self.game_id, "state": self.state,
            })
        game_id = uuid.uuid4().hex
        candidate_dir = self.native_root / game_id if self.native_root else None
        self.probe_audit()
        self.record("start_candidate", game_id=game_id, seed=seed,
                    native_log_dir=str(candidate_dir) if candidate_dir else None)
        try:
            if candidate_dir is None:
                raise OSError("No native log directory is configured")
            candidate_dir.mkdir(parents=True)
            with (candidate_dir / "log.txt").open("a", encoding="utf-8") as stream:
                stream.write("")
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            self.record("failed_start", game_id=game_id, native_log_dir=str(candidate_dir), error=str(error))
            raise SessionError("log_unavailable", "Native simulator log directory is unavailable.", {
                "path": str(candidate_dir), "error": str(error),
            }) from error

        candidate = None
        try:
            with redirect_stdout(sys.stderr):
                import numpy as np
                from Simulator.battle import champion, origin_class
                from Simulator.battle.combat_context import ListProxy
                from Simulator.generators.default_agent import Default_Agent
                from Simulator.simulators.tft_simulator import TFTConfig, TFT_Simulator

            self.python_rng = random.Random(seed).getstate()
            self.baseline_rng = np.random.RandomState(seed).get_state()
            self.module_state = (deepcopy(origin_class.game_comp_tiers_base),
                                 deepcopy(origin_class.game_compositions_base),
                                 {key: 0 for key in champion.test_multiple}, ListProxy("log"))
            with self.simulator_scope(native_dir=candidate_dir):
                if mode == "single_player":
                    from tft_mcp.single_player import SinglePlayer
                    candidate = SinglePlayer(seed)
                    baselines = {}
                else:
                    candidate = TFT_Simulator(TFTConfig())
                    candidate.reset(seed=seed)
                    baselines = {f"player_{i}": Default_Agent(False) for i in range(1, 8)}
            self.record("game_started", game_id=game_id, seed=seed, baseline_seed=seed,
                        baseline=("generated" if mode == "single_player"
                                  else "Simulator.generators.default_agent.Default_Agent(False)"),
                        controlled_player_id="player_0", hash_seed=os.environ.get("PYTHONHASHSEED"), hash_probe=hash("tft-mcp"),
                        simulator=simulator_identity(), runtime={
                            "python": sys.version, "implementation": sys.implementation.name,
                            "dependencies": {name: metadata.version(name) for name in
                                             ("numpy", "PettingZoo", "gymnasium", "mcp")},
                        }, configuration={
                            "mode": mode,
                            "num_players": 1 if mode == "single_player" else 8,
                            "max_actions_per_round": 15,
                            "reward_type": "winloss", "render_mode": None,
                            "render_path": "Games", "multi_step_position": False,
                            "preset_battle": False, "step_until_units_placed": False,
                            "observation_class": "Simulator.encoding.token.basic_observation.ObservationToken",
                            "action_class": "Simulator.encoding.token.action.ActionToken",
                            "simulator_defaults": simulator_defaults(),
                        }, native_log_dir=str(candidate_dir))
        except Exception as error:
            if candidate is not None:
                try:
                    with self.simulator_scope(game=candidate, native_dir=candidate_dir):
                        candidate.close()
                except Exception:
                    # Retain the initialization error and unpublished diagnostic directory.
                    pass
            self.python_rng = None
            self.baseline_rng = None
            self.module_state = None
            try:
                self.record("failed_start", game_id=game_id, native_log_dir=str(candidate_dir), error=str(error))
            except SessionError:
                pass
            if isinstance(error, SessionError):
                error.details.update({"failed_game_id": game_id, "native_log_dir": str(candidate_dir)})
                raise
            code = "log_unavailable" if isinstance(error, OSError) else "internal_error"
            raise SessionError(code, "Game initialization failed; the session remains idle.", {
                "failed_game_id": game_id, "native_log_dir": str(candidate_dir), "error": str(error),
            }) from error
        self.game = candidate
        self.game_id = game_id
        self.baselines = baselines
        self.mode = mode
        self.native_dir = candidate_dir
        self.state = "running"
        self.deliver_text = True
        return self.get_game_status()

    @transactional
    def close_game(self):
        outcome = self.outcome
        if self.game is not None:
            if self.state == "running":
                outcome = {"controlled_placement": None, "lobby_complete": False, "reason": "closed_incomplete"}
            self.record("game_closed", game_id=self.game_id, outcome=outcome,
                        native_log_dir=str(self.native_dir))
            with self.simulator_scope():
                self.game.close()
        receipt = {"closed_game_id": self.game_id, "outcome": deepcopy(outcome)}
        self.game = None
        self.game_id = None
        self.state = "idle"
        self.outcome = None
        self.planning_budget = None
        self.placements = {}
        self.terminal_snapshot = None
        self.public_final = {}
        self.baselines = {}
        self.native_dir = None
        self.python_rng = None
        self.baseline_rng = None
        self.module_state = None
        receipt["status"] = self.get_game_status()
        return receipt

    def require_decision(self):
        if self.state == "idle":
            raise SessionError("no_game", "Start a game first.")
        if self.state == "terminal":
            raise SessionError("game_terminal", "The completed game accepts no more actions.")
        if self.mode == "single_player":
            return
        if (self.game.agent_selection != "player_0" or self.game.truncations.get("player_0")
                or self.game.terminations.get("player_0", True)):
            raise SessionError("internal_error", "No controlled decision is available.")

    def _mask_command(self, action):
        return {"action_type": int(action[0]), "x1": int(action[1]), "x2": int(action[2])}

    def _public_observation(self, step_result=None):
        if self.mode == "single_player":
            with self.simulator_scope():
                observed = self.game.observe()
        else:
            observed = self.game.llm_observe("player_0")
        terminal = bool(observed["terminal"] or self.state == "terminal")
        if step_result is not None:
            self.last_reward = step_result["rewards"]["player_0"]
            start_turn = bool(step_result["start_turn"] or terminal)
        else:
            start_turn = bool(self.deliver_text or terminal)
        return {"reward": self.last_reward, "start_turn": start_turn, "terminal": terminal,
                "mask": [self._mask_command(action) for action in observed["mask"]],
                "text": observed["text"]}

    def _living_players(self):
        game = self.game
        return [(key, player) for key, player in game.player_manager.player_states.items()
                if player is not None and not game.terminations.get(key, True)]

    def _note_removals(self, retained, alive):
        game = self.game
        for key, player in retained:
            removed = game.player_manager.player_states.get(key) is None
            if removed and key not in self.placements and player.health <= 0:
                self.placements[key] = alive
                alive -= 1
        for key, player in retained:
            if game.player_manager.player_states.get(key) is None and key not in self.placements:
                self.placements[key] = 1
            if key in self.placements:
                self.public_final[key] = {"health": player.health, "level": player.level}
            if key == "player_0" and key in self.placements and self.terminal_snapshot is None:
                self.terminal_snapshot = freeze_player(player, game.game_round.current_round)

    def _record_trace(self, result, kind):
        for entry in result["trace"]:
            self.record("progression", game_id=self.game_id, player_id=entry["player_id"],
                        round=entry["round"], kind=kind if entry["player_id"] == "player_0" else "baseline",
                        action=entry["action"], placements=dict(self.placements),
                        native_log_dir=str(self.native_dir))

    def _snapshot_single_player(self, episode):
        player = self.game.player_manager.player_states.get("player_0")
        if player is not None and self.terminal_snapshot is None:
            self.public_final["player_0"] = {"health": player.health, "level": player.level}
            self.terminal_snapshot = freeze_player(player, self.game.last_fight["round"])
        if episode == "won":
            self.placements["player_0"] = 1

    def _finish_lobby(self, result):
        if not result["terminal"] or self.state == "terminal":
            return result
        episode = getattr(self.game, "episode_outcome", None)
        if episode in {"won", "lost"}:
            self._snapshot_single_player(episode)
        self.state = "terminal"
        self.outcome = {"controlled_placement": self.placements.get("player_0"),
                        "lobby_complete": True, "reason": "lobby_complete"}
        self.record("lobby_complete", game_id=self.game_id, outcome=self.outcome,
                    placements=self.placements, native_log_dir=str(self.native_dir))
        return result

    def _apply_result(self, retained, result, kind, alive=0):
        self._note_removals(retained, alive)
        self._record_trace(result, kind)
        self._finish_lobby(result)
        self.deliver_text = bool(result["start_turn"] or result["terminal"] or self.state == "terminal")
        return self._public_observation(result)

    @transactional
    def refresh_shop(self, **arguments):
        if arguments:
            raise SessionError("invalid_input", "refresh_shop takes no arguments.")
        return self._controlled([2, 0, 0], "refresh_shop")

    @transactional
    def buy_xp(self, **arguments):
        if arguments:
            raise SessionError("invalid_input", "buy_xp takes no arguments.")
        return self._controlled([1, 0, 0], "buy_xp")

    @transactional
    def buy_unit(self, **arguments):
        return self._controlled([3, arguments["shop_slot"], 0], "buy_unit")

    @transactional
    def sell_unit(self, **arguments):
        return self._controlled([4, _flat_location(arguments["location"]), 0], "sell_unit")

    @transactional
    def move_unit(self, **arguments):
        return self._controlled([5, _flat_location(arguments["source"]), _flat_location(arguments["target"])],
                                "move_unit")

    @transactional
    def equip_item(self, **arguments):
        return self._controlled([6, _flat_location(arguments["target"]), arguments["item_slot"]], "equip_item")

    def _controlled(self, action, kind):
        self.require_decision()
        if self.mode == "single_player":
            with self.simulator_scope():
                result = self.game.step(action)
            self._require_accepted(result)
            return self._apply_result([], result, kind)
        retained = self._living_players()
        alive = self.game.num_alive
        with self.simulator_scope():
            result = self.game.step_controlled([action], ("player_0",))
            self._require_accepted(result)
            self._note_removals(retained, alive)
            result = self._finish_until_decision(result)
            if action[0] in (5, 6) and not result["start_turn"] and not result["terminal"]:
                from Simulator.encoding.llm_observation import remember_action
                # Native movement/equipment hints omit some fields after swaps or merges.
                # Ask its native renderer to compare every visible section.
                remember_action(self.game, "player_0", action, True, True)
        return self._apply_result([], result, kind)

    def _require_accepted(self, result):
        if not result["accepted"]:
            raise SessionError("masked", "The action failed.", {
                "action": self._mask_command(result["action"]),
                "mask": [self._mask_command(command) for command in result["mask"]],
            })

    @transactional
    def end_turn(self):
        self.require_decision()
        if self.mode == "single_player":
            with self.simulator_scope():
                result = self.game.finish_round()
            self._require_accepted(result)
            return self._apply_result([], result, "end_turn")
        with self.simulator_scope():
            retained = self._living_players()
            alive = self.game.num_alive
            result = self.game.finish_controlled_round(("player_0",))
            self._note_removals(retained, alive)
            result = self._finish_until_decision(result)
        return self._apply_result([], result, "end_turn")

    def _finish_until_decision(self, result):
        """Finish baselines after elimination on either explicit or automatic combat."""
        trace = list(result["trace"])
        reward = result["rewards"]["player_0"]
        for _ in range(MAX_PROGRESS_STEPS):
            controlled_ready = (self.game.agent_selection == "player_0"
                                and not self.game.terminations.get("player_0", True)
                                and not self.game.truncations.get("player_0"))
            if result["terminal"] or controlled_ready:
                return {**result, "trace": trace,
                        "rewards": {**result["rewards"], "player_0": reward}}
            retained = self._living_players()
            alive = self.game.num_alive
            result = self.game.finish_controlled_round(("player_0",))
            self._note_removals(retained, alive)
            trace.extend(result["trace"])
            reward += result["rewards"]["player_0"]
        raise SessionError("internal_error", "Simulator progression exceeded 6000 steps.")


def _flat_location(location):
    if location["kind"] == "board":
        return location["x"] * 4 + location["y"]
    return 28 + location["slot"]

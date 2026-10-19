"""Real native campaign semantics and the session's atomic publication."""

from copy import deepcopy
import json
import os
from pathlib import Path
import pickle
import random
import subprocess
import sys

import jsonschema
import numpy as np
import pytest

from support import client, install_units, normalized_graph, simulator_bindings
from tft_mcp.errors import SessionError
from tft_mcp.session import GameSession
from tft_mcp.single_player import SinglePlayer
from tft_mcp.tool_calls import ToolCalls
from tft_mcp.tools import SINGLE_PLAYER_TOOLS
from tft_mcp.transport import campaign_text


@pytest.fixture
def session(tmp_path):
    session = GameSession(tmp_path / "audit.jsonl", tmp_path / "native")
    session.start_game(0, "single_player")
    yield session
    session.close_game()


def assert_aliases(game):
    native = game.native
    manager = native.player_manager
    assert game.view.player_manager is manager
    assert native.PLAYER is manager.player_states["player_0"]
    assert native.game_round.PLAYER is native.PLAYER
    assert native.game_round.pool_obj is manager.pool_obj
    assert native.game_round.step_func_obj is manager
    assert native.step_function.player_manager is manager
    assert native.rng is native.combat_ctx.rng
    for key, player in manager.player_states.items():
        assert player.pool_obj is manager.pool_obj
        assert manager.observation_states[key].player is player
        assert manager.action_handlers[key].player is player


def capture(session):
    return {
        "identities": (session.game, session.game.native, session.module_state,
                       session.python_rng, session.baseline_rng),
        "graph": pickle.dumps(session.game),
        "python_rng": random.getstate(), "numpy_rng": pickle.dumps(np.random.get_state()),
        "session_rng": pickle.dumps((session.python_rng, session.baseline_rng)),
        "logs": {str(path): path.read_bytes() for path in session.native_dir.rglob("*") if path.is_file()},
        "audit": session.audit_path.read_bytes(),
        "bindings": simulator_bindings(),
        "status": session.get_game_status(),
    }


def assert_unchanged(session, before):
    after = capture(session)
    for key in ("identities", "bindings"):
        assert all(a is b for a, b in zip(after.pop(key), before[key], strict=True))
    assert after == {key: value for key, value in before.items() if key not in {"identities", "bindings"}}
    assert_aliases(session.game)


def test_copy_preserves_renderer_history_and_native_aliases(session):
    from Simulator import config
    assert config.NUM_PLAYERS == 8
    original = session.game
    opening = session.get_decision()
    result = session.buy_unit(shop_slot=0)
    assert session.game is not original
    assert result["text"].startswith("action succeeded")
    assert "round " not in result["text"]
    assert session.get_decision() == result
    clone = deepcopy(session.game)
    assert_aliases(clone)
    with session.simulator_scope(game=clone):
        assert clone.observe()["text"] == result["text"]
    assert opening["text"].startswith("round 1")
    assert session.game.view.possible_agents == ["player_0"]
    assert not ({"_llm_caches", "actions_taken", "last_fight", "terminations"} & vars(session.game.native).keys())


def test_pass_budget_and_partial_end_turn_follow_native_action_count(session):
    for _ in range(14):
        with session.lifecycle_transaction(mutable=True):
            result = session._controlled([0, 0, 0], "pass")
        assert not result["start_turn"] and result["reward"] == 0
    assert session.game.native.action_count == 14
    assert session.get_game_status()["planning_budget"] == {"capacity": 15, "remaining": 1}
    result = session.end_turn()
    assert result["reward"] == 1 and result["start_turn"]
    assert session.game.native.action_count == 0
    assert session.get_last_fight()["round"] == 1
    rows = [json.loads(line) for line in session.audit_path.read_text().splitlines()]
    assert len([row for row in rows if row["event"] == "progression"]) == 15
    for _ in range(14):
        with session.lifecycle_transaction(mutable=True):
            session._controlled([0, 0, 0], "pass")
    with session.lifecycle_transaction(mutable=True):
        result = session._controlled([0, 0, 0], "pass")
    assert result["start_turn"] and result["reward"] == 1
    assert session.game.native.reward == 2
    assert session.get_last_fight()["round"] == 2


def test_masked_command_preserves_graph_native_bindings_logs_and_rng(session):
    before = capture(session)
    with pytest.raises(SessionError) as error:
        session.sell_unit(location={"kind": "bench", "slot": 8})
    assert error.value.code == "masked" and str(error.value) == "The action failed."
    assert_unchanged(session, before)


def test_reads_hide_dormant_players_and_preserve_native_state(session):
    before = pickle.dumps(session.game)
    rng = pickle.dumps((session.python_rng, session.baseline_rng))
    for _ in range(2):
        session.get_last_fight()
        session.campaign_schedule()
        assert "opponents" not in session.get_decision()["text"]
        assert [player["player_id"] for player in session.get_players()["players"]] == ["player_0"]
    # A dormant native board must not count as public pool knowledge.
    other = session.game.player_manager.player_states["player_1"]
    with session.simulator_scope():
        from Simulator.battle.champion import champion
        other.board[0][0] = champion("garen", stars=3)
    pool = session.get_champion_pool("garen")
    assert pool["visible_copies"] == 0
    other.board[0][0] = None
    assert pickle.dumps(session.game) == before
    assert pickle.dumps((session.python_rng, session.baseline_rng)) == rng


def test_native_loss_after_wins_uses_delta_and_retains_actual_final_fight(session):
    schema = next(tool.outputSchema for tool in SINGLE_PLAYER_TOOLS if tool.name == "get_last_fight")
    wins = 0
    for _ in range(45):
        previous_reward = session.game.native.reward
        result = session.end_turn()
        fight = session.get_last_fight()
        jsonschema.validate(fight, schema)
        assert result["reward"] == session.game.native.reward - previous_reward
        assert fight["won"] is (result["reward"] > 0)
        if result["terminal"]:
            break
        wins += 1
    assert wins > 1
    assert result["terminal"] and result["reward"] == -1
    assert session.game.native.reward > 0  # Cumulative reward cannot identify victory.
    assert session.game.episode_outcome == "lost"
    assert session.outcome["controlled_placement"] is None
    assert session.get_players()["players"][0]["status"] == "eliminated"
    assert session.terminal_snapshot["round"] == fight["round"]
    assert session.game.game_round.current_round == fight["round"] + 1
    assert f"round {fight['round']}" in result["text"].splitlines()
    assert session.terminal_snapshot["economy"]["health"] == 100
    assert fight["kind"] == "combat" and fight["enemy"]["board"]
    fight["enemy"]["board"].clear()
    assert session.get_last_fight()["enemy"]["board"]
    assert session.get_decision() == result
    assert result["mask"] == []
    with pytest.raises(SessionError) as error:
        session.end_turn()
    assert error.value.code == "game_terminal"


def test_native_minion_loss_ends_campaign_without_removing_native_player(session):
    # A board with no units loses the actual next PvE fight.
    install_units(session)
    result = session.end_turn()
    assert result["terminal"] and result["reward"] == -1
    assert session.get_last_fight() == {"game_id": session.game_id, "round": 1,
                                        "kind": "minion", "won": False, "enemy": None}
    assert session.game.native.PLAYER is session.game.player_manager.player_states["player_0"]
    assert session.own_inspection()["round"] == 1


@pytest.mark.parametrize("failure", ["adapter", "audit"])
def test_failed_candidate_rolls_back_and_replays_real_native_step(session, tmp_path, monkeypatch, failure):
    reference = GameSession(tmp_path / "reference-audit", tmp_path / "reference-native")
    reference.start_game(0, "single_player")
    before = capture(session)
    with monkeypatch.context() as patch:
        if failure == "adapter":
            original = SinglePlayer.step
            def fail_after_native(game, action):
                result = original(game, action)
                if result.get("start_turn"):
                    raise RuntimeError("injected after native combat")
                return result
            patch.setattr(SinglePlayer, "step", fail_after_native)
        else:
            def fail_replace(*args):
                raise OSError("injected audit failure")
            patch.setattr(os, "replace", fail_replace)
        with pytest.raises(SessionError):
            session.end_turn()
    assert_unchanged(session, before)
    assert session.end_turn() == reference.end_turn()
    assert_aliases(session.game)
    assert normalized_graph(session.game.native) == normalized_graph(reference.game.native)
    reference.close_game()


@pytest.mark.anyio
async def test_schema_failure_rolls_back_campaign_candidate(session, monkeypatch):
    before = capture(session)
    original = jsonschema.validate
    def reject_observation(instance, schema, *args, **kwargs):
        if "reward" in instance:
            raise jsonschema.ValidationError("injected observation failure")
        return original(instance, schema, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(jsonschema, "validate", reject_observation)
        result = await ToolCalls(session).call_tool("end_turn", {})
    assert result.isError and result.structuredContent["code"] == "internal_error"
    # ToolCalls separately audits the rejected request, preserving accepted game/log state.
    before["audit"] = session.audit_path.read_bytes()
    assert_unchanged(session, before)
    assert session.end_turn()["reward"] == 1


def test_schedule_uses_installed_methods_and_actual_generator_configs(session):
    schedule = session.campaign_schedule()
    rounds = session.game.game_round
    configs = [rounds.leveling_system.battle_generator.generator_config,
               *rounds.leveling_system.battle_levels[1:]]
    assert len(schedule) == len(rounds.game_rounds) - 1 == 45
    combats = [entry for entry in schedule if entry["kind"] == "combat"]
    assert len(combats) == len(configs) == 36
    for entry, methods in zip(schedule, rounds.game_rounds[1:], strict=True):
        names = {method.__name__ for method in methods}
        assert entry["carousel"] is ("carousel_round" in names)
        assert (entry["kind"] == "combat") is ("combat_round" in names)
    for entry, config in zip(combats, configs, strict=True):
        assert entry["enemy"]["level"] == config["current_level"]
        assert entry["enemy"]["items_vary"] == config["extra_randomness"]
        assert entry["enemy"]["items_per_unit"] == config["num_items"]
    initial = deepcopy(schedule)
    schedule[0]["round"] = -1
    session.end_turn()
    assert session.campaign_schedule() == initial
    text = campaign_text(initial)
    assert "Base completed items" in text
    assert "item count varies by up to 1 from the base, clipped to 0 through 3" in text


@pytest.mark.anyio
async def test_sdk_process_runs_to_native_loss_and_retains_terminal_views(tmp_path):
    async with client(tmp_path, TFT_MCP_MODE="single_player") as sdk:
        for _ in range(45):
            result = await sdk.call_tool("end_turn", {})
            assert not result.isError
            if result.structuredContent["terminal"]:
                break
        assert result.structuredContent["terminal"]
        assert result.structuredContent["reward"] == -1
        terminal = await sdk.call_tool("get_decision", {})
        fight = await sdk.call_tool("get_last_fight", {})
        refused = await sdk.call_tool("end_turn", {})
        assert terminal.structuredContent == result.structuredContent
        assert fight.structuredContent["won"] is False
        assert refused.isError and refused.structuredContent["code"] == "game_terminal"
    assert '"event": "game_closed"' in (tmp_path / "audit.jsonl").read_text()


def final_round_fixture(session):
    # Arrange a late-campaign own board and the actual final curriculum entry.
    # No native class, rule, schedule or method is replaced.
    units = ["azir", "ezreal", "kayn", "leesin", "lillia", "sett", "yone", "zilean", "shen"]
    player = install_units(session, board=[
        ((i % 7, i // 7), name, 3, ["infinity_edge", "hand_of_justice", "quicksilver"])
        for i, name in enumerate(units)
    ])
    player.level = player.max_units = 9
    session.game.game_round.current_round = len(session.game.game_round.game_rounds) - 1
    with session.simulator_scope():
        leveling = session.game.game_round.leveling_system
        for _ in range(len(leveling.battle_levels) - 1):
            leveling.single_player_level_up()


@pytest.mark.skipif(not __debug__, reason="The native assertion is disabled by Python optimization.")
def test_native_late_campaign_embedding_limit_is_reported_and_rolled_back(session):
    final_round_fixture(session)
    before = capture(session)
    with pytest.raises(SessionError) as error:
        session.end_turn()
    assert error.value.code == "internal_error"
    assert isinstance(error.value.__cause__, AssertionError)
    assert_unchanged(session, before)


def test_final_native_victory_under_optimized_python(tmp_path):
    # Native ObservationToken asserts player.round < 40 although its campaign
    # has 45 rounds. -O tests the real final-win branch without patching it.
    # This proves adapter semantics, not normal-runtime campaign acceptance.
    code = """
import json
from pathlib import Path
import sys
from tft_mcp.session import GameSession
from test_single_player_adapter import final_round_fixture, assert_aliases
root = Path(sys.argv[1])
session = GameSession(root / 'audit', root / 'native')
session.start_game(0, 'single_player')
final_round_fixture(session)
observed = session.end_turn()
print(json.dumps({'observation': observed, 'outcome': session.outcome,
                  'snapshot_round': session.terminal_snapshot['round'],
                  'fight': session.get_last_fight(), 'native_round': session.game.game_round.current_round}))
assert_aliases(session.game)
session.close_game()
"""
    environment = dict(os.environ)
    environment.pop("APPIMAGE", None)
    environment["PYTHONPATH"] = os.pathsep.join((str(Path(__file__).parents[1] / "src"), str(Path(__file__).parent)))
    result = subprocess.run([sys.executable, "-O", "-c", code, str(tmp_path)],
                            env=environment, cwd=tmp_path, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["observation"]["terminal"] and receipt["observation"]["reward"] == 1
    assert receipt["outcome"]["controlled_placement"] == 1
    assert receipt["snapshot_round"] == receipt["fight"]["round"] == 45
    assert receipt["native_round"] == 46 and receipt["fight"]["won"] is True

"""Protocol checks for an equip the mask rejects."""
import pytest

from support import memory_client, session_fixture


@pytest.mark.anyio
async def test_equip_mask_and_schema(tmp_path):
    session = session_fixture(tmp_path)
    async with memory_client(session) as sdk:
        tools = {tool.name: tool for tool in (await sdk.list_tools()).tools}
        assert 'mask' in tools['equip_item'].outputSchema['properties']
        result = await sdk.call_tool('equip_item', {'item_slot': 0, 'target': {'kind': 'bench', 'slot': 0}})
        assert result.isError and result.structuredContent['code'] == 'masked'
        assert session.game.actions_taken['player_0'] == 0

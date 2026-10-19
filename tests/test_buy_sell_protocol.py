"""Protocol checks for shop commands and masked rejections."""
import jsonschema
import pytest

from support import memory_client, session_fixture


@pytest.mark.anyio
async def test_buy_schema_and_masked_sale(tmp_path):
    session = session_fixture(tmp_path)
    async with memory_client(session) as sdk:
        tools = {tool.name: tool for tool in (await sdk.list_tools()).tools}
        bought = await sdk.call_tool('buy_unit', {'shop_slot': 0})
        assert not bought.isError, bought.structuredContent
        jsonschema.validate(bought.structuredContent, tools['buy_unit'].outputSchema)
        assert bought.structuredContent['text'].startswith('action succeeded')
        rejected = await sdk.call_tool('sell_unit', {'location': {'kind': 'bench', 'slot': 8}})
        assert rejected.isError and rejected.structuredContent['code'] == 'masked'
        assert session.game.actions_taken['player_0'] == 1

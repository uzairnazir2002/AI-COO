from app.domain.services.bank_provider import StubBankProvider


async def test_stub_bank_provider_link_exchange_and_sync():
    provider = StubBankProvider()
    link = await provider.create_link_token(org_id="org123", user_id="user123")
    assert link["link_token"].startswith("stub-link-")

    exchange = await provider.exchange_public_token(public_token="pub_test")
    assert exchange.external_item_id.startswith("stub-item-")
    assert len(exchange.accounts) >= 1

    first_sync = await provider.sync_transactions(access_token_ref=exchange.access_token_ref, cursor=None)
    assert first_sync.has_more is False
    assert first_sync.next_cursor is not None
    assert len(first_sync.transactions) >= 1

    second_sync = await provider.sync_transactions(
        access_token_ref=exchange.access_token_ref,
        cursor=first_sync.next_cursor,
    )
    assert second_sync.transactions == []

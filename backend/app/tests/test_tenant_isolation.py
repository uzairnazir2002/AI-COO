from uuid import uuid4


def test_tenant_ids_not_equal():
    org_a = uuid4()
    org_b = uuid4()
    assert org_a != org_b

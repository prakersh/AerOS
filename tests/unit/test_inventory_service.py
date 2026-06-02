"""Tests for inventory_service — SKU and category listing."""

import pytest

from aeros.models.organization import Organization, OrgType
from aeros.models.sku import SKU, Category
from aeros.services import inventory_service


@pytest.fixture
def org(session):
    o = Organization(name="InvTestOrg", type=OrgType.BUYER)
    session.add(o)
    session.commit()
    session.refresh(o)
    return o


@pytest.fixture
def categories(session):
    c1 = Category(name="Vegetables", sort_order=1)
    c2 = Category(name="Fruits", sort_order=2)
    session.add(c1)
    session.add(c2)
    session.commit()
    session.refresh(c1)
    session.refresh(c2)
    return [c1, c2]


@pytest.fixture
def skus(session, org, categories):
    s1 = SKU(org_id=org.id, code="V001", name="Tomato", category_id=categories[0].id, unit="kg")
    s2 = SKU(org_id=org.id, code="V002", name="Potato", category_id=categories[0].id, unit="kg")
    s3 = SKU(org_id=org.id, code="F001", name="Apple", category_id=categories[1].id, unit="kg")
    session.add(s1)
    session.add(s2)
    session.add(s3)
    session.commit()
    session.refresh(s1)
    session.refresh(s2)
    session.refresh(s3)
    return [s1, s2, s3]


class TestListCategories:
    def test_returns_all_categories(self, session, categories):
        result = inventory_service.list_categories(session)
        assert len(result) == 2

    def test_ordered_by_sort_order(self, session, categories):
        result = inventory_service.list_categories(session)
        assert result[0].name == "Vegetables"
        assert result[1].name == "Fruits"


class TestListSkus:
    def test_returns_all_skus(self, session, org, skus):
        result = inventory_service.list_skus(session, org.id)
        assert len(result) == 3

    def test_filter_by_category(self, session, org, skus, categories):
        result = inventory_service.list_skus(session, org.id, category_id=categories[0].id)
        assert len(result) == 2
        names = {s.name for s in result}
        assert "Tomato" in names
        assert "Potato" in names

    def test_ordered_by_name(self, session, org, skus):
        result = inventory_service.list_skus(session, org.id)
        names = [s.name for s in result]
        assert names == sorted(names)


class TestGetSku:
    def test_existing_sku(self, session, skus):
        result = inventory_service.get_sku(session, skus[0].id)
        assert result is not None
        assert result.name == "Tomato"

    def test_nonexistent_sku(self, session):
        result = inventory_service.get_sku(session, 99999)
        assert result is None


class TestSearchSkus:
    def test_search_match(self, session, org, skus):
        result = inventory_service.search_skus(session, org.id, "Tom")
        assert len(result) == 1
        assert result[0].name == "Tomato"

    def test_search_no_match(self, session, org, skus):
        result = inventory_service.search_skus(session, org.id, "xyz")
        assert result == []

    def test_search_case_insensitive(self, session, org, skus):
        # SQL contains is typically case-insensitive in SQLite
        result = inventory_service.search_skus(session, org.id, "pot")
        assert len(result) >= 1

    def test_search_by_code(self, session, org, skus):
        result = inventory_service.search_skus(session, org.id, "V001")
        assert result and result[0].code == "V001"

    def test_search_fuzzy_misspelling(self, session, org, skus):
        # "Tomatoe" is a misspelling of "Tomato".
        result = inventory_service.search_skus(session, org.id, "Tomatoe")
        assert result and result[0].name == "Tomato"


class TestResolveSkuRef:
    def test_by_integer_id(self, session, org, skus):
        match, candidates = inventory_service.resolve_sku_ref(session, org.id, skus[0].id)
        assert match and match.name == "Tomato"
        assert candidates == []

    def test_by_numeric_string_id(self, session, org, skus):
        match, _ = inventory_service.resolve_sku_ref(session, org.id, str(skus[0].id))
        assert match and match.name == "Tomato"

    def test_by_code_case_insensitive(self, session, org, skus):
        match, candidates = inventory_service.resolve_sku_ref(session, org.id, "v001")
        assert match and match.code == "V001"
        assert candidates == []

    def test_by_name(self, session, org, skus):
        match, _ = inventory_service.resolve_sku_ref(session, org.id, "Apple")
        assert match and match.code == "F001"

    def test_ambiguous_returns_candidates(self, session, org, categories):
        # Two equally-plausible "milk" matches -> no confident winner.
        cat = categories[0].id
        a = SKU(org_id=org.id, code="D1", name="Toned Milk", category_id=cat, unit="ltr")
        b = SKU(org_id=org.id, code="D2", name="Full Cream Milk", category_id=cat, unit="ltr")
        session.add(a)
        session.add(b)
        session.commit()
        match, candidates = inventory_service.resolve_sku_ref(session, org.id, "milk")
        assert match is None
        assert {c.name for c in candidates} == {"Toned Milk", "Full Cream Milk"}

    def test_no_match(self, session, org, skus):
        match, candidates = inventory_service.resolve_sku_ref(session, org.id, "xyzzy")
        assert match is None
        assert candidates == []

    def test_other_org_id_rejected(self, session, org, skus):
        match, _ = inventory_service.resolve_sku_ref(session, 99999, skus[0].id)
        assert match is None

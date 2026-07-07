"""Tests for LinkedIn provider factory and MockLinkedInProvider."""

import pytest
import pytest_asyncio

from providers import create_linkedin_provider
from providers.mock import MockLinkedInProvider
from providers.models import SearchCriteria


# ─── Factory ─────────────────────────────────────────────────────────────────


class TestProviderFactory:
    def test_create_mock_provider(self):
        p = create_linkedin_provider("mock", {})
        assert isinstance(p, MockLinkedInProvider)

    def test_create_rapidapi_provider(self):
        from providers.rapidapi import RapidAPILinkedInProvider

        p = create_linkedin_provider("rapidapi", {"LINKEDIN_API_KEY": "test"})
        assert isinstance(p, RapidAPILinkedInProvider)

    def test_create_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LinkedIn provider"):
            create_linkedin_provider("nonexistent", {})


# ─── MockLinkedInProvider ─────────────────────────────────────────────────────


class TestMockLinkedInProvider:
    @pytest.mark.asyncio
    async def test_search_no_filter_returns_all(self, mock_provider):
        results = await mock_provider.search_people(SearchCriteria())
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_search_filter_by_title(self, mock_provider):
        results = await mock_provider.search_people(
            SearchCriteria(title="VP")
        )
        assert len(results) >= 1
        assert all("VP" in p.title for p in results)

    @pytest.mark.asyncio
    async def test_search_filter_by_industry(self, mock_provider):
        results = await mock_provider.search_people(
            SearchCriteria(industry="Sales")
        )
        assert len(results) >= 1
        assert all("Sales" in p.industry for p in results)

    @pytest.mark.asyncio
    async def test_search_filter_by_location(self, mock_provider):
        results = await mock_provider.search_people(
            SearchCriteria(location="Seattle")
        )
        assert len(results) >= 1
        assert all("Seattle" in p.location for p in results)

    @pytest.mark.asyncio
    async def test_search_filter_by_company(self, mock_provider):
        results = await mock_provider.search_people(
            SearchCriteria(company="TechCorp")
        )
        assert len(results) == 1
        assert results[0].company == "TechCorp"

    @pytest.mark.asyncio
    async def test_search_filter_by_keywords(self, mock_provider):
        results = await mock_provider.search_people(
            SearchCriteria(keywords=["cloud"])
        )
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_max_results(self, mock_provider):
        results = await mock_provider.search_people(
            SearchCriteria(max_results=2)
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_profile_known(self, mock_provider):
        p = await mock_provider.get_profile("mock-001")
        assert p.name == "Alice Johnson"
        assert p.id == "mock-001"

    @pytest.mark.asyncio
    async def test_get_profile_unknown(self, mock_provider):
        p = await mock_provider.get_profile("nonexistent-id")
        assert p.name == "Unknown User"

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_provider):
        result = await mock_provider.send_message("mock-001", "Hello!")
        assert result.success is True
        assert result.message_id is not None

    @pytest.mark.asyncio
    async def test_get_conversations_no_messages(self, mock_provider):
        convos = await mock_provider.get_conversations()
        assert convos == []

    @pytest.mark.asyncio
    async def test_get_conversations_after_send(self, mock_provider):
        await mock_provider.send_message("mock-001", "Hi Alice")
        convos = await mock_provider.get_conversations()
        assert len(convos) == 1
        assert convos[0].participant_name == "Alice Johnson"
        assert len(convos[0].messages) >= 1

    @pytest.mark.asyncio
    async def test_reply_to_conversation(self, mock_provider):
        result = await mock_provider.reply_to_conversation("conv-001", "Thanks!")
        assert result.success is True


# ─── Pydantic Models ─────────────────────────────────────────────────────────


class TestModels:
    def test_search_criteria_defaults(self):
        c = SearchCriteria()
        assert c.max_results == 25
        assert c.keywords == []

    def test_search_criteria_with_values(self):
        c = SearchCriteria(title="CTO", industry="Finance", max_results=10)
        assert c.title == "CTO"
        assert c.industry == "Finance"
        assert c.max_results == 10

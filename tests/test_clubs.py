import uuid

import pytest

from app.schemas import OpenClubRequest


@pytest.fixture(scope="function")
def club_payload():
    return OpenClubRequest(name="Test Club").model_dump()


class TestOpenClub:
    async def test_response_status_code(self, superuser_client, club_payload):
        response = await superuser_client.post("/clubs/", json=club_payload)
        assert response.status_code == 201

    async def test_club_added(self, superuser_client, club_payload):
        response = await superuser_client.post("/clubs/", json=club_payload)
        club_id = response.json()

        # Test it was added
        response = await superuser_client.get(f"/clubs/{club_id}")
        assert response.status_code == 200

        club = response.json()
        assert club["id"] == club_id

    async def test_owner_is_member(self, superuser_client, superuser, club_payload):
        response = await superuser_client.post("/clubs/", json=club_payload)
        club_id = response.json()

        # Owner is also a member
        response = await superuser_client.get(f"/clubs/{club_id}/members")
        assert response.status_code == 200

        member_ids = [uuid.UUID(v["id"]) for v in response.json()]
        assert superuser.id in member_ids

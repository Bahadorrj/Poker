import uuid

import pytest

from app.models import Club, club_members
from app.schemas import OpenClubRequest


@pytest.fixture(scope="function")
def club_payload():
    return OpenClubRequest(name="Test Club").model_dump()


@pytest.mark.asyncio
class TestOpenClub:
    async def test_response_status_code(self, client, club_payload):
        response = await client.post("/clubs/", json=club_payload)
        assert response.status_code == 201

    async def test_club_is_added(self, client, club_payload):
        response = await client.post("/clubs/", json=club_payload)
        club_id = response.json()

        # Test it was added
        response = await client.get(f"/clubs/{club_id}")
        assert response.status_code == 200

        club = response.json()
        assert club["id"] == club_id

    async def test_owner_is_member(self, client, test_user, club_payload):
        response = await client.post("/clubs/", json=club_payload)
        club_id = response.json()

        # Owner is also a member
        response = await client.get(f"/clubs/{club_id}/members")
        assert response.status_code == 200

        member_ids = [uuid.UUID(v["id"]) for v in response.json()]
        assert test_user.id in member_ids


@pytest.mark.asyncio
class TestGetClubs:
    async def test_no_clubs(self, client):
        response = await client.get("/clubs/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_with_added_club(self, client, club_payload):
        response = await client.post("/clubs/", json=club_payload)
        club_id = response.json()

        response = await client.get("/clubs/")
        assert response.status_code == 200
        assert response.json() != []
        assert response.json()[0]["id"] == club_id


@pytest.mark.asyncio
async def test_get_club(client, club_payload):
    response = await client.post("/clubs/", json=club_payload)
    club_id = response.json()

    response = await client.get(f"/clubs/{club_id}")
    assert response.status_code == 200


@pytest.mark.asyncio
class TestDeleteClub:
    async def test_forbidden(self, client, db_session, other_user):
        club_id = uuid.uuid4()
        club = Club(
            id=club_id,
            name="Test Club",
            owner_id=other_user.id,
        )
        db_session.add(club)
        await db_session.commit()

        response = await client.delete(f"/clubs/{club_id}")

        assert response.status_code == 403

    async def test_success_current_user(self, client, club_payload):
        response = await client.post("/clubs/", json=club_payload)
        assert response.status_code == 201

        club_id = response.json()

        response = await client.delete(f"/clubs/{club_id}")
        assert response.status_code == 204

    async def test_success_superuser(self, superuser_client, db_session, other_user):
        club_id = uuid.uuid4()
        club = Club(
            id=club_id,
            name="Test Club",
            owner_id=other_user.id,
        )
        db_session.add(club)
        await db_session.commit()

        response = await superuser_client.delete(f"/clubs/{club_id}")

        assert response.status_code == 204


@pytest.mark.asyncio
class TestJoinClub:
    async def test_member_already_exists(self, client, club_payload):
        response = await client.post("/clubs/", json=club_payload)
        club_id = response.json()

        response = await client.post(f"/clubs/{club_id}/members")
        assert response.status_code == 409

    async def test_success(self, db_session, other_user, client):
        club_id = uuid.uuid4()
        club = Club(
            id=club_id,
            name="Test Club",
            owner_id=other_user.id,
        )
        db_session.add(club)
        await db_session.commit()

        response = await client.post(f"/clubs/{club_id}/members")
        assert response.status_code == 200


async def test_get_club_members(db_session, test_user, client):
    club_id = uuid.uuid4()
    club = Club(
        id=club_id,
        name="Test Club",
        owner_id=test_user.id,
    )
    db_session.add(club)
    await db_session.commit()

    await db_session.execute(
        club_members.insert().values(club_id=club_id, user_id=test_user.id)
    )
    await db_session.commit()

    response = await client.get(f"/clubs/{club_id}/members")
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(test_user.id)

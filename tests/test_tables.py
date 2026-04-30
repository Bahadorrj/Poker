from app.routers.tables import get_transactions
from app.schemas import PlayerResponse
import uuid


def make_player(username: str, buy_in: int, cash_out: int) -> PlayerResponse:
    return PlayerResponse(
        id=uuid.uuid4(),
        table_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        username=username,
        buy_in=buy_in,
        cash_out=cash_out,
    )


def test_no_players():
    assert get_transactions([]) == []


def test_balanced_two_players():
    # erfan bought in 100, cashed out 50 → lost 50
    # bahador bought in 100, cashed out 150 → won 50
    players = [
        make_player("erfan", buy_in=100, cash_out=50),
        make_player("bahador", buy_in=100, cash_out=150),
    ]
    transactions = get_transactions(players)
    assert len(transactions) == 1
    assert transactions[0].giver == "erfan"
    assert transactions[0].getter == "bahador"
    assert transactions[0].money == 50


def test_all_even():
    # Everyone breaks even, no transactions needed
    players = [
        make_player("erfan", buy_in=100, cash_out=100),
        make_player("bahador", buy_in=200, cash_out=200),
    ]
    assert get_transactions(players) == []


def test_three_players():
    players = [
        make_player("erfan", buy_in=100, cash_out=0),  # lost 100
        make_player("bahador", buy_in=100, cash_out=0),  # lost 100
        make_player("sardar", buy_in=100, cash_out=300),  # won 200
    ]
    transactions = get_transactions(players)
    total_paid = sum(t.money for t in transactions)
    assert total_paid == 200
    assert all(t.getter == "sardar" for t in transactions)

"""Listing journal entries by activity, plus editing and deleting one entry."""

from httpx import AsyncClient

from tests.conftest import make_activity, make_log


async def test_filter_logs_by_activity(alice: AsyncClient) -> None:
    running = await make_activity(alice, "Running", "km")
    reading = await make_activity(alice, "Reading", "pages")
    first = await make_log(alice, running, "3.00")
    await make_log(alice, reading, "20.00")
    second = await make_log(alice, running, "4.50")

    filtered = (await alice.get("/logs", params={"activity_id": running})).json()
    everything = (await alice.get("/logs")).json()

    assert [item["id"] for item in filtered] == [second, first]
    assert {item["activity_name"] for item in filtered} == {"Running"}
    assert len(everything) == 3


async def test_filter_pages_within_one_activity(alice: AsyncClient) -> None:
    running = await make_activity(alice, "Running", "km")
    reading = await make_activity(alice, "Reading", "pages")
    ids = []
    for _ in range(3):
        ids.append(await make_log(alice, running))
        await make_log(alice, reading)

    page = (
        await alice.get("/logs", params={"activity_id": running, "limit": 2, "offset": 1})
    ).json()

    assert [item["id"] for item in page] == [ids[1], ids[0]]


async def test_filter_by_another_users_activity_is_empty(
    alice: AsyncClient, bob: AsyncClient
) -> None:
    running = await make_activity(alice)
    await make_log(alice, running)

    response = await bob.get("/logs", params={"activity_id": running})

    assert response.status_code == 200
    assert response.json() == []


async def test_filter_rejects_a_non_positive_id(alice: AsyncClient) -> None:
    assert (await alice.get("/logs", params={"activity_id": 0})).status_code == 422


async def test_update_log_amount(alice: AsyncClient) -> None:
    running = await make_activity(alice)
    log_id = await make_log(alice, running, "5.00")

    response = await alice.patch(f"/logs/{log_id}", json={"amount": "7.25"})

    assert response.status_code == 200
    assert response.json()["amount"] == "7.25"


async def test_delete_log_keeps_the_activity(alice: AsyncClient) -> None:
    running = await make_activity(alice)
    log_id = await make_log(alice, running)

    response = await alice.delete(f"/logs/{log_id}")

    assert response.status_code == 204
    assert (await alice.get("/logs")).json() == []
    assert (await alice.get(f"/activities/{running}")).json()["entries_count"] == 0


async def test_another_users_log_looks_missing(alice: AsyncClient, bob: AsyncClient) -> None:
    running = await make_activity(alice)
    log_id = await make_log(alice, running)

    assert (await bob.patch(f"/logs/{log_id}", json={"amount": "1.00"})).status_code == 404
    assert (await bob.delete(f"/logs/{log_id}")).status_code == 404
    assert len((await alice.get("/logs")).json()) == 1

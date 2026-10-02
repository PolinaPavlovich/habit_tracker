"""Reading, editing and deleting a single activity."""

from httpx import AsyncClient

from tests.conftest import make_activity, make_log


async def test_get_activity_reports_its_entry_count(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)
    await make_log(alice, activity_id)
    await make_log(alice, activity_id)

    response = await alice.get(f"/activities/{activity_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Running"
    assert body["unit"] == "km"
    assert body["entries_count"] == 2


async def test_entry_count_ignores_other_activities(alice: AsyncClient) -> None:
    running = await make_activity(alice, "Running", "km")
    reading = await make_activity(alice, "Reading", "pages")
    await make_log(alice, reading)

    response = await alice.get(f"/activities/{running}")

    assert response.json()["entries_count"] == 0


async def test_rename_activity(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)

    response = await alice.patch(f"/activities/{activity_id}", json={"name": "Jogging"})

    assert response.status_code == 200
    assert response.json()["name"] == "Jogging"
    assert response.json()["unit"] == "km"
    listed = (await alice.get("/activities")).json()
    assert [item["name"] for item in listed] == ["Jogging"]


async def test_change_unit_only(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)

    response = await alice.patch(f"/activities/{activity_id}", json={"unit": "miles"})

    assert response.status_code == 200
    assert response.json()["name"] == "Running"
    assert response.json()["unit"] == "miles"


async def test_rename_shows_up_in_history_and_summary(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)
    await make_log(alice, activity_id)

    await alice.patch(f"/activities/{activity_id}", json={"name": "Jogging", "unit": "mi"})

    history = (await alice.get("/logs")).json()
    assert history[0]["activity_name"] == "Jogging"
    assert history[0]["unit"] == "mi"
    summary = (await alice.get("/logs/summary")).json()
    assert summary["items"][0]["activity_name"] == "Jogging"


async def test_rename_to_a_name_already_taken_is_409(alice: AsyncClient) -> None:
    await make_activity(alice, "Reading", "pages")
    running = await make_activity(alice, "Running", "km")

    response = await alice.patch(f"/activities/{running}", json={"name": "Reading"})

    assert response.status_code == 409
    assert response.json()["detail"] == "You already have an activity named 'Reading'."


async def test_rename_to_own_current_name_is_allowed(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)

    response = await alice.patch(
        f"/activities/{activity_id}", json={"name": "Running", "unit": "miles"}
    )

    assert response.status_code == 200
    assert response.json()["unit"] == "miles"


async def test_two_users_may_rename_to_the_same_name(alice: AsyncClient, bob: AsyncClient) -> None:
    await make_activity(alice, "Reading", "pages")
    bobs = await make_activity(bob, "Running", "km")

    response = await bob.patch(f"/activities/{bobs}", json={"name": "Reading"})

    assert response.status_code == 200


async def test_update_rejects_empty_body(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)

    response = await alice.patch(f"/activities/{activity_id}", json={})

    assert response.status_code == 422


async def test_update_rejects_unknown_field(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)

    response = await alice.patch(f"/activities/{activity_id}", json={"user_id": 99})

    assert response.status_code == 422


async def test_update_rejects_null_and_blank(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)

    assert (await alice.patch(f"/activities/{activity_id}", json={"name": None})).status_code == 422
    assert (await alice.patch(f"/activities/{activity_id}", json={"name": ""})).status_code == 422
    assert (
        await alice.patch(f"/activities/{activity_id}", json={"unit": "x" * 33})
    ).status_code == 422


async def test_delete_activity_removes_its_entries(alice: AsyncClient) -> None:
    running = await make_activity(alice, "Running", "km")
    reading = await make_activity(alice, "Reading", "pages")
    await make_log(alice, running)
    await make_log(alice, running)
    kept = await make_log(alice, reading)

    response = await alice.delete(f"/activities/{running}")

    assert response.status_code == 204
    assert response.content == b""
    assert (await alice.get(f"/activities/{running}")).status_code == 404
    assert [item["name"] for item in (await alice.get("/activities")).json()] == ["Reading"]
    assert [item["id"] for item in (await alice.get("/logs")).json()] == [kept]


async def test_deleted_name_can_be_reused(alice: AsyncClient) -> None:
    activity_id = await make_activity(alice)
    await alice.delete(f"/activities/{activity_id}")

    response = await alice.post("/activities", json={"name": "Running", "unit": "km"})

    assert response.status_code == 201


async def test_missing_activity_is_404(alice: AsyncClient) -> None:
    for response in (
        await alice.get("/activities/999"),
        await alice.patch("/activities/999", json={"name": "x"}),
        await alice.delete("/activities/999"),
    ):
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity with id 999 does not exist."


async def test_another_users_activity_looks_missing(alice: AsyncClient, bob: AsyncClient) -> None:
    activity_id = await make_activity(alice)
    await make_log(alice, activity_id)
    missing = f"Activity with id {activity_id} does not exist."

    for response in (
        await bob.get(f"/activities/{activity_id}"),
        await bob.patch(f"/activities/{activity_id}", json={"name": "Stolen"}),
        await bob.delete(f"/activities/{activity_id}"),
    ):
        assert response.status_code == 404
        assert response.json()["detail"] == missing

    untouched = (await alice.get(f"/activities/{activity_id}")).json()
    assert untouched["name"] == "Running"
    assert untouched["entries_count"] == 1

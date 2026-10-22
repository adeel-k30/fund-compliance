import uuid
import pytest_asyncio
from app.db.models import ValidationIssue


# ---------------------------------------------------------------------------
# Local helper — not a fixture, just reduces repetition when seeding issues
# ---------------------------------------------------------------------------

def _make_issue(upload_id: str, isin: str | None, instrument_name: str | None, field_code: str = "07010") -> ValidationIssue:
    return ValidationIssue(
        id=str(uuid.uuid4()),
        upload_id=upload_id,
        row_index=1,
        isin=isin,
        instrument_name=instrument_name,
        field_code=field_code,
        field_label="Some Field",
        rule_type="mandatory",
        message="Field is required but missing.",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_issues_unauthenticated(client, seeded_upload):
    response = await client.get(f"/validate/uploads/{seeded_upload.id}/issues")
    assert response.status_code == 401


async def test_issues_upload_not_found(client, auth_headers):
    random_id = str(uuid.uuid4())
    response = await client.get(f"/validate/uploads/{random_id}/issues", headers=auth_headers)
    assert response.status_code == 404


async def test_issues_tenant_isolation(client, db_session, seeded_upload):
    """
    A second user registers under a different org (different client_id).
    They must not be able to see the first user's upload.
    Expect 404 — the endpoint intentionally does not reveal whether the upload exists.
    """
    second_user = {
        "organisation_name": "Rival Asset Management",
        "email": "analyst@rival.com",
        "password": "rivalpass123",
    }
    await client.post("/auth/register", json=second_user)
    login = await client.post("/auth/token", data={
        "username": second_user["email"],
        "password": second_user["password"],
    })
    second_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get(f"/validate/uploads/{seeded_upload.id}/issues", headers=second_headers)
    assert response.status_code == 404


async def test_issues_empty(client, auth_headers, seeded_upload):
    """Upload exists but has no ValidationIssue rows — should return empty groups."""
    response = await client.get(f"/validate/uploads/{seeded_upload.id}/issues", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["upload_id"] == seeded_upload.id
    assert data["total_issues"] == 0
    assert data["groups"] == []


async def test_issues_grouped_by_isin(client, db_session, auth_headers, seeded_upload):
    """
    3 issues seeded: 2 for ISIN_A, 1 for ISIN_B.
    Expect 2 groups with correct per-group issue counts.
    """
    isin_a = "IE00B4L5Y983"
    isin_b = "LU0290358497"
    db_session.add(_make_issue(seeded_upload.id, isin_a, "Blackrock World Fund", field_code="07010"))
    db_session.add(_make_issue(seeded_upload.id, isin_a, "Blackrock World Fund", field_code="08070"))
    db_session.add(_make_issue(seeded_upload.id, isin_b, "Vanguard Global Equity", field_code="07010"))
    await db_session.flush()

    response = await client.get(f"/validate/uploads/{seeded_upload.id}/issues", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_issues"] == 3
    assert len(data["groups"]) == 2

    groups_by_isin = {g["isin"]: g for g in data["groups"]}
    assert len(groups_by_isin[isin_a]["issues"]) == 2
    assert len(groups_by_isin[isin_b]["issues"]) == 1


async def test_issues_null_isin_grouped(client, db_session, auth_headers, seeded_upload):
    """
    Issues where isin is None should all land in a single group with isin=null.
    """
    db_session.add(_make_issue(seeded_upload.id, None, None, field_code="07010"))
    db_session.add(_make_issue(seeded_upload.id, None, None, field_code="08070"))
    await db_session.flush()

    response = await client.get(f"/validate/uploads/{seeded_upload.id}/issues", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_issues"] == 2
    assert len(data["groups"]) == 1
    assert data["groups"][0]["isin"] is None
    assert len(data["groups"][0]["issues"]) == 2


async def test_issues_response_structure(client, db_session, auth_headers, seeded_upload):
    """
    Verify the full shape of a single-issue response — every field present
    and matches the seeded values exactly.
    """
    issue = ValidationIssue(
        id=str(uuid.uuid4()),
        upload_id=seeded_upload.id,
        row_index=3,
        isin="IE00B4L5Y983",
        instrument_name="Blackrock World Fund",
        field_code="07010",
        field_label="Target Market — Return Profile",
        rule_type="mandatory",
        message="Field is required but missing.",
    )
    db_session.add(issue)
    await db_session.flush()

    response = await client.get(f"/validate/uploads/{seeded_upload.id}/issues", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["upload_id"] == seeded_upload.id
    assert data["total_issues"] == 1

    group = data["groups"][0]
    assert group["isin"] == "IE00B4L5Y983"
    assert group["instrument_name"] == "Blackrock World Fund"
    assert len(group["issues"]) == 1

    i = group["issues"][0]
    assert i["id"] == issue.id
    assert i["row_index"] == 3
    assert i["field_code"] == "07010"
    assert i["field_label"] == "Target Market — Return Profile"
    assert i["rule_type"] == "mandatory"
    assert i["message"] == "Field is required but missing."
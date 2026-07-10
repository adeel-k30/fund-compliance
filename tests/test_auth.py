# ---------- Registration tests ----------

async def test_register_valid(client):
    response = await client.post("/auth/register", json={
        "organisation_name": "Aberdeen Asset Management",
        "email": "analyst@aberdeen.com",
        "password": "securepass123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "analyst@aberdeen.com"
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_duplicate_email(client, registered_user):
    # registered_user already created test@testorg.com
    # try to register the same email again
    response = await client.post("/auth/register", json={
        "organisation_name": "Another Org",
        "email": registered_user["email"],  # duplicate
        "password": "differentpass123"
    })
    assert response.status_code == 400


async def test_register_short_password(client):
    response = await client.post("/auth/register", json={
        "organisation_name": "Test Org",
        "email": "shortpass@test.com",
        "password": "short"  # less than 8 chars
    })
    assert response.status_code == 422  # Pydantic validation error


async def test_register_invalid_email(client):
    response = await client.post("/auth/register", json={
        "organisation_name": "Test Org",
        "email": "not-an-email",
        "password": "validpass123"
    })
    assert response.status_code == 422


# ---------- Login tests ----------

async def test_login_correct_credentials(client, registered_user):
    response = await client.post("/auth/token", data={
        "username": registered_user["email"],
        "password": registered_user["password"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client, registered_user):
    response = await client.post("/auth/token", data={
        "username": registered_user["email"],
        "password": "wrongpassword"
    })
    assert response.status_code == 401


async def test_login_unknown_email(client):
    response = await client.post("/auth/token", data={
        "username": "nonexistent@test.com",
        "password": "anypassword"
    })
    assert response.status_code == 401


async def test_protected_endpoint_no_token(client):
    response = await client.get("/validate/uploads")
    assert response.status_code == 401


async def test_protected_endpoint_with_token(client, auth_headers):
    response = await client.get("/validate/uploads", headers=auth_headers)
    assert response.status_code == 200
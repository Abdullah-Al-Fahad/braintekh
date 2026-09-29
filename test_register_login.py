import requests

print("Registering new user...")
resp = requests.post("http://localhost:8000/api/v1/auth/register/", json={
    "first_name": "Test",
    "last_name": "User",
    "email": "test.user@example.com",
    "password": "Password123!"
})
print("Register:", resp.status_code, resp.text)

print("Logging in...")
resp = requests.post("http://localhost:8000/api/v1/auth/login/", json={
    "email": "test.user@example.com",
    "password": "Password123!"
})
print("Login:", resp.status_code, resp.text)

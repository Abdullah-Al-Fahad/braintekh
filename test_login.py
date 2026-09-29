import requests
resp = requests.post("http://localhost:8000/api/v1/auth/login/", json={
    "email": "admin@damani.ai",
    "password": "AdminPassword123!"
})
print("STATUS:", resp.status_code)
print("RESPONSE:", resp.json())

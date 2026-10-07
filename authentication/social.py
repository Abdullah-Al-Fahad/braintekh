from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
import jwt
import requests as http_requests

def verify_google_token(token):
    """
    Verifies a Google id_token and returns the decoded payload.
    Checks the audience against GOOGLE_SERVER_CLIENT_ID if configured.
    """
    client_id = getattr(settings, 'GOOGLE_SERVER_CLIENT_ID', None)
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)
        
        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        return idinfo
    except ValueError as e:
        # Invalid token
        return None


def fetch_apple_public_key(kid):
    """
    Fetches the Apple public key for the given key ID (kid) from Apple's JWKS.
    """
    keys_url = "https://appleid.apple.com/auth/keys"
    r = http_requests.get(keys_url)
    keys = r.json().get('keys', [])
    for key in keys:
        if key['kid'] == kid:
            return key
    return None

def verify_apple_token(token):
    """
    Verifies an Apple id_token and returns the decoded payload.
    """
    client_id = getattr(settings, 'APPLE_CLIENT_ID', 'com.braintekh.diafi')
    try:
        # Extract header to get the key ID
        headers = jwt.get_unverified_header(token)
        kid = headers.get('kid')
        
        if not kid:
            raise ValueError("No kid found in token header")
            
        public_key_jwk = fetch_apple_public_key(kid)
        if not public_key_jwk:
            raise ValueError("Apple public key not found")
            
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(public_key_jwk)
        
        # Decode and verify the token
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience=client_id,
            issuer='https://appleid.apple.com'
        )
        return decoded
        
    except Exception as e:
        # Invalid token
        print("Apple Auth Error:", e)
        return None

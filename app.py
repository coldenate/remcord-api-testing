"""
This module contains routes for retrieving documentation for the RemCord Exchange Server API.

Routes:
    /callback
    /refresh

Functions:
    token_updater(token, request: Request)
    make_session(token=None, state=None, scope=None)
    refresh(request: Request)
    callback(request: Request)
    encrypt_base64(string)
"""
import base64
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from requests_oauthlib import OAuth2Session
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

OAUTH2_CLIENT_ID = os.environ["OAUTH2_CLIENT_ID"]
OAUTH2_CLIENT_SECRET = os.environ["OAUTH2_CLIENT_SECRET"]
OAUTH2_REDIRECT_URI = "https://coldenate.github.io/dishandle"

API_BASE_URL = os.environ.get("API_BASE_URL", "https://discordapp.com/api")
AUTHORIZATION_BASE_URL = API_BASE_URL + "/oauth2/authorize"
TOKEN_URL = API_BASE_URL + "/oauth2/token"

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=OAUTH2_CLIENT_SECRET)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if "http://" in OAUTH2_REDIRECT_URI:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"


def token_updater(token, request: Request):
    """
    Updates the token in the session.

    Args:
        token (dict): The token dictionary to be updated.
        request (Request): The incoming request object.
    """
    request.session["oauth2_token"] = token


def make_session(token=None, state=None, scope=None):
    """
    Creates an OAuth2Session for the user.

    Args:
        token (dict, optional): The token dictionary to be used for the session. Defaults to None.
        state (str, optional): The state string to be used for the session. Defaults to None.
        scope (str, optional): The scope string to be used for the session. Defaults to None.

    Returns:
        OAuth2Session: The OAuth2Session object for the user.
    """

    return OAuth2Session(
        client_id=OAUTH2_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=OAUTH2_REDIRECT_URI,
        auto_refresh_kwargs={
            "client_id": OAUTH2_CLIENT_ID,
            "client_secret": OAUTH2_CLIENT_SECRET,
        },
        auto_refresh_url=TOKEN_URL,
        token_updater=token_updater,
    )

@app.post("/refresh")
async def refresh(request: Request):
    """
    Route that takes in a refresh token and returns a new access token response.

    Args:
        request (Request): The incoming request object.

    Returns:
        dict: A dictionary containing the new access token response.
    """
    if request.query_params.get("error"):
        print(request.query_params["error"])
        return request.query_params["error"]
    discord = make_session()
    token = discord.refresh_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        refresh_token=request.headers.get("refresh_token"),
    )
    request.session["oauth2_token"] = token
    return token


@app.get("/callback")
async def callback(request: Request):
    """
    Route that handles the callback from Discord.

    Args:
        request (Request): The incoming request object.

    Returns:
        str: The encrypted token in base64 format.
    """
    if request.query_params.get("error"):
        print(request.query_params["error"])
        return request.query_params["error"]
    discord = make_session()
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=str(request.url),
    )
    request.session["oauth2_token"] = token
    encrypted_token = encrypt_base64(json.dumps(token))
    return encrypted_token


def encrypt_base64(string):
    """
    Encrypts a string to base64.

    Args:
        string (str): The string to be encrypted.

    Returns:
        str: The encrypted string in base64 format.
    """
    encoded_bytes = base64.b64encode(string.encode("utf-8"))
    encoded_string = encoded_bytes.decode("utf-8")
    return encoded_string


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5032)

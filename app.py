"""
This module contains routes for retrieving documentation for the RemCord Exchange Server API.

Routes:
    /callback
    /refresh
    /activity
    /delete

Functions:
    token_updater(token, request: Request)
    make_session(token=None, state=None, scope=None)
    refresh(request: Request)
    callback(request: Request)
    encrypt_base64(string)
    decrypt_base64(string)
    activity(request: Request, goal_activity: Activity)
    delete_session(request: Request)
"""
import base64
import json
import os
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # pylint: disable=no-name-in-module
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

class Activity(BaseModel):
    """
    Represents an activity object.

    Attributes:
        type (int): The type of the activity.
        application_id (int): The ID of the application.
        name (str): The name of the activity.
        details (str): The details of the activity.
        state (str): The state of the activity.
        assets (dict, optional): The assets of the activity. Defaults to None.
        platform (str): The platform of the activity.
    """

    application_id: int
    name: str
    details: str
    state: str
    assets: Optional[dict] = None
    platform: str

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


@app.post("/activity")
async def activity(request: Request, goal_activity: Activity):
    """
    Route that takes in an activity object from the request's data, and sets it
    as the discord user's activity.
    The request will contain a header under the name "access_token".

    Args:
        request (Request): The incoming request object.
        activity (Activity): The activity object to be set as the user's activity.

    Returns:
        str: A string indicating whether the activity was successfully set or not.
    """

    token = request.headers.get("token")

    # parse the token into a python dict
    token = json.loads(token)


    discord = make_session(token = token)

    activities = [goal_activity]

    if token is not None:
        response = discord.post(
            API_BASE_URL + "/users/@me/headless-sessions",
            json={"activities": activities},
        )
    else:
        # Handle the error here, for example by returning an
        # error message or redirecting to an error page
        return "Error: oauth2_token is None"

    session_token = None

    if response.status_code not in (204, 200):
        # Handle the error here, for example by returning an
        # error message or redirecting to an error page
        print("Error: " + response.text)
    if response.status_code == 200:
        # extract the session token from the response
        session_token = response.json()["token"]
        # save the session token in a cookie

    return session_token

@app.post("/delete")
async def delete_session(request: Request):
    """
    Route that deletes a user's headless session.

    Args:
        request (Request): The incoming request object.

    Returns:
        str: A string indicating whether the session was successfully deleted or not.
    """
    try:
        session_token = request.headers.get("session_token")
        discord = make_session(token=json.loads(request.headers.get("token")))
        response = discord.post(
            API_BASE_URL + "/users/@me/headless-sessions/delete",
            json={"token": session_token},
        )
        response.raise_for_status()
        return "Session deleted"
    except requests.HTTPError as error_http:
        print(error_http.response.text)
        return error_http.response.text

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

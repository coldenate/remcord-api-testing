"""
This module contains routes for retrieving documentation for the RemCord Exchange Server API.

Routes:
    /callback
    /refresh
    /activity
    /delete
    /heartbeat

Functions:
    token_updater(token, request: Request)
    make_session(token=None, state=None, scope=None)
    refresh(request: Request)
    callback(request: Request)
    encrypt_base64(string)
    decrypt_base64(string)
    activity(request: Request, goal_activity: Activity)
    delete_session(request: Request)
    heartbeat(request: Request)
"""
import asyncio
import base64
import json
import os
import time
from typing import Optional

import requests
from cachetools import TTLCache
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # pylint: disable=no-name-in-module
from requests_oauthlib import OAuth2Session
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

OAUTH2_CLIENT_ID = os.environ["OAUTH2_CLIENT_ID"]
OAUTH2_CLIENT_SECRET = os.environ["OAUTH2_CLIENT_SECRET"]
OAUTH2_REDIRECT_URI = "https://coldenate.github.io/dishandle"

API_BASE_URL = os.environ.get("API_BASE_URL", "https://discordapp.com/api/v9")
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

    type: int
    application_id: int
    name: str
    details: str
    state: str
    assets: Optional[dict] = None
    platform: str


class UserToken(BaseModel):
    """
    Represents a user token object.

    Attributes:
        token (dict): The token dictionary.
    """

    access_token: str
    expires_in: int
    refresh_token: str
    scope: list[str]
    token_type: str
    expires_at: float


class Interaction(BaseModel):
    """
    Represents an interaction object between RemCord Plugin and this RemCord Exchange Server
    """

    token: UserToken
    activity: Optional[Activity] = None
    session_id: Optional[str] = None


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


@app.post("/refresh")
async def refresh(request: Request, interaction: Interaction):
    """
    Route that handles the refresh of the user token.

    Args:
        request (Request): The incoming request object.
        user_token (UserToken): The user token object.

    Returns:
        str: The refreshed token in JSON format.
    """
    if request.query_params.get("error"):
        print(request.query_params["error"])
        return request.query_params["error"]
    discord = make_session()
    token = discord.refresh_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        refresh_token=interaction.token.refresh_token,
    )
    request.session["oauth2_token"] = token
    return dict(token)


@app.post("/create")
async def activity(interaction: Interaction):
    """
    Route that handles the creation of a new activity for the user.

    Args:
        interaction (Interaction): The interaction object
        containing the user token and activity details.

    Returns:
        str: The session token in JSON format if the activity
        was created successfully, otherwise an error message.
    """
    discord = make_session(token=dict(interaction.token))

    if interaction.activity is None:
        return interaction.session_id

    activities = [
        {
            "type": 0,
            "application_id": interaction.activity.application_id,
            "name": interaction.activity.name,
            "details": interaction.activity.details,
            "state": interaction.activity.state,
            "assets": interaction.activity.assets,
            "platform": interaction.activity.platform,
        }
    ]

    if interaction.token is not None:
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
async def delete_session(interaction: Interaction):
    """
    Deletes a session with the given session ID.

    Args:
        interaction (Interaction): The interaction object containing the session ID and user token.

    Returns:
        Response: A response object with a status code of 200 if the session was successfully
        deleted, or a status code of 404 if the session ID is None.
    """
    try:
        if interaction.session_id is None:
            return Response(status_code=404)
        discord = make_session(token=dict(interaction.token))
        response = discord.post(
            API_BASE_URL + "/users/@me/headless-sessions/delete",
            json={"token": interaction.session_id},
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            return "bad bad bad no good"
        return Response(status_code=200)
    except requests.HTTPError as error_http:
        print(error_http.response.text)
        return error_http.response.text


@app.post("/edit")
async def edit_session(interaction: Interaction):
    """
    Edits a session with the given session ID and activity.

    Args:
        interaction (Interaction): The interaction object
        containing the session ID, user token, and activity.

    Returns:
        str: The session ID if the session was successfully edited.

    Raises:
        ValueError: If the session ID is None.

    """
    try:
        if interaction.session_id is None:
            raise ValueError("SessionId is not exist!")
        discord = make_session(token=dict(interaction.token))
        if interaction.activity is None:
            return interaction.session_id
        response = discord.post(
            API_BASE_URL + "/users/@me/headless-sessions",
            json={
                "activities": [dict(interaction.activity)],
                "token": interaction.session_id,
            },
        )
        response.raise_for_status()

        return interaction.session_id
    except requests.HTTPError as error_http:
        print(error_http.response.text)
        return Response(status_code=error_http.response.status_code)

cache = TTLCache(maxsize=1000, ttl=15)

@app.post("/heartbeat")
async def heartbeat(request: Request, interaction: Interaction):
    """
    Receives a heartbeat from the RemCord Plugin and updates the last heartbeat time in the cache.

    Args:
        request (Request): The request object.
        interaction (Interaction): The interaction object containing the user token and session ID.

    Returns:
        dict: A dictionary containing a message indicating whether this
        is the first heartbeat received,
        a message indicating that a heartbeat was received, or a message
        indicating that the session was deleted.

    """
    if request.client is None:
        return {"message": "No client found."}

    client_id = request.client.host

    # Get current time
    current_time = time.time()


    # If this is the first heartbeat, set the last heartbeat time to the current time
    if client_id not in cache:
        cache[client_id] = current_time
        return {"message": "First heartbeat received."}

    cache[client_id] = current_time

    await mourn_loss(interaction, client_id)
    return {"message": "Heartbeat received."}

async def mourn_loss(interaction: Interaction, client_id: str):
    """Deal with the loss of a heartbeat.
    Watch for the TTL Cache to lose the instructed client_id."""

    # Wait for the TTL Cache to lose the instructed client_id
    seconds_passed = 0
    while client_id in cache:
        if client_id not in cache:
            break
        if seconds_passed > 15:
            return
        await asyncio.sleep(1)
        seconds_passed += 1

    # Delete the session
    await delete_session(interaction)



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

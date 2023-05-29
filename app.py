import os
import time
from typing import Literal
from flask import Flask, g, session, redirect, request, url_for, jsonify
import pyperclip

from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import json

load_dotenv()

OAUTH2_CLIENT_ID = os.environ["OAUTH2_CLIENT_ID"]
OAUTH2_CLIENT_SECRET = os.environ["OAUTH2_CLIENT_SECRET"]
OAUTH2_REDIRECT_URI = "http://127.0.0.1:5000/callback"

API_BASE_URL = os.environ.get("API_BASE_URL", "https://discordapp.com/api")
AUTHORIZATION_BASE_URL = API_BASE_URL + "/oauth2/authorize"
TOKEN_URL = API_BASE_URL + "/oauth2/token"

app = Flask(__name__)
app.debug = True
app.config["SECRET_KEY"] = OAUTH2_CLIENT_SECRET

if "http://" in OAUTH2_REDIRECT_URI:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "true"


def token_updater(token):
    session["oauth2_token"] = token


def make_session(token=None, state=None, scope=None):
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


@app.route("/")
def index():
    scope = request.args.get(
        "scope",
        "identify email connections guilds guilds.join activities.write activities.read",
    )
    discord = make_session(scope=scope.split(" "))
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session["oauth2_state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    print("request.values")
    if request.values.get("error"):
        print(request.values["error"])
        return request.values["error"]
    discord = make_session(state=session.get("oauth2_state"))
    token = discord.fetch_token(
        TOKEN_URL,
        client_secret=OAUTH2_CLIENT_SECRET,
        authorization_response=request.url,
    )
    session["oauth2_token"] = token
    print("token: " + str(token))
    return redirect(url_for(".me"))


@app.route("/me")
def me():
    discord = make_session(token=session.get("oauth2_token"))
    user = discord.get(API_BASE_URL + "/users/@me").json()
    # guilds = discord.get(API_BASE_URL + "/users/@me/guilds").json()
    # connections = discord.get(API_BASE_URL + "/users/@me/connections").json()

    # set the user's activity to "Playing with OAuth"
    activities = [
        {
            "type": 0,
            "application_id": 1083778386708676728,
            "name": "RemNote",
            "details": "Ooiga booga dev testing",
            "state": "Typing Stuff and Stuff",
            "assets": {
                "large_image": "transparent_icon_logo",
            },
            "platform": "desktop",
        }
    ]
    token_dictionary = session.get("oauth2_token")
    if token_dictionary is not None:
        response = discord.post(
            API_BASE_URL + "/users/@me/headless-sessions",
            json={"activities": activities},
        )
    else:
        # Handle the error here, for example by returning an
        # error message or redirecting to an error page
        return "Error: oauth2_token is None"

    if response.status_code not in (204, 200):
        # Handle the error here, for example by returning an
        # error message or redirecting to an error page
        print("Error: " + response.text)
    if response.status_code == 200:
        # extract the session token from the response
        session_token = response.json()["token"]
        # save the session token in a cookie
        session["session_token"] = session_token
        print(response.text)
    session_token = session.get("session_token")
    if session_token is not None:
        print("http://127.0.0.1:5000/delete?session_token=" + session_token)

    return jsonify(user=user)


@app.route("/delete")
def delete_session() -> Literal["Session deleted", "Session not found"]:
    discord = make_session(token=session.get("oauth2_token"))
    session_token = request.args.get("session_token")
    response = discord.post(
        API_BASE_URL + "/users/@me/headless-sessions/delete",
        json={"token": session_token},
    )
    if response.status_code in (204, 200):
        print("Session deleted")
        return "Session deleted"
    return "Session not found"


if __name__ == "__main__":
    app.run()

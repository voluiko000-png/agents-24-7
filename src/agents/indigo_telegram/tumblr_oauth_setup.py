#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разовый скрипт: получить user access token для Tumblr (OAuth 1.0a,
3-legged, callback=oob — без локального сервера, PIN показывается прямо
на странице авторизации). Consumer key/secret уже есть в
Ключи_секреты/tumblr_api.txt.

Запуск:
    python tumblr_oauth_setup.py
Печатает authorize-URL, ждёт PIN с клавиатуры, печатает access_token/secret.
"""
import base64
import hashlib
import hmac
import time
import urllib.parse
import uuid

import requests

CONSUMER_KEY = "osxr9FOFZGWYwlfoFe8iEMfGw63wCe3xeTrMS7YQlSrwkLRstx"
CONSUMER_SECRET = "5ZGMVNxDeUeJUebOBDnNot2UP486Et6AyBXZNEwn8k4Nq165yt"

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.tumblr.com/oauth/access_token"


def _sign(method: str, url: str, params: dict, token_secret: str = "") -> str:
    base = "&".join(
        urllib.parse.quote(x, safe="")
        for x in (
            method,
            url,
            "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}" for k, v in sorted(params.items())),
        )
    )
    key = f"{urllib.parse.quote(CONSUMER_SECRET, safe='')}&{urllib.parse.quote(token_secret, safe='')}"
    return base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()


def _oauth_params(extra: dict, token_secret: str = "", method: str = "POST") -> dict:
    params = {
        "oauth_consumer_key": CONSUMER_KEY,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
        **extra,
    }
    url = extra.pop("_url")
    params.pop("_url", None)
    params["oauth_signature"] = _sign(method, url, params, token_secret)
    return params


def auth_header(method: str, url: str, oauth_token: str, token_secret: str) -> str:
    """Authorization header for API calls signed with oauth params only (no body
    params) — correct for multipart/binary bodies like Tumblr's photo post endpoint."""
    signed = _oauth_params({"_url": url, "oauth_token": oauth_token}, token_secret, method)
    return "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(str(v), safe="")}"' for k, v in signed.items())


def get_request_token():
    # ponytail: no oauth_callback param — Tumblr rejects "oob" explicitly ("Disallowed
    # oauth_callback specified"), omitting it falls back to the app's registered default
    # callback, and we just read oauth_verifier off the redirected browser URL afterwards.
    params = {"_url": REQUEST_TOKEN_URL}
    signed = _oauth_params(params)
    r = requests.post(REQUEST_TOKEN_URL, data=signed, timeout=20)
    r.raise_for_status()
    parsed = dict(urllib.parse.parse_qsl(r.text))
    return parsed["oauth_token"], parsed["oauth_token_secret"]


def get_access_token(oauth_token: str, oauth_token_secret: str, verifier: str):
    params = {"_url": ACCESS_TOKEN_URL, "oauth_token": oauth_token, "oauth_verifier": verifier}
    signed = _oauth_params(params, token_secret=oauth_token_secret)
    r = requests.post(ACCESS_TOKEN_URL, data=signed, timeout=20)
    r.raise_for_status()
    parsed = dict(urllib.parse.parse_qsl(r.text))
    return parsed["oauth_token"], parsed["oauth_token_secret"]


if __name__ == "__main__":
    rt, rts = get_request_token()
    print(f"Открой и авторизуй: {AUTHORIZE_URL}?oauth_token={rt}")
    pin = input("PIN со страницы: ").strip()
    at, ats = get_access_token(rt, rts, pin)
    print(f"ACCESS_TOKEN={at}")
    print(f"ACCESS_TOKEN_SECRET={ats}")

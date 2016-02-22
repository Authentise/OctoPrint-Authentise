# coding=utf-8
from __future__ import absolute_import

import json
import os
import subprocess
from uuid import uuid4

import requests


def run_client_and_wait(settings, logger, args=None):
    try:
        process = run_client(settings, args, pipe=subprocess.PIPE)
        output, _ = process.communicate()
        return output.strip()
    except subprocess.CalledProcessError as exception:
        logger.error("Error running client command `%s` using parameters: %s", exception, args)
        return

DEVNULL = open(os.devnull, 'w')
def run_client(settings, args=None, pipe=None):
    command = []
    if isinstance(settings.get(["streamus_client_path"]), list):
        command.extend(settings.get(["streamus_client_path"]))
    else:
        command.append(settings.get(["streamus_client_path"]))

    command.extend([
                   '--logging-level', 'debug',
                   ])

    if settings.get(["streamus_config_path"]):
        command.extend(['-c', settings.get(["streamus_config_path"])])

    if args:
        command.extend(args)

    if pipe==None:
        pipe=DEVNULL
    return subprocess.Popen(command, stdout=pipe, stderr=pipe)

class ClaimNodeException(Exception):
    pass

def claim_node(node_uuid, settings, logger):
    _session = session(settings)

    if not node_uuid:
        raise ClaimNodeException("No Authentise node uuid available to claim")

    url = "{}/client/{}/".format(settings.get(["authentise_url"]), node_uuid)
    response = _session.get(url)
    if response.ok:
        return

    claim_code = run_client_and_wait(settings, args=['--connection-code'], logger=logger)
    if claim_code:
        logger.info("Got claim code: %s", claim_code)
    else:
        raise ClaimNodeException("Could not get a claim code from Authentise")

    url = "{}/client/claim/{}/".format(settings.get(["authentise_url"]), claim_code)
    response = _session.put(url)
    logger.info("Response from - POST %s - %s - %s", url, response.status_code, response.text)

    if response.ok:
        logger.info("Claimed node: %s", node_uuid)
        return

    raise ClaimNodeException("Could not use claim code {} for node {}".format(claim_code, node_uuid))

def login(settings, username, password, logger):
    url = '{}/sessions/'.format(settings.get(["authentise_user_url"]))
    payload = {"username": username, "password": password,}
    response = requests.post(url, json=payload)
    logger.info("Response from - POST %s - %s - %s", url, response.status_code, response.text)

    if response.ok:
        logger.info("Successfully logged in to user service: %s", username)
        return response.status_code, json.loads(response.text), response.cookies
    elif response.status_code == 400:
        logger.warning("Failed to log in to user service for user %s", username)
    else:
        logger.error("Error logging in to user service for user %s", username)

    return response.status_code, json.loads(response.text), None

def create_api_token(settings, cookies, logger):
    if not cookies:
        logger.warning("Cannot create api token without a valid session cookie")
        return None, None

    url = '{}/api_tokens/'.format(settings.get(["authentise_user_url"]))
    payload = {"name": "Octoprint Token - {}".format(str(uuid4()))}
    response = requests.post(url, json=payload, cookies=cookies)
    logger.info("Response from - POST %s - %s - %s", url, response.status_code, response.text)

    if response.ok:
        logger.info("Successfully created api token: %s", response.text)
    elif response.status_code == 400:
        logger.warning("Failed to create api token for user")
    else:
        logger.error("Error creating api token for user")

    return response.status_code, json.loads(response.text)

class SessionException(Exception):
    pass

def session(settings):
    api_key = settings.get(['api_key'])
    api_secret = settings.get(['api_secret'])

    if not api_key:
        raise SessionException("No Authentise API Key available to claim node")

    if not api_secret:
        raise SessionException("No Authentise API secret available to claim node")

    _session = requests.Session()
    _session.auth = requests.auth.HTTPBasicAuth(api_key, api_secret)
    return _session

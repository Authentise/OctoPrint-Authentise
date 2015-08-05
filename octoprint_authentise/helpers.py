# coding=utf-8
from __future__ import absolute_import

import json
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

def run_client(settings, args=None, pipe=None):
    command = [settings.get(["streamus_client_path"]),
               '--logging-level', 'debug',
               ]

    if settings.get(["streamus_config_path"]):
        command.extend(['-c', settings.get(["streamus_config_path"])])

    if args:
        command.extend(args)

    return subprocess.Popen(command, stdout=pipe, stderr=pipe)

def claim_node(settings, node_uuid, api_key, api_secret, logger):
    if not node_uuid:
        logger.error("No node uuid available to claim")
        return False

    if not api_key:
        logger.error("No API Key available to claim node")
        return False

    if not api_secret:
        logger.error("No API secret available to claim node")
        return False

    claim_code = run_client_and_wait(settings, args=['--connection-code'], logger=logger)
    if claim_code:
        logger.info("Got claim code: %s", claim_code)
    else:
        logger.error("Could not get a claim code from Authentise")
        return False

    url = "{}/client/claim/{}/".format(settings.get(["authentise_url"]), claim_code)
    response = requests.put(url, auth=(api_key, api_secret))
    logger.info("Response from - POST %s - %s - %s", url, response.status_code, response.text)

    if response.ok:
        logger.info("Claimed node: %s", node_uuid)
        return True

    logger.error("Could not use claim code %s for node %s", claim_code, node_uuid)
    return False

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

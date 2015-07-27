# coding=utf-8
from __future__ import absolute_import

from uuid import uuid4
import sys
import os
import subprocess
import requests
import json

# AUTHENTISE_CLIENT_PATH = 'authentise-streaming-client'
AUTHENTISE_CLIENT_PATH = '/Applications/Authentise.app/Contents/Resources/streamus-client'
AUTHENTISE_PRINT_API = 'https://print.dev-auth.com'
AUTHENTISE_USER_API = 'https://users.dev-auth.com'

class HelpersPlugin():
    def run_client(self, *args):
        command = (
            AUTHENTISE_CLIENT_PATH,
            '--logging-level',
            'error',
            '-c',
            '/Applications/Authentise.app/Contents/Resources/client.conf',
        ) + args

        try:
            return subprocess.check_output(command).strip()
        except Exception as e:
            self._logger.error("Error running client command `%s` using parameters: %s", e, args)
            return

    def claim_node(self, api_key, api_secret):
        if not self.node_uuid:
            self._logger.error("No node uuid available to claim")
            return False

        if not api_key:
            self._logger.error("No API Key available to claim node")
            return False

        if not api_secret:
            self._logger.error("No API secret available to claim node")
            return False

        claim_code = self.run_client('--connection-code')
        if claim_code:
            self._logger.info("Got claim code: %s", claim_code)
        else:
            self._logger.error("Could not get a claim code from Authentise")
            return False

        url = "{}/client/claim/{}/".format(AUTHENTISE_PRINT_API, claim_code)
        response = requests.put(url, auth=(api_key, api_secret))
        self._logger.info("Response from - POST - %s - %s", url, response.status_code, response.text)

        if response.ok:
            self._logger.info("Claimed node: %s", self.node_uuid)
            return True

        self._logger.error("Could not use claim code %s for node %s", claim_code, self.node_uuid)
        return False

    def login(self,username, password):
        url = '{}/sessions/'.format(AUTHENTISE_USER_API)
        payload = {
            "username": username,
            "password": password,
        }
        response = requests.post(url, json=payload)
        self._logger.info("Response from - POST %s - %s - %s", url, response.status_code, response.text)

        if response.ok:
            self._logger.info("Successfully logged in to user service: %s", username)
            return response.status_code, json.loads(response.text), response.cookies
        elif response.status_code == 400:
            self._logger.warning("Failed to log in to user service for user %s", username)
        else:
            self._logger.error("Error logging in to user service for user %s", username)

        return response.status_code, json.loads(response.text), None

    def create_api_token(self, cookies):
        if not cookies:
            self._logger.warning("Cannot create api token without a valid session cookie")
            return None, None

        url = '{}/api_tokens/'.format(AUTHENTISE_USER_API)
        payload = { "name": "Octoprint Token - {}".format(str(uuid4())) }
        response = requests.post(url, json=payload, cookies=cookies)
        self._logger.info("Response from - POST %s - %s - %s", url, response.status_code, response.text)

        if response.ok:
            self._logger.info("Successfully created api token: %s", response.text)
        elif response.status_code == 400:
            self._logger.warning("Failed to create api token for user %s", username)
        else:
            self._logger.error("Error creating api token for user")

        return response.status_code, json.loads(response.text)

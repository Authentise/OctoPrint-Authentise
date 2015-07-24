# coding=utf-8
from __future__ import absolute_import

import sys
import os
import subprocess
import requests

# AUTHENTISE_CLIENT_PATH = 'authentise-streaming-client'
AUTHENTISE_CLIENT_PATH = '/Applications/Authentise.app/Contents/Resources/streamus-client'
AUTHENTISE_PRINT_API = 'https://print.dev-auth.com'

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

        if response.ok:
            self._logger.info("Claimed node: %s", self.node_uuid)
            return True

        self._logger.error(
            "Could not use claim code %s for node %s.  Response is %s, %s",
            claim_code,
            self.node_uuid,
            response.status_code,
            response.text,
        )
        return False

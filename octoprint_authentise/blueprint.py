# coding=utf-8
from __future__ import absolute_import

import flask
import json
import octoprint.plugin
from octoprint_authentise import helpers

class BlueprintPlugin(octoprint.plugin.BlueprintPlugin):
    @octoprint.plugin.BlueprintPlugin.route("/connect/", methods=["POST"])
    def connect(self):
        username = flask.request.json.get('username')
        password = flask.request.json.get('password')

        status_code, response_json, cookies = helpers.login(username, password, self._logger)
        if not cookies:
            return json.dumps(response_json), status_code

        status_code, response_json = helpers.create_api_token(cookies, self._logger)
        if status_code == 201:
            api_key = response_json.get('uuid')
            api_secret = response_json.get('secret')

            if helpers.claim_node(self.node_uuid, api_key, api_secret, self._logger):
                self.on_settings_save({
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "claimed_by": response_json.get('user_uuid'),
                })

        return json.dumps(response_json), status_code

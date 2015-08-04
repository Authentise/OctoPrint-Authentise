# coding=utf-8
#pylint: disable=no-member
from __future__ import absolute_import

import json

import flask

import octoprint.plugin
from octoprint_authentise import helpers


class BlueprintPlugin(octoprint.plugin.BlueprintPlugin):
    @octoprint.plugin.BlueprintPlugin.route("/connect/", methods=["POST"])
    def blueprint_connect(self):
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

    @octoprint.plugin.BlueprintPlugin.route("/node/", methods=["GET"])
    def get_node(self):
        connection_code = helpers.run_client_and_wait(args='--connection-code', logger=self._logger)
        if connection_code:
            self._logger.info("Found node connection code: %s", connection_code)
            results = {
                "connectionCode": connection_code,
                "uuid": self.node_uuid,
                "version": self.node_version,
                "plugin_version": self._plugin_version,
            }
            return json.dumps(results), 200
        else:
            self._logger.warning("Could not find node connection code")
            return json.dumps({"message": "Could not find node connection code"}), 500

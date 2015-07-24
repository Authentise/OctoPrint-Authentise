# coding=utf-8
from __future__ import absolute_import

import flask
import json
import octoprint.plugin

class BlueprintPlugin(octoprint.plugin.BlueprintPlugin):
    @octoprint.plugin.BlueprintPlugin.route("/connect/", methods=["POST"])
    def connect(self):
        username = flask.request.json.get('username')
        password = flask.request.json.get('password')

        status_code, response_json, cookies = self.login(username, password)
        if not cookies:
            return json.dumps(response_json), status_code

        status_code, response_json = self.create_api_token(cookies)
        return json.dumps(response_json), status_code

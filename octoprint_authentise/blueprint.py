# coding=utf-8
from __future__ import absolute_import

import flask
import json
import octoprint.plugin

class BlueprintPlugin(octoprint.plugin.BlueprintPlugin):
    @octoprint.plugin.BlueprintPlugin.route("/connect/", methods=["POST"])
    def connect(self):
        pass

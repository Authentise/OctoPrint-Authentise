# coding=utf-8
#pylint: disable=no-member
from __future__ import absolute_import

import json

import octoprint.plugin

from octoprint_authentise import helpers


class BlueprintPlugin(octoprint.plugin.BlueprintPlugin):
    @octoprint.plugin.BlueprintPlugin.route("/node/", methods=["GET"])
    def get_node(self):
        connection_code = helpers.run_client_and_wait(self._settings, args=['--connection-code'], logger=self._logger)
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

# coding=utf-8
#pylint: disable=no-member, too-few-public-methods
from __future__ import absolute_import


class UpdatePlugin(object):
    def get_update_information(self):
        return dict(
            authentise=dict(
                displayName="Authentise Plugin",
                displayVersion=self._plugin_version,
                type="github_release",
                user="OctoPrint",
                repo="OctoPrint-Authentise",
                current=self._plugin_version,
                pip="https://github.com/Authentise/OctoPrint-Authentise/archive/{target_version}.zip"
            )
        )

$(function() {
  function AuthentiseModelsViewModel(parameters) {
    this.apiRoot = "/plugin/authentise";
    this.$frame = $("#authentise-models");
    this.frame = this.$frame[0];

    this.settings = parameters[0];
    this.listening = false;
    this.nodeUuid = this.$frame.data("node_uuid");
    this.nodeVersion = this.$frame.data("node_version");
    this.pluginVersion = this.$frame.data("plugin_version");

    var eventMethod = window.addEventListener ? "addEventListener" : "attachEvent";
    var messageEvent = eventMethod == "attachEvent" ? "onmessage" : "message";

    window[eventMethod](messageEvent, $.proxy(function(e) {
      var data = e[e.message ? "message" : "data"];
      if (data && data.type && $.isFunction(this.handlers[data.type])) {
        this.handlers[data.type].call(this, data);
      }
    }, this), false);

    this.postMessage = $.proxy(function(payload) {
      this.frame.contentWindow.postMessage(payload, "*");
    }, this);

    this.handlers = {
      GET_NODE: function(data) {
        var handleSuccess = $.proxy(function(results){
          results.type = "GOT_NODE";
          this.postMessage(results);
        }, this);

        var handleError = $.proxy(function(jqXHR, textStatus, errorThrown){
          console.error("Error getting node from Authentise plugin", jqXHR, textStatus, errorThrown);
        }, this);

        $.ajax({
          type: "get",
          dataType: "json",
          contentType: "application/json; charset=utf-8",
          url: this.apiRoot + "/node/",
          success: handleSuccess,
          error: handleError,
        });
      },
    };
  }

  OCTOPRINT_VIEWMODELS.push([
    AuthentiseModelsViewModel,
    ["connectionViewModel"],
    ['#tab_plugin_authentise']
  ]);
});

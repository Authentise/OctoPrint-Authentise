$(function() {
  function AuthentiseConnectViewModel(parameters) {
    this.settings = parameters[0];

    this.apiRoot = "/plugin/authentise";

    this.onSubmit = $.proxy(function() {
      this.toggleLoading();
      this.setMessage();

      var form = $("#authentise-connect"),
          data = {
            username: form.find("[name=authentise_user]").val(),
            password: form.find("[name=authentise_pass]").val()
          };

      var handleSuccess = $.proxy(function(results){
        this.clearForm();
        this.hideModal();
        this.setKey(results);
      }, this);

      var handleError = $.proxy(function(jqXHR, textStatus, errorThrown){
        var results = jqXHR.responseJSON;
        this.setMessage(results.errors[0].title);
        console.error("Error connecting to Authentise", results, jqXHR, textStatus, errorThrown);
      }, this);

      $.ajax({
        type: "post",
        dataType: "json",
        contentType: "application/json; charset=utf-8",
        url: this.apiRoot + "/connect/",
        data: JSON.stringify(data),
        success: handleSuccess,
        error: handleError,
        complete: this.toggleLoading
      });

      return false;
    }, this);

    this.setKey = $.proxy(function(result) {
      var keyInput = $("#authentise-settings input[name=key]");
      var secretInput = $("#authentise-settings input[name=secret]");
      keyInput.val(result.uuid).change();
      secretInput.val(result.secret).change();
    }, this);

    this.setMessage = $.proxy(function(message) {
      var messageBox = $("#authentise-connect .modal-body .alert-error");
      messageBox.children('span').text(message);

      if(message) {
        messageBox.fadeIn();
        return
      }
      messageBox.fadeOut();
    }, this);

    this.hideModal = $.proxy(function() {
      $("#authentise-connect").modal('hide');
    }, this);

    this.clearForm = $.proxy(function() {
      $("#authentise-connect .modal-body input").val(null);
    }, this);

    this.toggleLoading = $.proxy(function() {
      var form = $("#authentise-connect"),
          inputs = form.find(".modal-body input, .modal-footer .btn-primary"),
          spinner = form.find(".modal-footer .btn-primary > i");
      if(!form.prop("loading")) {
        inputs.addClass("disabled").prop("disabled", true);
        spinner.addClass("icon-spinner icon-spin");
        form.prop("loading", true);
        return;
      }

      inputs.removeClass("disabled").prop("disabled", false);
      spinner.removeClass("icon-spinner icon-spin");
      form.prop("loading", false);
    }, this);
  }

  OCTOPRINT_VIEWMODELS.push([
    AuthentiseConnectViewModel,
    ["settingsViewModel"],
    ['#authentise-connect'],
  ]);
});

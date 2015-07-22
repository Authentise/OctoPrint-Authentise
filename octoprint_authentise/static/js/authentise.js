$(function() {
  function AuthentiseViewModel(parameters) {
    this.settings = parameters[0];
  }

  OCTOPRINT_VIEWMODELS.push([
    AuthentiseViewModel,
    ["controlViewModel"],
    ['']
  ]);
});

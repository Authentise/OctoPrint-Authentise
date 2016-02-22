def patch_connect(mocker):
    mocker.patch('octoprint_authentise.comm.threading.Thread')
    mocker.patch('octoprint_authentise.comm.RepeatedTimer')
    mocker.patch("octoprint_authentise.comm.helpers.run_client")
    mocker.patch("octoprint_authentise.comm.helpers.claim_node")

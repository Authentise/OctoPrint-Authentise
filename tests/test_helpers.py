import pytest

from octoprint_authentise import helpers


def test_claim_node_no_node_uuid(settings, mocker):
    logger = mocker.Mock()
    with pytest.raises(helpers.ClaimNodeException) as error:
        helpers.claim_node(None, settings, logger)
    assert error.value.message == "No Authentise node uuid available to claim"

def test_claim_node_already_claimed(settings, httpretty, mocker, client_uri, node_uuid):
    logger = mocker.Mock()
    httpretty.register_uri(httpretty.GET, client_uri, status=200)

    helpers.claim_node(node_uuid, settings, logger)

def test_claim_node_unclaimed_no_claim_code(settings, httpretty, mocker, client_uri, node_uuid):
    logger = mocker.Mock()
    httpretty.register_uri(httpretty.GET, client_uri, status=403)

    mocker.patch('octoprint_authentise.helpers.run_client_and_wait', return_value=None)

    with pytest.raises(helpers.ClaimNodeException) as error:
        helpers.claim_node(node_uuid, settings, logger)
    assert error.value.message == "Could not get a claim code from Authentise"

def test_claim_node_unclaimed_bad_claim_code(settings, httpretty, mocker, client_uri, node_uuid, claim_code, claim_code_uri):
    logger = mocker.Mock()
    httpretty.register_uri(httpretty.GET, client_uri, status=403)

    mocker.patch('octoprint_authentise.helpers.run_client_and_wait', return_value=claim_code)

    httpretty.register_uri(httpretty.PUT, claim_code_uri, status=404)

    with pytest.raises(helpers.ClaimNodeException) as error:
        helpers.claim_node(node_uuid, settings, logger)

    assert error.value.message == "Could not use claim code {} for node {}".format(claim_code, node_uuid)

def test_claim_node_unclaimed_good_claim_code(settings, httpretty, mocker, client_uri, node_uuid, claim_code, claim_code_uri):
    logger = mocker.Mock()
    httpretty.register_uri(httpretty.GET, client_uri, status=403)

    mocker.patch('octoprint_authentise.helpers.run_client_and_wait', return_value=claim_code)

    httpretty.register_uri(httpretty.PUT, claim_code_uri, status=200)

    helpers.claim_node(node_uuid, settings, logger)

def test_session_no_api_key(settings):
    settings.set(['api_key'], '')

    with pytest.raises(helpers.SessionException) as error:
        helpers.session(settings)

    assert error.value.message == "No Authentise API Key available to claim node"

def test_session_no_api_secret(settings):
    settings.set(['api_key'], 'some_api_key')
    settings.set(['api_secret'], '')

    with pytest.raises(helpers.SessionException) as error:
        helpers.session(settings)

    assert error.value.message == "No Authentise API secret available to claim node"

def test_session_success(settings):
    settings.set(['api_key'], 'some_api_key')
    settings.set(['api_secret'], 'some_secret')

    session = helpers.session(settings)

    assert session.auth.username == 'some_api_key'
    assert session.auth.password == 'some_secret'

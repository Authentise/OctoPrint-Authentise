import json
from urlparse import urljoin

import httpretty


# tests case in which the user has no authentise printers
def test_printer_connect_create_authentise_printer(comm, httpretty, mocker, settings):
    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")
    httpretty.register_uri(httpretty.GET,
                           url,
                           body='[]',
                           content_type='application/json')

    httpretty.register_uri(httpretty.POST, url,
                           adding_headers={"Location": urljoin(url, "/abc-123/")})

    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.start_authentise", return_value=1234)

    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.run_client", return_value="you're-a-wizard-harry")

    comm.connect(port="1234", baudrate=5678)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()


# tests case in which the user has a printer on the right port, but the baud rate is wrong
def test_printer_connect_get_authentise_printer(comm, httpretty, mocker, settings):
    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")
    printer_uri = urljoin(url, "/abc-123/")
    printers_payload = [{"baud": 250000,
                         "port": "/dev/tty.derp",
                         "uri": printer_uri}]

    httpretty.register_uri(httpretty.GET,
                           url,
                           body='[]',
                           content_type='application/json')

    httpretty.register_uri(httpretty.POST, url,
                           adding_headers={"Location": urljoin(url, "/abc-123/")})

    httpretty.register_uri(httpretty.PUT, printer_uri)


    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.start_authentise", return_value=1234)

    comm.connect(port="/dev/tty.derp", baudrate=5678)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()


# tests case in which port and baud rate are just right
def test_printer_connect_get_authentise_printer_no_put(comm, httpretty, mocker, settings):
    url = urljoin(settings.get(["authentise_url"]), "/printer/instance/")
    printer_uri = urljoin(url, "/abc-123/")
    printers_payload = [{"baud": 250000,
                         "port": "/dev/tty.derp",
                         "uri": printer_uri}]

    httpretty.register_uri(httpretty.GET,
                           url,
                           body=json.dumps(printers_payload),
                           content_type='application/json')

    # keep authentise from actually starting
    mocker.patch("octoprint_authentise.helpers.start_authentise", return_value=1234)

    comm.connect(port="/dev/tty.derp", baudrate=250000)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()

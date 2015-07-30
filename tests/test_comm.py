import httpretty

def test_comm_startup(comm, httpretty):
    httpretty.register_uri(httpretty.GET, 'https://print.authentise.com/printer/instance/',
                           body='',
                           content_type='application/json')

    comm.connect(port=1234, baudrate=5678)

    assert comm.isOperational()
    assert not comm.isBusy()
    assert not comm.isPrinting()
    assert not comm.isPaused()
    assert not comm.isError()
    assert not comm.isClosedOrError()

def test_second_test_does_not_fail(comm):
    assert comm

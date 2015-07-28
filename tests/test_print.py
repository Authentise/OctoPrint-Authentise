import httpretty

def test_printer_connect(printer, httpretty):
    httpretty.register_uri(httpretty.GET, 'https://print.authentise.com/printer/instance/',
                           body='',
                           content_type='application/json')

    printer.connect(port=1234, baudrate=5678)

    assert printer.is_operational()
    assert printer.is_ready()
    assert not printer.is_printing()
    assert not printer.is_paused()
    assert not printer.is_error()
    assert not printer.is_closed_or_error()

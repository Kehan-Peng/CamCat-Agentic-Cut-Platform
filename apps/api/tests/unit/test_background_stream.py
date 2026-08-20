from threading import Event

from camcat.agent.streaming import background_stream


def test_closing_browser_stream_does_not_stop_producer():
    released, completed = Event(), Event()

    def producer():
        yield "started"
        assert released.wait(2)
        completed.set()
        yield "completed"

    stream = background_stream(producer)
    assert next(stream) == "started"
    stream.close()
    released.set()
    assert completed.wait(2)

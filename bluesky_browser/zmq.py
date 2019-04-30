from bluesky.callbacks.zmq import RemoteDispatcher
from qtpy.QtCore import QThread
from qtpy.QtCore import Signal


class ConsumerThread(QThread):
    documents = Signal([tuple])

    def __init__(self, *args, zmq_address, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatcher = RemoteDispatcher(zmq_address)

        def callback(name, doc):
            self.documents.emit((name, doc))

        self.dispatcher.subscribe(callback)

    def run(self):
        self.dispatcher.start()

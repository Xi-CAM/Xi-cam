import logging

from bluesky.callbacks.zmq import RemoteDispatcher
from qtpy.QtCore import QThread
from qtpy.QtCore import Signal


log = logging.getLogger('bluesky_browser')


class ConsumerThread(QThread):
    documents = Signal([tuple])
    new_run_uid = Signal([str])

    def __init__(self, *args, zmq_address, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatcher = RemoteDispatcher(zmq_address)

        def callback(name, doc):
            if name == 'start':
                self.new_run_uid.emit(doc['uid'])
                log.debug("New streaming Run: uid=%r", doc['uid'])
            self.documents.emit((name, doc))

        self.dispatcher.subscribe(callback)

    def run(self):
        self.dispatcher.start()

class Workflow(object):
    def __init__(self):
        self.operations = []

    def addOperation(self, operation):
        self.operations.append(operation)

    def toGraph(self):

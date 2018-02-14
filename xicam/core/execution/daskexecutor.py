class DaskExecutor:
    def __init__(self):
        pass

    def execute(self, wf):
        import distributed
        # from distributed import Queue

        dsk = wf.convertGraph()

        client = distributed.Client()

        # generate queues
        """
        for node in wf._processes:
            i = node
            for key in i.inputs.keys():
              j = i.inputs[key]
              for k in j.subscriptions:
                # share distributed Queue between sender and receiver
                q = Queue()
                j.__internal_data__.queues_in.append({j.name : q})
                k[1].parent.__internal_data__.queues_out.append({k[0].name : q})
        """

        print("Running: ", dsk[0], dsk[1])
        result = client.get(dsk[0], dsk[1])
        client.close()

        #res = {}
        #for f in result:
        #    for fx in f:
        #        for f1 in fx:
        #            res[f1.name] = f1.value

        return result

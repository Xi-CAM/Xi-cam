def test_IProcessingPlugin():
    from ..ProcessingPlugin import ProcessingPlugin, Input, Output

    class SumProcessingPlugin(ProcessingPlugin):
        a = Input(default=1, unit='nm', min=0)
        b = Input(default=2)
        c = Output()

        def evaluate(self):
            self.c.value = self.a.value + self.b.value
            return self.c.value

    t1 = SumProcessingPlugin()
    t2 = SumProcessingPlugin()
    assert t1.evaluate() == 3
    t1.a.value = 100
    assert t2.a.value == 1
    assert t1.inputs['a'].name == 'a'
    assert t1.outputs['c'].name == 'c'
    assert t1.outputs['c'].value == 3

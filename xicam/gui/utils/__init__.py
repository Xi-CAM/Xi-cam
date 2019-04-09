from pyqtgraph.parametertree import Parameter, parameterTypes, ParameterTree
from qtpy.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
from qtpy.QtCore import Qt


def parameterize(func):
    """
    Usage:

    from pyqtgraph.parametertree.parameterTypes import SimpleParameter

    @parameterize
    def sum(a, b):
        return sum(a, b)

    a = SimpleParameter(name='a', type='float', value=1)
    b = SimpleParameter(name='b', type='float', value=2)

    sum(a, b)  # spawns a dialog; user-interaction required
    """

    def func_wrapper(*args, **kwargs):
        param = args_to_params(*args, **kwargs)

        # query values
        paramdialog = ParameterDialog(param)
        paramdialog.exec_()

        # extract values
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, Parameter):
                args[i] = arg.value()
            else:
                args[i] = arg

        for key, value in kwargs.items():
            if isinstance(value, Parameter):
                kwargs[key] = value.value()
            else:
                kwargs[key] = value

        # make the call
        return func(*args, **kwargs)

    return func_wrapper


def args_to_params(*args, **kwargs):
    param = parameterTypes.GroupParameter(name='Parameters')
    for arg in args + tuple(kwargs.values()):
        if isinstance(arg, Parameter):
            param.addChild(arg)
        elif isinstance(arg, (list, tuple)):
            param.addChild(args_to_params(*arg))
    return param


class ParameterDialog(QDialog):
    def __init__(self, children, parent=None):
        super(ParameterDialog, self).__init__(parent)

        layout = QVBoxLayout(self)

        self.paramtree = ParameterTree()
        layout.addWidget(self.paramtree)

        self.paramtree.setParameters(children, showTop=False)

        # OK and Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def exec_(self, *args, **kwargs):
        result = super(ParameterDialog, self).exec_()
        if result != self.Accepted:
            raise InterruptedError('Execution aborted by user.')

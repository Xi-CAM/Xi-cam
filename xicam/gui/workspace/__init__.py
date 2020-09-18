# TODO encapsulate the Ensemble and Catalog Items (if we need to store more info than just checkstate)
# class EnsembleItem(QStandardItem):
#     def __init__(self, *args, **kwargs):
#         super(EnsembleItem, self).__init__(*args, **kwargs)
#
#         self.setCheckable(True)
#
#


# TODO: subclass from QAbstractItemModel, book-keep the list of ensembles
# contains Ensembles, no QStandardItems
# data(index, role):
#   if index.parent().parent.isValid():
#       index_type = 'Intent'
#   elif index.parent().isValid():
#       index_type = 'Run'
#   else:
#       index_type = 'Ensemble'

#   if index.parent().isValid():
#       if role == index.data(DisplayRole)
#


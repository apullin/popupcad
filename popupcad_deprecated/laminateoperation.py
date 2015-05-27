# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
from popupcad.filetypes.laminate  import Laminate
from popupcad.filetypes.operation import Operation
import PySide.QtGui as qg
from popupcad.filetypes.listwidgetitem import ListWidgetItem
from popupcad.widgets.dragndroptree import DraggableTreeWidget,ParentItem,ChildItem

class Dialog(qg.QDialog):
    def __init__(self,operationlist,index0,operationindeces1=None,operationindeces2 = None):
        super(Dialog,self).__init__()
        
        if operationindeces1 ==None:
            operationindeces1 = []
        if operationindeces2 ==None:
            operationindeces2 = []
        
        from popupcad.widgets.operationlist import OperationList
        self.le0 = OperationList(LaminateOperation.unaryoperationtypes,LaminateOperation.pairoperationtypes,LaminateOperation.displayorder)
        self.operationlist = operationlist

        self.unarylistwidget = DraggableTreeWidget()
        self.unarylistwidget.linklist(self.operationlist)
        self.unarylistwidget.setSelectionMode(qg.QListWidget.SelectionMode.ExtendedSelection)
        self.unarylistwidget.selectIndeces(operationindeces1)

        self.pairlistwidget = DraggableTreeWidget()
        self.pairlistwidget.linklist(self.operationlist)
        self.pairlistwidget.setSelectionMode(qg.QListWidget.SelectionMode.ExtendedSelection)
        self.pairlistwidget.selectIndeces(operationindeces2)

        layout3 = qg.QVBoxLayout()
        layout3.addWidget(qg.QLabel('Unary Operators'))
        layout3.addWidget(self.unarylistwidget)

        layout4 = qg.QVBoxLayout()
        layout4.addWidget(qg.QLabel('Binary Operators'))
        layout4.addWidget(self.pairlistwidget)

        layout5 = qg.QHBoxLayout()
        layout5.addLayout(layout3)
        layout5.addLayout(layout4)

        button1 = qg.QPushButton('Ok')
        button2 = qg.QPushButton('Cancel')
        layout2 = qg.QHBoxLayout()
        layout2.addWidget(button1)
        layout2.addWidget(button2)

        layout = qg.QVBoxLayout()
        layout.addWidget(self.le0)
        layout.addLayout(layout5)
#        layout.addWidget(self.unarylistwidget)
#        layout.addWidget(self.pairlistwidget)
        layout.addLayout(layout2)

        self.setLayout(layout)    

        button1.pressed.connect(self.accept)
        button2.pressed.connect(self.reject)
        
        self.le0.unary_selected.connect(lambda:self.pairlistwidget.setEnabled(False))
        self.le0.binary_selected.connect(lambda:self.pairlistwidget.setEnabled(True))
        self.le0.setCurrentIndex(index0)

    def acceptdata(self):
        unaryparents = self.unarylistwidget.currentRefs()
        pairparents = self.pairlistwidget.currentRefs()
        function = self.le0.currentText()
        return unaryparents, pairparents, function

class LaminateOperation(Operation):
    name = 'Laminate Op'
    unaryoperationtypes = ['union','intersection']    
    pairoperationtypes = ['difference','symmetric_difference']
    displayorder = unaryoperationtypes + pairoperationtypes
    attr_init = 'operation_links1','operation_links2','function'
    attr_init_k = tuple()
    attr_copy = 'id','customname'
    
    def __init__(self,*args,**kwargs):
        super(LaminateOperation,self).__init__()
        self.editdata(*args,**kwargs)
        self.id = id(self)
        
    def editdata(self,operation_links1,operation_links2,function):
        super(LaminateOperation,self).editdata()
        self.operation_links1 = operation_links1
        self.operation_links2 = operation_links2
        self.function = function

    def operate(self,design):
        if len(self.operation_links1)>0:
            laminates1 = [design.op_from_ref(link).output[ii].csg for link,ii in self.operation_links1]
        else:
            laminates1 = [Laminate(design.return_layer_definition())]

        if len(self.operation_links2)>0:
            laminates2 = [design.op_from_ref(link).output[ii].csg for link,ii in self.operation_links2]
        else:
            laminates2 = [Laminate(design.return_layer_definition())]
            
        if self.function in self.unaryoperationtypes:
            return Laminate.unaryoperation(laminates1,self.function)
        elif self.function in self.pairoperationtypes:
            laminate1 = Laminate.unaryoperation(laminates1,'union')
            laminate2 = Laminate.unaryoperation(laminates2,'union')
            return laminate1.binaryoperation(laminate2,self.function)
        
    @classmethod
    def buildnewdialog(cls,design,currentop):
        return Dialog(design.operations,0)

    def buildeditdialog(self,design):
        operationindeces1 = [(design.operation_index(ref),ii) for ref,ii in self.operation_links1]
        operationindeces2 = [(design.operation_index(ref),ii) for ref,ii in self.operation_links2]
        ii = self.displayorder.index(self.function)
        return Dialog(design.prioroperations(self),ii,operationindeces1,operationindeces2)

    def parentrefs(self):
        if self.function in self.unaryoperationtypes:
            return [ref for ref,ii in self.operation_links1]
        else:
            return [ref for ref,ii in self.operation_links1 + self.operation_links2]

    def upgrade(self,*args,**kwargs):
        from popupcad.manufacturing.laminateoperation2 import LaminateOperation2
        operation_links = {'unary':self.operation_links1,'binary':self.operation_links2}
        new = LaminateOperation2(operation_links,self.function)
        new.customname = self.customname
        new.id = self.id
        return new

#    def copy(self):
#        return self.upgrade()

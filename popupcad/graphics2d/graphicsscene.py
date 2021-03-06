# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import PySide.QtCore as qc
import PySide.QtGui as qg

import popupcad
from popupcad.graphics2d.static import Static
from popupcad.graphics2d.svg_support import SVGOutputSupport
from popupcad.geometry.vertex import DrawnPoint,BaseVertex
from popupcad.graphics2d.interactivevertex import DrawingPoint,StaticDrawingPoint
from popupcad.graphics2d.text import TextParent,GenericText
#import time

import numpy
from popupcad.graphics2d.interactivevertex import ReferenceInteractiveVertex
from popupcad.graphics2d.interactiveedge import ReferenceInteractiveEdge

class GraphicsScene(qg.QGraphicsScene,SVGOutputSupport):
    mode_select,mode_pan,mode_newgeometry = range(3)
    newpolygon = qc.Signal()
    itemclicked = qc.Signal(object)
    enteringeditmode = qc.Signal()
    leavingeditmode = qc.Signal()
    savesnapshot = qc.Signal()
    itemdeleted = qc.Signal()
    refresh_request = qc.Signal()

    def __init__(self):
        super(GraphicsScene,self).__init__()
        self.setSceneRect(qc.QRectF(0, 0, 1000,1000))
        self.setBackgroundBrush(qg.QBrush(qg.QPixmap(popupcad.backgroundpath)))
        self.snaptogrid= False
        self.gridsize = 20
        self.temp = None
        self.update()
        self.setItemIndexMethod(self.NoIndex)
        self.constraints_on= False
        self.extraobjects = []
        self.nextgeometry = None
    def addItem(self,item):
        super(GraphicsScene,self).addItem(item)
        try:
            item.updatescale()
        except AttributeError:
            pass
        
    def setIsEnabled(self,test):
        for item in self.items():
            if not isinstance(item,Static):
                item.setEnabled(test)
        
    def deleteall(self):
        for item in self.items():
            item.harddelete()
        self.update()

    def removeItem(self,item):
        self.saferemoveitem(item)
        
    def saferemoveitem(self,item):
        if item in self.items():
            super(GraphicsScene,self).removeItem(item)
                    
    def addpolygon(self,polygonclass):
        self.nextgeometry = polygonclass
        
    def returnpoint(self,point):
        if self.snaptogrid:
            gridsize = 1.*self.gridsize
            gridvalue = ((numpy.array(point.toTuple(),dtype=float)/gridsize).round()*gridsize)
            return qc.QPointF(*gridvalue)
        else:
            return point

    def sketch(self):
        return self._sketch
        
    def setsketch(self,sketch):
        self._sketch = sketch

    def screenShot(self):
        import os
        import popupcad
        
        from popupcad.graphics2d.svg_support import OutputSelection

        win = OutputSelection()
        accepted = win.exec_()
        if accepted:
            time = popupcad.basic_functions.return_formatted_time()
            self.renderprocess('2D_screenshot_'+time+'.svg',*win.acceptdata())

    def keyPressEvent(self,event):
        self.savesnapshot.emit()
        if event.key() == qc.Qt.Key_Delete:
            self.delete_selected_items()
        self.itemdeleted.emit()
        super(GraphicsScene,self).keyPressEvent(event)
            
    def cut_to_clipboard(self):
        self.copy_to_clipboard()
        self.delete_selected_items()

    def copy_to_clipboard(self):
        self.clipboard = [item for item in self.selectedItems() if hasattr(item,'copy')]

    def delete_selected_items(self):
        [item.softdelete() for item in self.selectedItems()]

    def paste_from_clipboard(self):
        [self.addItem(item.copy()) for item in self.clipboard]

    def deselectall(self):                
        [item.setSelected(False) for item in self.selectedItems()]
            
    def mousePressEvent(self, event):
        pos = self.returnpoint(event.scenePos())

        if self.temp!=None:
            if event.button() == qc.Qt.LeftButton:
                self.temp.mousepress(pos)            

        elif self.nextgeometry!=None:
            if event.button() == qc.Qt.LeftButton:
                if self.temp==None:
                    if self.nextgeometry==TextParent:
                        textpos = BaseVertex()
                        textpos.setpos(pos.toTuple())
                        text = GenericText('',textpos,font='Courier',fontsize=2)
                        temp = self.nextgeometry(text)
                        self.addItem(temp)
#                        self.setFocusItem(temp.editchild)
                        temp.editmode()
                        
#                        self.nextgeometry = None
                    elif self.nextgeometry==DrawingPoint:
                        temp = self.nextgeometry(DrawnPoint())
                        self.addItem(temp)
                        self.setFocusItem(temp)
                        temp.setPos(pos)
                        temp.updatescale()
                        self.childfinished()
#                        self.nextgeometry = None
                    else:
                        self.temp = self.nextgeometry()
                        self.addItem(self.temp)
                        self.setFocusItem(self.temp)
                        self.temp.mousepress(pos)
#                        self.nextgeometry = None
        else:
            super(GraphicsScene,self).mousePressEvent(event)
            self.leavingeditmode.emit()

    def mouseMoveEvent(self, event):
        pos = self.returnpoint(event.scenePos())
        if not self.temp==None:
            self.temp.mousemove(pos)
        else:
            super(GraphicsScene,self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        pos = self.returnpoint(event.scenePos())
        if not self.temp==None:
            self.temp.mouserelease(pos)
        else:
            super(GraphicsScene,self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self,event):
        pos = self.returnpoint(event.pos())
        if self.temp!=None:
            self.temp.mousedoubleclick(pos)
        else:
            super(GraphicsScene,self).mouseDoubleClickEvent(event)

    def childfinished(self):
        self.newpolygon.emit()
        self.updatevertices()
        self.temp=None

    def cancelcreate(self):
        self.nextgeometry = None
        try:
            self.temp.harddelete()
        except AttributeError:
            pass
        self.temp = None
        
    def showvertices(self,constraints_on):
#        if self.constraints_on:        
        self.constraints_on = constraints_on
#        else:
#            self.constraints_on = True
    def update_extra_objects(self,extraobjects):
        self.extraobjects = extraobjects
        
    def updatevertices(self):
#        self.removerefgeoms()
        self.removecontrolpoints()
        if self.constraints_on:            
            for item in self.items():
                try:
                    for child in item.children():
                        if not child in self.items():
                            self.addItem(child)
                except AttributeError:
                    pass
            for item in self.extraobjects:
                if not item in self.items():
                    self.addItem(item)
        else:
            for item in self.items():
                try:
                    for child in item.children():
                        child.removefromscene()
                except AttributeError:
                    pass
#            self.removecontrolpoints()
        self.views()[0].updatescaleables()

    def removerefgeoms(self):
        for item in self.items():
            if isinstance(item,Static):
                self.removeItem(item)
            if isinstance(item,StaticDrawingPoint):
                self.removeItem(item)
            if isinstance(item,ReferenceInteractiveVertex):
                self.removeItem(item)
            if isinstance(item,ReferenceInteractiveEdge):
                self.removeItem(item)

    def removecontrolpoints(self):
        for item in self.items():
            if isinstance(item,ReferenceInteractiveVertex):
                self.removeItem(item)
            if isinstance(item,ReferenceInteractiveEdge):
                self.removeItem(item)
        
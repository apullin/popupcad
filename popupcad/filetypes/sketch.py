# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
from popupcad.filetypes.constraints import ConstraintSystem
import popupcad
from popupcad.filetypes.popupcad_file import popupCADFile

class Sketch(popupCADFile):
    filetypes = {'sketch':'Sketch File'}
    defaultfiletype = 'sketch'
    
    @classmethod
    def lastdir(cls):
        return popupcad.lastsketchdir

    @classmethod
    def setlastdir(cls,directory):
        popupcad.lastsketchdir = directory

    def __init__(self):
        super(Sketch,self).__init__()
        self.operationgeometry = []
        self.constraintsystem = ConstraintSystem()

    def copy(self,identical = True):
        new = type(self)()
        new.operationgeometry = [geom.copy(identical=True) for geom in self.operationgeometry if geom.isValid()]
        new.constraintsystem = self.constraintsystem.copy()
        if identical:
            new.id = self.id
        self.copy_file_params(new,identical)
        return new

    def upgrade(self,identical = True):
        new = type(self)()
        new.operationgeometry = [geom.upgrade(identical=True) for geom in self.operationgeometry if geom.isValid()]
        new.constraintsystem = self.constraintsystem.upgrade()
        if identical:
            new.id = self.id
        self.copy_file_params(new,identical)
        return new

    def addoperationgeometries(self,polygons):
        self.operationgeometry.extend(polygons)

    def cleargeometries(self):
        self.operationgeometry = []

    def edit(self,parent,design = None,**kwargs):
        from popupcad.guis.sketcher import Sketcher
        sketcher = Sketcher(parent,self,design,accept_method = self.edit_result,**kwargs)
        sketcher.show()
        sketcher.graphicsview.zoomToFit()

    def edit_result(self,sketch):
        self.operationgeometry = sketch.operationgeometry
        self.constraintsystem = sketch.constraintsystem
        
    def output_csg(self):
        import popupcad.geometry.customshapely
        shapelygeoms = []
        for item in self.operationgeometry:
            try:
                if not item.is_construction():
                    shapelyitem = item.outputshapely()
                    shapelygeoms.append(shapelyitem)
            except ValueError as ex:
                print(ex)
            except AttributeError as ex:
                shapelyitem = item.outputshapely()
                shapelygeoms.append(shapelyitem)
        shapelygeoms = popupcad.geometry.customshapely.unary_union_safe(shapelygeoms)   
        shapelygeoms = popupcad.geometry.customshapely.multiinit(shapelygeoms)
        return shapelygeoms
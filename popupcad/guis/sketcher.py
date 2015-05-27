# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import sys
import PySide.QtGui as qg
import PySide.QtCore as qc
import popupcad
from popupcad.geometry.vertex import ShapeVertex,DrawnPoint
from popupcad.graphics2d.interactivevertex import InteractiveVertex,ReferenceInteractiveVertex,DrawingPoint,StaticDrawingPoint,InteractiveVertexBase
from popupcad.graphics2d.interactiveedge import InteractiveEdge,ReferenceInteractiveEdge,EdgeBase
from popupcad.graphics2d.interactive import Interactive, InteractiveLine
from popupcad.graphics2d.static import Static,StaticLine
from popupcad.graphics2d.proto import ProtoLine,ProtoPath,ProtoCircle,ProtoPoly,ProtoRect2Point
from popupcad.graphics2d.graphicsscene import GraphicsScene
from popupcad.graphics2d.graphicsview import GraphicsView
import popupcad.filetypes.constraints as constraints
from popupcad.filetypes.sketch import Sketch
from popupcad.widgets.listeditor import ListEditor,ListSelector
from popupcad.supportfiles import Icon
import numpy
from popupcad.widgets.widgetcommon import WidgetCommon
from popupcad.filetypes.undoredo import UndoRedo
from popupcad.widgets.dragndroptree import DraggableTreeWidget
from popupcad.manufacturing.nulloperation import NullOp
from popupcad.graphics2d.text import TextParent

class Sketcher(qg.QMainWindow,WidgetCommon):
    showprop = qc.Signal(object)
    def __init__(self,parent,sketch,design = None,accept_method = None,selectops = False):
        
        qg.QMainWindow.__init__(self,parent)
        self.design = design
        self.accept_method = accept_method
        self.selectops = selectops
                
        if self.design == None:
            self.operations = [NullOp()]
        else:
            self.operations = [NullOp()]+self.design.operations[:]

        self.setupLayout()   
        
        if self.selectops:
            self.optree.linklist(self.operations)


        self.undoredo = UndoRedo(self.get_current_sketch,self.loadsketch)
        self.loadsketch(sketch)
        self.undoredo.restartundoqueue()

        self.createActions()        
        
#        if self.selectops:
#            if ii!=None:
#                ii = ii+1
#            else:
#                ii = 0
#            self.optree.setCurrentIndeces(ii,jj)
        
        self.load_references()

        self.connectSignals()
    def connectSignals(self):
        self.setWindowModality(qc.Qt.WindowModality.ApplicationModal)
        self.setAttribute(qc.Qt.WA_DeleteOnClose)
        self.scene.itemclicked.connect(self.loadpropwindow)
        self.showprop.connect(self.loadpropwindow)
        self.scene.newpolygon.connect(self.undoredo.savesnapshot)
        self.scene.savesnapshot.connect(self.undoredo.savesnapshot)
        self.scene.itemdeleted.connect(self.cleanupconstraints)
        self.scene.refresh_request.connect(self.refreshconstraints)

        self.constraint_editor.signal_edit.connect(self.editItem)
        self.constraint_editor.itemPressed.connect(self.showconstraint_item)
        self.constraint_editor.itemdeleted.connect(self.constraint_deleted)        
        if self.selectops:
            self.optree.currentRowChanged.connect(self.load_references_inner)
        
    def setupLayout(self):
        self.constraint_editor = ListEditor()
        if self.selectops:
            self.optree = DraggableTreeWidget()
        self.propertieswindow = qg.QWidget()
        
        ok_button = qg.QPushButton('&Ok',self)
        cancel_button= qg.QPushButton('&Cancel',self)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        sublayout= qg.QHBoxLayout()
        sublayout.addStretch(1)
        sublayout.addWidget(ok_button)
        sublayout.addWidget(cancel_button)
        sublayout.addStretch(1)

        self.scene = GraphicsScene()
        self.graphicsview = GraphicsView(self.scene)
        
        centrallayout = qg.QVBoxLayout()
        centrallayout.addWidget(self.graphicsview)
        centrallayout.addLayout(sublayout)
        centralwidget = qg.QWidget()
        centralwidget.setLayout(centrallayout)

        if self.selectops:
            self.optreedock = qg.QDockWidget()
            self.optreedock.setWidget(self.optree)
            self.optreedock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
            self.optreedock.setWindowTitle('Operatons')

        self.constraintdock = qg.QDockWidget()
        self.constraintdock.setWidget(self.constraint_editor)
        self.constraintdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.constraintdock.setWindowTitle('Constraints')
        self.constraintdock.setMinimumHeight(200)

        self.propdock = qg.QDockWidget()
        self.propdock.setWidget(self.propertieswindow)
        self.propdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.propdock.setWindowTitle('Properties')
        self.propdock.setMinimumHeight(200)

        if self.selectops:
            self.addDockWidget(qc.Qt.LeftDockWidgetArea,self.optreedock)
        self.addDockWidget(qc.Qt.RightDockWidgetArea,self.constraintdock)
        self.addDockWidget(qc.Qt.RightDockWidgetArea,self.propdock)

        self.setCentralWidget(centralwidget)        
        self.setWindowTitle('Sketcher')

        self.set_nominal_size()
        self.move_center()

        if self.selectops:
            self.optreedock.closeEvent = lambda event: self.action_uncheck(self.act_view_ops)
        self.constraintdock.closeEvent = lambda event: self.action_uncheck(self.act_view_constraints)
        self.propdock.closeEvent = lambda event: self.action_uncheck(self.act_view_properties)
        
    def regen_id(self):
        self.sketch.regen_id()

    def editItem(self,constraint):
        self.undoredo.savesnapshot()
        constraint.edit()
        self.refreshconstraints()

    def createActions(self):
        self.fileactions = []
        self.fileactions.append({'text':"&New",'kwargs':{'triggered':self.newfile,'shortcut':qg.QKeySequence.New,'icon':Icon('new')}})
        self.fileactions.append({'text':"&Open...",'kwargs':{'triggered':self.open,'shortcut':qg.QKeySequence.Open,'icon':Icon('open')}})
        self.fileactions.append({'text':"Import...",'kwargs':{'triggered':self.solidworksimport,'icon':Icon('import')}})      
        self.fileactions.append({'text':"&Save",'kwargs':{'triggered':self.save,'shortcut':qg.QKeySequence.Save,'icon':Icon('save')}})
        self.fileactions.append({'text':"Save &As...",'kwargs':{'triggered':self.saveAs,'shortcut':qg.QKeySequence.SaveAs,'icon':Icon('saveas')}})      
        self.fileactions.append({'text':"Regen ID",'kwargs':{'triggered':self.regen_id}})      

        self.editactions = []
        self.editactions.append({'text':'Undo','kwargs':{'triggered':self.undoredo.undo,'shortcut':qg.QKeySequence.Undo,'icon':Icon('undo')}})      
        self.editactions.append({'text':'Redo','kwargs':{'triggered':self.undoredo.redo,'shortcut':qg.QKeySequence.Redo,'icon':Icon('redo')}})      
        self.editactions.append(None)      
        self.editactions.append({'text':'Cut','kwargs':{'triggered':self.cut_to_clipboard,'shortcut':qg.QKeySequence.Cut}})      
        self.editactions.append({'text':'Copy','kwargs':{'triggered':self.copy_to_clipboard,'shortcut':qg.QKeySequence.Copy}})      
        self.editactions.append({'text':'Paste','kwargs':{'triggered':self.paste_from_clipboard,'shortcut':qg.QKeySequence.Paste}})      
        self.editactions.append(None)      
        self.editactions.append({'text':'Group','kwargs':{'triggered':self.group,'shortcut':qc.Qt.CTRL+qc.Qt.Key_G}})      
        self.editactions.append({'text':'Unroup','kwargs':{'triggered':self.ungroup,'shortcut':qc.Qt.CTRL+qc.Qt.Key_U}})      

        self.viewactions = []
        def dummy(action):
            action.setCheckable(True)
            action.setChecked(True)
            self.act_view_ops= action
        self.viewactions.append({'prepmethod':dummy,'text':'Operations','kwargs':{'triggered':lambda:self.showhide2(self.optreedock,self.act_view_ops)}})
        def dummy(action):
            action.setCheckable(True)
            action.setChecked(True)
            self.act_view_constraints= action
        self.viewactions.append({'prepmethod':dummy,'text':'Constraints','kwargs':{'triggered':lambda:self.showhide2(self.constraintdock,self.act_view_constraints)}})
        def dummy(action):
            action.setCheckable(True)
            action.setChecked(True)
            self.act_view_properties= action
        self.viewactions.append({'prepmethod':dummy,'text':'Properties','kwargs':{'triggered':lambda:self.showhide2(self.propdock,self.act_view_properties)}})
        self.viewactions.append({'text':'select','kwargs':{'triggered':self.graphicsview.rubberband,'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_S,'icon':Icon('select')}})
        self.viewactions.append({'text':'pan','kwargs':{'triggered':self.graphicsview.scrollhand,'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_P,'icon':Icon('pan')}})
        self.viewactions.append(None)
        self.viewactions.append({'text':'Zoom Fit','kwargs':{'triggered':self.graphicsview.zoomToFit,'shortcut':qc.Qt.CTRL+qc.Qt.Key_F}})
        self.viewactions.append({'text':'Screenshot','kwargs':{'triggered':self.scene.screenShot,'shortcut': qc.Qt.CTRL+qc.Qt.Key_R}})
        
        self.drawingactions = []
        self.drawingactions.append({'text':'point','kwargs':{'triggered':self.adddrawingpoint,'icon':Icon('points')}})
        self.drawingactions.append({'text':'line','kwargs':{'triggered':lambda:self.addproto(ProtoLine),'icon':Icon('line')}})
        self.drawingactions.append({'text':'polyline','kwargs':{'triggered':lambda:self.addproto(ProtoPath),'icon':Icon('polyline')}})
        self.drawingactions.append({'text':'rect','kwargs':{'triggered':lambda:self.addproto(ProtoRect2Point),'icon':Icon('rectangle')}})
        self.drawingactions.append({'text':'circle','kwargs':{'triggered':lambda:self.addproto(ProtoCircle),'icon':Icon('circle')}})
        self.drawingactions.append({'text':'poly','kwargs':{'triggered':lambda:self.addproto(ProtoPoly),'icon':Icon('polygon')}})
        self.drawingactions.append({'text':'text','kwargs':{'triggered':lambda:self.addproto(TextParent),'icon':Icon('text')}})

        self.tools = []
#        self.drawingactions.append(None)
        self.tools.append({'text':'joinedges','kwargs':{'triggered':self.joinedges,'icon':Icon('joinedges')}})
        self.tools.append({'text':'autobridge','kwargs':{'triggered':self.autobridge,'icon':Icon('autobridge')}})
        self.tools.append({'text':'get joints','kwargs':{'triggered':self.getjoints,'icon':Icon('getjoints2')}})
        self.tools.append({'text':'flip direction','kwargs':{'triggered':self.flipdirection}})
        self.tools.append({'text':'hollow','kwargs':{'triggered':self.hollow}})
        self.tools.append({'text':'fill','kwargs':{'triggered':self.fill}})

        distanceactions = []
        distanceactions.append({'text':'Coincident','kwargs':{'triggered':lambda:self.add_constraint(constraints.coincident),'icon':Icon('coincident')}})
        distanceactions.append({'text':'Distance','kwargs':{'triggered':lambda:self.add_constraint(constraints.distance),'icon':Icon('distance')}})
        distanceactions.append({'text':'DistanceX','kwargs':{'triggered':lambda:self.add_constraint(constraints.distancex),'icon':Icon('distancex')}})
        distanceactions.append({'text':'DistanceY','kwargs':{'triggered':lambda:self.add_constraint(constraints.distancey),'icon':Icon('distancey')}})
        distanceactions.append({'text':'Fixed','kwargs':{'triggered':lambda:self.add_constraint(constraints.fixed)}})

        twolineactions = []
        twolineactions.append({'text':'Angle','kwargs':{'triggered':lambda:self.add_constraint(constraints.angle),'icon':Icon('angle')}})
        twolineactions.append({'text':'Parallel','kwargs':{'triggered':lambda:self.add_constraint(constraints.parallel),'icon':Icon('parallel')}})
        twolineactions.append({'text':'Perpendicular','kwargs':{'triggered':lambda:self.add_constraint(constraints.perpendicular),'icon':Icon('perpendicular')}})
        twolineactions.append({'text':'Equal','kwargs':{'triggered':lambda:self.add_constraint(constraints.equal),'icon':Icon('equal')}})
        twolineactions.append({'text':'Horizontal','kwargs':{'triggered':lambda:self.add_constraint(constraints.horizontal),'icon':Icon('horizontal')}})
        twolineactions.append({'text':'Vertical','kwargs':{'triggered':lambda:self.add_constraint(constraints.vertical),'icon':Icon('vertical')}})

        self.constraintactions = []

        def dummy(action):
            action.setCheckable(True)
            action.setChecked(False)
            self.act_view_vertices= action
            
        self.constraintactions.append({'prepmethod':dummy,'text':'Constraints On','kwargs':{'triggered':self.showvertices,'icon':Icon('showconstraints')}})
        self.constraintactions.append(None)
        self.constraintactions.append({'text':'Distance','submenu':distanceactions,'kwargs':{'icon':Icon('distance')}})
        self.constraintactions.append({'text':'Lines','submenu':twolineactions,'kwargs':{'icon':Icon('parallel')}})
        self.constraintactions.append({'text':'PointLine','kwargs':{'triggered':lambda:self.add_constraint(constraints.PointLine),'icon':Icon('pointline')}})
        self.constraintactions.append({'text':'Midpoint','kwargs':{'triggered':lambda:self.add_constraint(constraints.LineMidpoint)}})
        self.constraintactions.append({'text':'Update','kwargs':{'triggered':self.refreshconstraints_button,'icon':Icon('refresh')}})
        self.constraintactions.append({'text':'Cleanup','kwargs':{'triggered':self.cleanupconstraints,'icon':Icon('broom')}})

        self.menu_file = self.addMenu(self.fileactions,name='File')
        self.menu_edit = self.addMenu(self.editactions,name='Edit')
        self.toolbar_drawing,self.menu_drawing = self.addToolbarMenu(self.drawingactions,name='Drawing')
        self.toolbar_tools,self.menu_tools = self.addToolbarMenu(self.tools,name='Drawing')
        self.toolbar_constraints,self.menu_constraints = self.addToolbarMenu(self.constraintactions,name='Constraints')
        self.menu_view = self.addMenu(self.viewactions,name='View')

    def cut_to_clipboard(self):
        self.undoredo.savesnapshot()
        self.scene.cut_to_clipboard()
    def copy_to_clipboard(self):
        self.undoredo.savesnapshot()
        self.scene.copy_to_clipboard()
    def paste_from_clipboard(self):
        self.undoredo.savesnapshot()
        self.scene.paste_from_clipboard()

    def add_constraint(self,constraintclass):
        from popupcad.filetypes.genericshapes import GenericLine
        self.undoredo.savesnapshot()
        items = []
        new_constraints = []
        
        for item in self.scene.selectedItems():
            if isinstance(item,ReferenceInteractiveVertex):
                generic = item.get_generic()
                newgeneric = generic.copy_values(DrawnPoint(),False)
                newitem = newgeneric.gen_interactive()
                self.scene.addItem(newitem)
                items.append(newgeneric)
                item.setSelected(False)
                newitem.setSelected(True)
                new_constraints.append(constraints.fixed.new(newgeneric))

            elif isinstance(item,ReferenceInteractiveEdge):
                generic = item.get_generic()
                v1 = generic.vertex1.copy_values(ShapeVertex(),False)
                v2 = generic.vertex2.copy_values(ShapeVertex(),False)
                new_constraints.append(constraints.fixed.new(v1,v2))

                l = GenericLine([v1,v2],[],construction = True)

                a = l.outputinteractive()
#                b = v1.gen_interactive()
#                c = v2.gen_interactive()
                self.scene.addItem(a)
#                self.scene.addItem(b)
#                self.scene.addItem(c)
                
                item.setSelected(False)
                a.setSelected(True)
#                b.setSelected(True)
#                c.setSelected(True)
                items.append(a.selectableedges[0].get_generic())

            elif isinstance(item,InteractiveVertex):
                items.append(item.get_generic())
            elif isinstance(item,InteractiveEdge):
                items.append(item.get_generic())
            elif isinstance(item,InteractiveLine):
                items.append(item.selectableedges[0].get_generic())
            elif isinstance(item,StaticLine):
                items.append(item.selectableedges[0].get_generic())
            elif isinstance(item,DrawingPoint):
                items.append(item.get_generic())
            elif isinstance(item,StaticDrawingPoint):
                items.append(item.get_generic())
                                         
        new_constraints .append(constraintclass.new(*items))
        for constraint in new_constraints:
            self.sketch.constraintsystem.add_constraint(constraint)
        self.refreshconstraints()

    def refreshconstraints_button(self):
#        self.undoredo.savesnapshot()
        self.refreshconstraints()
    def constraint_deleted(self):
#        self.undoredo.savesnapshot()
        self.refreshconstraints()
    def refreshconstraints(self):
#        self.undoredo.savesnapshot()
        self.sketch.constraintsystem.regenerate()
        self.sketch.constraintsystem.update()

        for item in self.scene.items():
            try:
                item.updateshape()
            except AttributeError:
                pass
        
        self.constraint_editor.refresh()

    def buildvertices(self):
        self.buildsketch()
        
        vertices = []
        control =  [item.get_generic() for item in self.controlpoints+self.controllines]       

        for geom in self.sketch.operationgeometry+control:
            vertices.extend(geom.vertices())
        return vertices

    def cleanupconstraints(self):
#        self.sketch.constraintsystem.update()
        self.sketch.constraintsystem.cleanup()
        self.constraint_editor.refresh()
        self.sketch.constraintsystem.regenerate()

    def showconstraint_item(self,obj1):
        self.showprop.emit(obj1.customdata)
        self.scene.clearSelection()
        vertices = [item for item in self.scene.items() if isinstance(item,InteractiveVertexBase)]
        for v in vertices:
            if v.get_generic().id in obj1.customdata.vertex_ids:
                v.setSelected(True)
        pass
        edges = [item for item in self.scene.items() if isinstance(item,InteractiveEdge) or isinstance(item,ReferenceInteractiveEdge)]
        for edge in edges:
            c= tuple(sorted([item.id for item in edge.generic.vertices()]))
            if c in obj1.customdata.segment_ids:
                edge.setSelected(True)

    def loadsketch(self,sketch):
        self.sketch = sketch.copy()
        self.scene.deleteall()
        self.scene.setsketch(self.sketch)
        for item in self.sketch.operationgeometry:
            newitem = item.outputinteractive()
            self.scene.addItem(newitem)
            newitem.refreshview()

        self.constraint_editor.linklist(self.sketch.constraintsystem.constraints)
        self.sketch.constraintsystem.link_vertex_builder(self.buildvertices)
        
    def showvertices(self):
        self.scene.showvertices(self.act_view_vertices.isChecked())
        self.scene.updatevertices()

    def buildsketch(self):
        self.sketch.cleargeometries()
        geometries = [item.generic for item in self.scene.items() if isinstance(item,Interactive) if item.generic.isValid()]
        geometries.extend([item.generic for item in self.scene.items() if isinstance(item,DrawingPoint)])
        geometries.extend([item.generic for item in self.scene.items() if isinstance(item,TextParent)])
        self.sketch.addoperationgeometries(geometries)

    def get_current_sketch(self):
        self.buildsketch()
        return self.sketch
        
    def newfile(self):
        sketch = popupcad.filetypes.sketch.Sketch()
        self.loadsketch(sketch)
        self.undoredo.restartundoqueue()

    def solidworksimport(self):
        from popupcad.filetypes.solidworksimport import Assembly
        a = Assembly.open()
        sketch = a.build_face_sketch()
        self.loadsketch(sketch)
        self.undoredo.restartundoqueue()

    def open(self):
        sketch = popupcad.filetypes.sketch.Sketch.open()
        if not sketch==None:
            self.loadsketch(sketch)
            self.undoredo.restartundoqueue()

    def save(self):
        self.buildsketch()
        self.sketch.save()
        
    def saveAs(self):
        self.buildsketch()
        self.sketch.saveAs()

    def adddrawingpoint(self):
        self.graphicsview.turn_off_drag()
        self.scene.addpolygon(DrawingPoint)
        
    def addproto(self,proto):
        self.graphicsview.turn_off_drag()
        self.scene.addpolygon(proto)

    def joinedges(self):
        from popupcad.graphics2d.interactivevertexbase import InteractiveVertexBase
        from popupcad.graphics2d.interactiveedge import InteractiveEdge
        
        selecteditems = self.scene.selectedItems()
        genericvertices = []
        for item in selecteditems:
            if isinstance(item,InteractiveVertexBase):
                genericvertices.append(item.get_generic())
            elif isinstance(item,InteractiveEdge):
                genericvertices.extend(item.get_generic().vertices())
        vertices2 = [vertex.getpos() for vertex in genericvertices]
        vertices2 = numpy.array(vertices2)        
        poly = popupcad.algorithms.autobridge.joinedges(vertices2)
        self.scene.addItem(poly.outputinteractive())

    def autobridge(self):
        interactives = [item for item in self.scene.items() if isinstance(item,Interactive)]
        
        handles = []
        [handles.extend(item.handles()) for item in interactives]
        try:
            handles.extend(self.controlpoints)        
        except AttributeError:
            pass
        handles.extend([item for item in self.scene.items() if isinstance(item,DrawingPoint)])
        vertices = []
        for handle in handles:
            scenepos = handle.scenePos()
            vertices.append((scenepos.x(),scenepos.y()))
        polys = popupcad.algorithms.autobridge.autobridge(vertices)
        [self.scene.addItem(poly.outputinteractive()) for poly in polys]     
        
    def getjoints(self):
        import popupcad.algorithms.getjoints as gj
        items = []
        for item in self.scene.items():
            if isinstance(item,Interactive):
                items.append(item.generic)
                item.removefromscene()
        genericlines = gj.getjoints(items)
        [self.scene.addItem(line) for line in genericlines]
        

    def showconstraint(self,row):
        item = self.constraint_editor.item(row)
        self.showconstraint_item(item)

    def accept(self):
        if self.accept_method!=None:
            self.accept_method(*self.acceptdata())
        self.close()

    def reject(self):
        self.close()

    def keyPressEvent(self,event):
        if not self.keypressfiltering(event):
            super(Sketcher,self).keyPressEvent(event)
    
    def loadpropwindow(self,obj):
        widget = obj.properties()
        self.propdock.setWidget(widget)        
        
    def acceptdata(self):
        self.buildsketch()
        return self.sketch,

    def keypressfiltering(self,event):
        if event.key() == qc.Qt.Key_Escape:
            return True
        elif event.key() == qc.Qt.Key_Enter:
            return True
        elif event.key() == qc.Qt.Key_Return:
            return True
        else:
            return False

    def load_references3(self,ii,jj):
        staticgeometries,controlpoints,controllines = [],[],[]        
        ii-=1
        if ii>=0:
            if self.design !=None:
                print(ii,jj)
                try:
                    operationgeometries = self.design.operations[ii].output[jj].controlpolygons()
                    staticgeometries =  [item.outputstatic() for item in operationgeometries]
    
                    controlpoints = self.design.operations[ii].output[jj].controlpoints()
                    controlpoints = [point.gen_interactive() for point in controlpoints]
    
                    controllines = self.design.operations[ii].output[jj].controllines()
                    controllines = [line.gen_interactive() for line in controllines]
                except (IndexError,AttributeError):
                    pass
        return staticgeometries,controlpoints,controllines
    
    def load_references_inner(self,ii,jj):
        self.scene.removerefgeoms()
        self.static_items,self.controlpoints,self.controllines = self.load_references3(ii,jj)
        self.scene.update_extra_objects(self.controlpoints+self.controllines)
        self.scene.updatevertices()
        [self.scene.addItem(item) for item in self.static_items]

    def load_references(self):
        if self.selectops:
            selected_indeces = self.optree.currentIndeces2()
            if len(selected_indeces)>0:
                ii,jj = selected_indeces[0]
                self.load_references_inner(ii,jj)

    def group(self):
        from popupcad.graphics2d.grouper import Grouper
        o = Grouper()        
        selecteditems = self.scene.selectedItems()
        associateditems = [vertex for item in selecteditems if hasattr(item,'handles') for vertex in item.handles()]
        selecteditems+associateditems
        o.addchildren(associateditems)
        self.scene.addItem(o)
        
    def ungroup(self):
        from popupcad.graphics2d.grouper import Grouper
        for item in self.scene.selectedItems():
            if isinstance(item,Grouper):
                item.resetTransform()
                item.setPos(0,0)
                item.removegroupeditems()
                item.softdelete()
    def flipdirection(self):
        selecteditems = self.scene.selectedItems()
        for item in selecteditems:
            item.generic.flip()
            item.updateshape()
    def hollow(self):
        selecteditems = self.scene.selectedItems()
        newgenerics = []
        for item in selecteditems:
            newgenerics.append(item.generic.hollow())
            item.harddelete()
        for item in newgenerics:
            self.scene.addItem(item.outputinteractive())
    def fill(self):
        selecteditems = self.scene.selectedItems()
        newgenerics = []
        for item in selecteditems:
            newgenerics.append(item.generic.fill())
            item.harddelete()
        for item in newgenerics:
            self.scene.addItem(item.outputinteractive())

                
if __name__ == "__main__":
    app = qg.QApplication(sys.argv)
    mw = Sketcher(None,Sketch())
    mw.show()
    mw.raise_()
    sys.exit(app.exec_())        
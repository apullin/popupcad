# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import PySide.QtGui as qg

class FileMissing(Exception):
    def __init__(self,filename):
        super(FileMissing,self).__init__('Child File Missing:{filename}'.format(filename=filename) )

class GenericFile(object):
    filetypes = {'file':'Generic File'}
    defaultfiletype = 'file'
    _lastdir = '.'
    def __init__(self):
        self.id = id(self)
        self.set_basename(self.genbasename())
        
    def get_basename(self):
        try:
            return self._basename
        except AttributeError:
            self._basename = self.genbasename()
            return self._basename

    def copy(self,identical = True):
        new = type(self)()
        self.copy_file_params(new,identical)
        return new

    def upgrade(self,*args,**kwargs):
        return self

    @classmethod
    def lastdir(cls):
        return cls._lastdir

    @classmethod
    def setlastdir(cls,directory):
        cls._lastdir = directory

    @classmethod
    def get_parent_program_name(self):
        return None
        
    @classmethod
    def get_parent_program_version(self):
        return None

    def copy_file_params(self,new,identical):
        try:
            new.dirname = self.dirname
        except AttributeError:
            pass

        try:
            if identical:
                new.set_basename(self.get_basename())
            else:
                new.set_basename(new.genbasename())
        except AttributeError:
            pass
        
        try:
            new.parent_program_name = self.parent_program_name
        except AttributeError:
            pass
        try:
            new.parent_program_version = self.parent_program_version
        except AttributeError:
            pass

        return new

    def genbasename(self):
        basename = str(self.id)+'.'+self.defaultfiletype
        return basename

    def set_basename(self,basename):
        self._basename = basename

    @classmethod
    def buildfilters(cls):
        filters = {}
        for filetype,name in cls.filetypes.items():
            filters[filetype] = '{0}(*.{1})'.format(name,filetype)
        filterstring = ''.join([item+';;' for item in filters.values()])
        selectedfilter=filters[cls.defaultfiletype]
        return filterstring,selectedfilter
        
            
    def updatefilename(self,filename):
        import os
        try:
            del self.filename
        except AttributeError:
            pass
        self.dirname,self._basename = os.path.split(filename)
        self.setlastdir(self.dirname)

#    @classmethod
#    def updatefilter(cls,selectedfilter):
#        cls.selectedfilter = selectedfilter
        
    @classmethod
    def load_yaml(cls,filename):
        import yaml
        with open(filename,'r') as f:
            obj1 = yaml.load(f)
        obj1.updatefilename(filename)
        return obj1
    
    @classmethod
    def load_dxf(cls,filename):
        import dxfgrabber
        #Do these imports imply that this function should be moved to a derived class?
        import popupcad 
        
        from popupcad.geometry.vertex import ShapeVertex
        from popupcad.filetypes.genericshapes import GenericShapeBase
        from popupcad.filetypes.genericshapes import GenericPoly,GenericPolyline,GenericLine,GenericCircle,GenericTwoPointRect
        from popupcad.manufacturing.simplesketchoperation import SimpleSketchOp

        #Read in the DXF
        dxf = dxfgrabber.readfile(filename)
            
        names = dxf.layers.names()
        bylayer = {}
        for layname in names:
            bylayer[layname] = popupcad.filetypes.sketch.Sketch()
        
        for ent in dxf.entities:
            print ent
            lay = ent.layer
            if type(ent) is dxfgrabber.entities.Circle:
                vert_center = ShapeVertex(ent.center)
                pt_edge = (ent.center[0] + ent.radius, ent.center[1])
                vert_edge = ShapeVertex(pt_edge)
                circ = GenericCircle(exterior = [vert_center, vert_edge], interiors = [])
                bylayer[lay].operationgeometry.append(circ)
                
            elif type(ent) is dxfgrabber.entities.LWPolyline:
                poly = GenericShapeBase.gengenericpoly(ent.points,[])
                bylayer[lay].operationgeometry.append(poly)
                
        print bylayer
        
        sketches = {}
        # This seems like an odd operation, like I am not leveraging some existing key/value construction elsewhere
        # This converts the named DXF layer dict into one keyed by popupcad id's
        for sk in bylayer.values():
            sketches[sk.id] = sk
        
        from popupcad.filetypes.layerdef import LayerDef
        from popupcad.materials.materials import Carbon_0_90_0,Pyralux,Kapton
        from popupcad.filetypes.design import Design
        
        design = Design()
        # default Wood Lab 5-layer
        design.define_layers(LayerDef(Carbon_0_90_0(),Pyralux(),Kapton(),Pyralux(),Carbon_0_90_0()))
        design = Design()
        
        # Assign collection of sketches from above
        design.sketches = sketches
        
        # Generate sketch ops
        layer_links_all = [lay.id for lay in design._layerdef.layers]
        sketch_ops = []
        for sk in sketches.values():
            sketch_links = {'sketch':[sk.id]}
            sketch_ops.append(SimpleSketchOp(sketch_links, layer_links_all))
        
        design.operations = sketch_ops
        
        design.updatefilename(filename)
        
        return design

    @classmethod
    def open_filename(cls,parent = None,openmethod = None,**openmethodkwargs):
        filterstring,selectedfilter = cls.buildfilters()
        filename, selectedfilter = qg.QFileDialog.getOpenFileName(parent,'Open',cls.lastdir(),filter = filterstring,selectedFilter = selectedfilter)
        if filename:
            ext = filename[-3:]
            if ext == u'dxf':
                openmethod = cls.load_dxf
            elif ext == u'eps':
                pass #Fake placeholder, example of where to add in openmethod selection for other types
            
            if openmethod == None:
                object1 = cls.load_yaml(filename)
            else:
                object1 = openmethod(filename,**openmethodkwargs)
#            object1.updatefilter(selectedfilter)
            return filename, object1
        else:
            return None,None
            
    @classmethod
    def open(cls,*args,**kwargs):
        filename,object1 = cls.open_filename(*args,**kwargs)
        return object1
            
    def save(self,parent = None,savemethod = None,**savemethodkwargs):
        try:
            if savemethod == None:
                return self.save_yaml(self.filename())
            else:
                return savemethod(self.filename(),**savemethodkwargs)
        except AttributeError:
            return self.saveAs(parent)

    def regen_id(self):
        import random
        self.id = int(random.randint(0,9999999999))
                    
    def saveAs(self,parent = None,savemethod = None,**savemethodkwargs):
        import os
        try:
            tempfilename = os.path.normpath(os.path.join(self.dirname,self.get_basename())) 
        except AttributeError:
            try:
                basename = self.get_basename()
            except AttributeError:
                basename = self.genbasename()
                
            tempfilename = os.path.normpath(os.path.join(self.lastdir(),basename))                
            
        filterstring,selectedfilter = self.buildfilters()
        filename, selectedfilter = qg.QFileDialog.getSaveFileName(parent, "Save As", tempfilename,filter = filterstring,selectedFilter = selectedfilter)
        if not filename:
            return False
        else:
#            self.updatefilter(selectedfilter)
            if savemethod == None:
                return self.save_yaml(filename)
            else:
                return savemethod(self.filename(),**savemethodkwargs)

    def filename(self):
        import os
        return os.path.normpath(os.path.join(self.dirname,self.get_basename()))              
            
    def save_yaml(self,filename,identical = True):
        import yaml
        self.updatefilename(filename)
        self.parent_program_name = self.get_parent_program_name()
        self.parent_program_version = self.get_parent_program_version()
        new = self.copy(identical)
        with open(filename,'w') as f:        
            yaml.dump(new,f)
        return True
        
    def __str__(self):
        return self.get_basename()

    def __repr__(self):
        return str(self)


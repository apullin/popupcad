# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""

import numpy

def find_minimum_xy(geom):
    points = numpy.array(geom.exteriorpoints())
    min_x,min_y = points.min(0)
    return min_x,min_y
    
def sort_lams(lams,values):
    dtype = [('x',float),('y',float)]
    mins = numpy.array(values,dtype)
    ii_mins = mins.argsort(order=['x','y'])
    lam_out = [lams[ii] for ii in ii_mins]
    return lam_out


def find(generic,layerdef):
    from popupcad.filetypes.laminate import Laminate
    
    layer_dict = dict([(geom.id,layer) for layer,geoms in generic.items() for geom in geoms])
    geom_dict = dict([(geom.id,geom) for layer,geoms in generic.items() for geom in geoms])
    geom_dict_whole = geom_dict.copy()
    
    laminates = []
    values = []
    while len(geom_dict)>0:
        laminate = Laminate(layerdef)
        key = list(geom_dict.keys())[0]
        gs = findallconnectedneighborgeoms(key,generic,geom_dict,layerdef)
        geom_mins = numpy.array([find_minimum_xy(geom_dict_whole[geom_id]) for geom_id in gs])
        values.append(tuple(geom_mins.min(0)))
        for item_id in gs:
            geom = geom_dict_whole[item_id]
            laminate.insertlayergeoms(layer_dict[item_id], [geom.outputshapely()])
        laminates.append(laminate)
    laminates = sort_lams(laminates,values)
    return laminates
    
def findallconnectedneighborgeoms(geomid,generic_geometry,geom_dict,layerdef):
    '''find all the connected shapes'''
    connectedgeomids = [geomid]
    testids= [geomid]
    while len(testids)>0:
        result = findconnectedneighborgeoms(testids.pop(),generic_geometry,geom_dict,layerdef)
        result = list(set(result)-set(connectedgeomids))
        testids.extend(result)
        connectedgeomids.extend(result)
    [geom_dict.pop(item) for item in connectedgeomids]
    return connectedgeomids

def findconnectedneighborgeoms(geomid,generic_geometry,geom_dict,layerdef):
    '''find geoms in neighboring layers which are overlapping'''
    geom = geom_dict[geomid]
    geom = geom.outputshapely()
    layer = findgeomlayerinstep(geomid,generic_geometry)
    neighbors = layerdef.connected_neighbors(layer)
    validneighbors = []
    for neighbor in neighbors:
        for item in generic_geometry[neighbor]:
            shapelygeom = item.outputshapely() 
            result = geom.intersection(shapelygeom)
            if not result.is_empty:                    
                validneighbors.append(item.id)
            else:
                pass
    return validneighbors        

def findgeomlayerinstep(geomid,generic_geometry_2d):
    '''Find the layer of a laminate a given shape is in'''
    for layer,geoms in generic_geometry_2d.items():
        if geomid in [geom.id for geom in geoms]:
            return layer     

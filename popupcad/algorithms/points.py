# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import numpy

def twopointsthesame(pt1,pt2,tolerance):
    v = numpy.array(pt2)-numpy.array(pt1)
    l = v.dot(v)**.5
    return l<tolerance
        
def pointinpoints(pt1,pts,tolerance):
    tests = [twopointsthesame(pt1,pt2,tolerance) for pt2 in pts]
    return True in tests

def point_on_line(point,line,tolerance):
    point = numpy.array(point)
    p1 = numpy.array(line[0])
    p2 = numpy.array(line[1])
    v = p2 - p1
    lv = v.dot(v)
    
    v2 = point - p1
    lv2 = v2.dot(v2)
    vpoint = v.dot(v2)**2 - lv*lv2
    vpoint = abs(vpoint)**(.5)
    return abs(vpoint)<abs(tolerance)

def colinear(line1,line2,tolerance):
    a = point_on_line(line2[0],line1,tolerance)
    b = point_on_line(line2[1],line1,tolerance)
    return a and b
    
def point_within_line(point,line,tolerance):
    point = numpy.array(point)
    p1 = numpy.array(line[0])
    p2 = numpy.array(line[1])
    v = p2 - p1
    v2 = point - p1
    lv = v.dot(v)**.5
    lv2 = v2.dot(v2)**.5
    v_dot_v2 = v.dot(v2)
    same_orientation = v_dot_v2>0 
    within = lv2<lv 
    same_direction = abs(abs(v_dot_v2)-(lv*lv2))<tolerance    
    return same_direction and same_orientation and within
    
def order_vertices(vertices,segment_seed,tolerance):
    vertices = list(set(vertices))
    ordering = list(segment_seed)
    while vertices:
        c = vertices.pop()
        a = ordering[0]
        b = ordering[-1]
        if point_within_line(a,[c,b],tolerance):
            ordering.insert(0,c)
        elif point_within_line(b,[a,c],tolerance):
            ordering.append(c)
        else:
            for ii,b in enumerate(ordering[1:]):
                if point_within_line(c,[a,b],tolerance):
                    ordering.insert(ii+1,c)
                    break
    return ordering

def segment_midpoints(segments):
    segments = numpy.array(segments)
    a = segments.sum(1)/2
    return a.tolist()
    
def distance_of_lines(lines,point = [0,0]):
    point = numpy.array(point)
    lines2 = numpy.array(lines)
    v1 = lines2[:,1,:] - lines2[:,0,:]
    l1 = (v1**2).sum(1)**.5
    v2 = lines2[:,0,:] - point
    v3 = numpy.cross(v1,v2)
    l3 = v3/l1
    return abs(l3)

def shared_edge(line1,line2,tolerance):
    if colinear(line1,line2,tolerance):
        a = point_within_line(line2[0],line1,tolerance)
        b = point_within_line(line2[1],line1,tolerance)
        return a or b
    return False

def inner_segment(line1,line2,tolerance):
    points = line1
    if point_within_line(line2[0],line1,tolerance):
        if point_within_line(line1[0],(line2[0],line1[1]),tolerance):
            points = (line1[0],line2[0])
        elif point_within_line(line1[1],(line2[0],line1[0]),tolerance):
            points = (line1[1],line2[0])
        else:
            points = line2
            
    if point_within_line(line2[1],line1,tolerance):
        if point_within_line(line1[0],(line2[1],line1[1]),tolerance):
            points = (line1[0],line2[1])
        elif point_within_line(line1[1],(line2[1],line1[0]),tolerance):
            points = (line1[1],line2[1])
        else:
            points = line2

    return points
        
def calctransformfrom2lines(pointset1,pointset2,scale_x = None,scale_y = None):
    import math
    pointset1 = numpy.array(pointset1)
    pointset2 = numpy.array(pointset2)
    v1 = pointset1[1]-pointset1[0]
    v2 = pointset2[1]-pointset2[0]
    q1 = math.atan2(v1[1],v1[0])
    q2 = math.atan2(v2[1],v2[0])
    l1 = v1.dot(v1)**.5
    l2 = v2.dot(v2)**.5
    scale_internal = l2/l1

    if scale_x == None:
        scale_x = scale_internal
    if scale_y == None:
        scale_y = scale_internal
    
    T0 = numpy.eye(3)
    T0[0:2,2] = -pointset1[0]

    T1 = numpy.eye(3)
    T1[0,0] = math.cos(-q1)
    T1[0,1] = -math.sin(-q1)
    T1[1,1] = math.cos(-q1)
    T1[1,0] = math.sin(-q1)

    T2 = numpy.eye(3)
    T2[0,0] = scale_x
    T2[1,1] = scale_y
    
    T3 = numpy.eye(3)
    T3[0,0] = math.cos(q2)
    T3[0,1] = -math.sin(q2)
    T3[1,1] = math.cos(q2)
    T3[1,0] = math.sin(q2)
    T3[0:2,2] = pointset2[0]
    
    T = T3.dot(T2.dot(T1.dot(T0)))
    return T[0,0],T[0,1],T[1,0],T[1,1],T[0,2],T[1,2]  

def angle_between_lines(pointset1,pointset2,scale_x = None,scale_y = None):
    import math
    pointset1 = numpy.array(pointset1)
    pointset2 = numpy.array(pointset2)
    v1 = pointset1[1]-pointset1[0]
    v2 = pointset2[1]-pointset2[0]

    l1 = (v1.dot(v1))**.5
    l2 = (v2.dot(v2))**.5

    cq = v1.dot(v2)/(l1*l2)
    q1 = math.acos(cq)
    return q1

def convert_to_3d(listin):
    a = numpy.array(listin)
    c = a.T[0]*0
    d = numpy.concatenate((a.T,[c]),0)
    a = d.T
    return a.tolist()

def jointholes(sketch_result,layerdef):
    import popupcad
    import operator
    import math
    from popupcad.filetypes.laminate import Laminate
    generic = sketch_result.genericfromls()
    for key,value in generic.items():
        if not not value:
            allgeoms = value
            hingelayer = key
    allpoints = []
    for geom in allgeoms:
        allpoints.extend(geom.exteriorpoints())
    allpoints.sort()
    commonpoints = []
    
    for ii,point1 in enumerate(allpoints[1:-1]):
        point0 = allpoints[ii]
        point2 = allpoints[ii+2]
        a = popupcad.algorithms.points.twopointsthesame(point1,point2,1e-5)
        b = popupcad.algorithms.points.twopointsthesame(point0,point1,1e-5)
        if ii==0:
            if b:
                commonpoints.append(point1)
            elif a:
                commonpoints.append(point1)
        else:
            if (a and (not b)):
                commonpoints.append(point1)

    shapelys = []
    for point in commonpoints:
        lineset = {}
        for item in allgeoms:
            points = numpy.array(item.exteriorpoints())
            points -= point
            l = (points[:,0]**2+points[:,1]**2)**.5
            test = l<1e-5
            if True in test:
                ii = 1-test.nonzero()[0][0]
                lineset[item] = math.atan2(points[ii,1],points[ii,0])
        q_s = sorted(lineset.items(),key = operator.itemgetter(1))
        gaps = [item1[1]-item0[1] for item0,item1 in zip(q_s[:-1],q_s[1:])] + [2*math.pi+q_s[0][1]-q_s[-1][1]]
        min_gap = min(gaps)
        bufferval = 1.1/math.sin(min_gap/2)
#            print(gaps,min_gap,bufferval)
        shapely = popupcad.geometry.vertex.DrawnPoint(position = point).outputshapely()
        shapely = shapely.buffer(bufferval*popupcad.internal_argument_scaling)
        shapelys.append(shapely)
    shapelys = popupcad.geometry.customshapely.multiinit(*shapelys)
#        generics = [popupcad.geometry.vertex.DrawnPoint(position = point) for point in commonpoints]
#        shapelys = [item.outputshapely() for item in generics]
#        layer = Layer(shapelys)
    holes = Laminate(layerdef)
    holes.replacelayergeoms(hingelayer,shapelys)
    return holes,allgeoms,hingelayer 


if __name__=='__main__':
#    print(colinear([[0,0],[1,1]],[[.1,.1+.9e-3],[.9,.9]],1e-3))
#    print(point_within_line([2,0],[[0,0],[1,0]],1e-3))
#    print(colinear([[0,0],[1,1]],[[-.1,-.1+.9e-3],[-.9,-.9]],1e-3))
#    print(shared_edge([[0,0],[1,1]],[[-.1,-.1+.9e-3],[-.9,-.9]],1e-3))y
    point = [.001,0.001]
    line = [[-1,-1],[1,1]]
    tol = 1e-10
#    print(point_within_line(point,line,tol))

    import random
    points = [(random.random(),1.1) for item in range(10)]
    a = order_vertices(points,1e-5)
    segments = []
    while points:
        segments.append((points.pop(),points.pop()))
    
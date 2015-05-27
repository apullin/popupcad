# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""

from popupcad.manufacturing.multivalueoperation3 import MultiValueOperation3

class ToolClearance3(MultiValueOperation3):
    name = 'ToolClearance'
    valuenames = []
    defaults = []

    def operate(self,design):
        import popupcad_manufacturing_plugins.algorithms.toolclearance as toolclearance
        operation_ref,output_index = self.operation_links['parent'][0]
        
        ls1 = design.op_from_ref(operation_ref).output[output_index].csg

        if self.keepout_type == self.keepout_types.laser_keepout:
            toolclearance = toolclearance.laserclearance(ls1)
        elif self.keepout_type == self.keepout_types.mill_keepout:
            toolclearance = toolclearance.millclearance(ls1)
        elif self.keepout_type == self.keepout_types.mill_flip_keepout:
            toolclearance = toolclearance.millflipclearance(ls1)
        else:
            raise(Exception('keepout type'))
            
        return toolclearance


"""Reference checks must detect invalid labels and unsupported optimality claims."""
import copy
import unittest
import networkx as nx
from scripts.audit_general_pilot import check_observation, check_pairs, reference_bounds


class PilotAuditTests(unittest.TestCase):
    def fixture(self):
        graph=nx.path_graph(4)
        row=dict(Graph='tree_4_seed0__h1_k1__r0__cadical',Instance='tree_4_seed0',Family='tree',
                 h='1',k='1',Method='cadical',Repeat='0',V='4',E='3',Delta='2',Diameter='3',
                 Status='OPT',Span='2',LB='2',Wall_Time='0.1',Limit='30',Termination='RETURNED')
        record=dict(Graph=row['Graph'],configuration=dict(vertices=list(graph),edges=list(graph.edges()),h=1,k=1,method='cadical'),
                    result=dict(h=1,k=1,status='OPT',span=2,proven_lower_bound=2,
                                labels=[['0',0],['1',1],['2',2],['3',0]],wall_time=.1,termination='RETURNED'))
        return graph,row,record

    def test_exact_tree_reference_and_invalid_witness(self):
        graph,row,record=self.fixture()
        result=check_observation(row,record,graph,'tree',{'timeout':30})
        self.assertTrue(result['Theory_Optimal'])
        record['result']['labels'][1][1]=0
        with self.assertRaisesRegex(ValueError,'invalid witness'):
            check_observation(row,record,graph,'tree',{'timeout':30})

    def test_valid_but_nonoptimal_labeling_is_not_optimum(self):
        graph,row,record=self.fixture()
        row.update(Span='3',LB='3')
        record['result'].update(span=3,proven_lower_bound=3,labels=[['0',0],['1',1],['2',2],['3',3]])
        with self.assertRaisesRegex(ValueError,'contradicts theory'):
            check_observation(row,record,graph,'tree',{'timeout':30})
        row.update(Status='FEASIBLE',LB='2')
        record['result'].update(status='FEASIBLE',proven_lower_bound=2)
        result=check_observation(row,record,graph,'tree',{'timeout':30})
        self.assertEqual(result['Reference_Check'],'ABOVE_EXACT')
        self.assertFalse(result['Theory_Optimal'])

    def test_bound_certificate_keeps_recorded_status(self):
        graph,row,record=self.fixture()
        row.update(Status='FEASIBLE',LB='1')
        record['result'].update(status='FEASIBLE',proven_lower_bound=1)
        result=check_observation(row,record,graph,'tree',{'timeout':30})
        self.assertTrue(result['Theory_Optimal'])
        self.assertEqual(result['Status'],'FEASIBLE')

    def test_reference_domains_and_cross_solver_conflict(self):
        self.assertIsNone(reference_bounds('P_3xP_5',nx.grid_2d_graph(3,5),2,1)['Exact_Reference'])
        self.assertEqual(reference_bounds('P_4xP_5',nx.grid_2d_graph(4,5),2,1)['Exact_Reference'],6)
        self.assertIsNone(reference_bounds('tree',nx.path_graph(4),3,2)['Exact_Reference'])
        graph,row,record=self.fixture()
        first=check_observation(row,record,graph,'tree',{'timeout':30})
        other=copy.deepcopy(first);other.update(Method='gurobi',Span=3,Recorded_LB=3)
        with self.assertRaisesRegex(ValueError,'inconsistent solver optima'):
            check_pairs([first,other])


if __name__=='__main__':
    unittest.main()

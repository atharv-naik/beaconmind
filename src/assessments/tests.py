from django.test import TestCase
from .definitions import PHQ9Phase, GAD7Phase, ASQPhase, MonitoringPhase, PhaseMap
from . import definitions
import random

class AssessmentDefinitionsTests(TestCase):
    def setUp(self):
        self.phq9 = PHQ9Phase()
        self.gad7 = GAD7Phase()
        self.asq = ASQPhase()
        self.monitoring = MonitoringPhase()
        self.phases = PhaseMap()
    
    def test_phase_map(self):
        self.assertEqual(self.phases.get("assessment.phq9"), self.phq9)
        self.assertEqual(self.phases.get("assessment.gad7"), self.gad7)
        self.assertEqual(self.phases.get("assessment.asq"), self.asq)
        self.assertEqual(self.phases.get("monitoring"), self.monitoring)
        self.assertIsNone(self.phases.get("UnknownPhase"))
    
class AssessmentPhaseRoutingTestCase(TestCase):
    def setUp(self):
        """Initialize all assessment phases."""
        self.phases = PhaseMap()._mapper

    def test_questions_structure(self):
        """Ensure each assessment phase has a valid questions dictionary."""
        for name, phase in self.phases.items():
            with self.subTest(phase=name):
                questions_dict = phase.get_questions_dict()
                self.assertIsInstance(questions_dict, dict)
                self.assertIn(phase.base_node_id, questions_dict)

    def test_question_routing_till_end(self):
        for name, phase in self.phases.items():
            with self.subTest(phase=name):
                for _ in range(100):
                    q_node = phase.get(phase.base_node_id)
                    r = 0
                    visited_nodes = set()

                    while q_node != definitions.END:
                        self.assertNotIn(q_node.node_id, visited_nodes, "Circular loop detected.")
                        
                        tr = random.choice(["y", "n", "o", "c"])

                        if tr in ('y', 'n'):
                            prev_node = q_node
                            q_node = phase.next_q(q_node.node_id, tr, r=r)
                            self.assertNotEqual(prev_node, q_node, f"Self loop for {tr} detected.")
                            r = 0
                            visited_nodes.add(prev_node.node_id)
                        elif tr == 'o':
                            prev_node = q_node
                            q_node = phase.next_q(q_node.node_id, tr, r=r)

                            if r > prev_node.r:
                                self.assertNotEqual(prev_node, q_node, "Response 'o' must transition to a new question.")

                            if q_node == prev_node:
                                r += 1
                            else:
                                r = 0
                                visited_nodes.add(prev_node.node_id)
                        elif tr == 'c':
                            prev_node = q_node
                            q_node = phase.next_q(q_node.node_id, tr, r=r)
                            self.assertEqual(prev_node, q_node, "Self loop for 'c' detected.")
                            r = 0

                    self.assertEqual(q_node, definitions.END)

    def test_o_response_exceeding_r(self):
        for name, phase in self.phases.items():
            with self.subTest(phase=name):
                start_node = phase.get(phase.base_node_id)
                q_node = start_node
                r = 0

                for _ in range(start_node.r + 2):
                    q_node = phase.next_q(q_node.node_id, "o", r=r)
                    r += 1

                self.assertNotEqual(q_node, start_node, "Response 'o' exceeding r must transition to a new question.")
    
    def test_c_response_infinitely_repeats(self):
        for name, phase in self.phases.items():
            with self.subTest(phase=name):
                start_node = phase.get(phase.base_node_id)
                q_node = start_node
                r = 0

                for _ in range(10):
                    q_node = phase.next_q(q_node.node_id, "c", r=r)
                    r += 1
                
                self.assertEqual(q_node, start_node, "Response 'c' must result in inf self loop.")

    def test_invalid_transitions(self):
        for name, phase in self.phases.items():
            with self.subTest(phase=name):
                with self.assertRaises(ValueError):
                    phase.next_q("invalid_node_id", "y", r=0)

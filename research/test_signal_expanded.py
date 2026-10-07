import unittest
from research.signal_broker_expanded import broker_view, session_quality
from research.signal_broker_phase2 import FIELDS, broker_history
from research.signal_expanded_contract import ExpandedInvestigation

class ExpansionNullTests(unittest.TestCase):
    def test_null_retains_broker_without_zero_or_flat(self):
        row={'symbol':'BMRI','date':'2026-07-29','broker_code':'AA',**{f:None for f in (*FIELDS,'nval','nlot')}}
        rows,summary=broker_view([row],{})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['net_role'],'UNKNOWN')
        self.assertIsNone(rows[0]['nval'])
        self.assertEqual(rows[0]['net_flat_sessions'],0)
        self.assertIsNone(summary['totals']['bval'])
        self.assertEqual(session_quality([row],{'volume':100})['status'],'BROKER_FIELDS_INCOMPLETE')
        history=broker_history('AA',['2026-07-29'],{'2026-07-29':[row]},{'2026-07-29':session_quality([row],{'volume':100})})
        self.assertEqual(history['reconciled_observed_sessions'],0)
        self.assertIsNone(history['series'][0]['nval'])
    def test_known_invalid_number_still_rejected(self):
        row={'symbol':'BMRI','date':'2026-07-29','broker_code':'AA',**{f:None for f in (*FIELDS,'nval','nlot')}}
        row['bval']=-1
        with self.assertRaises(ValueError):broker_view([row],{})

    def test_unknown_list_cannot_be_inactive_or_zero(self):
        from research.signal_expanded_contract import ExpandedListItem
        base={'symbol':'AMMN','state':'UNKNOWN','active':None,'persistence_hits':None,'last_updated':'2026-09-30'}
        ExpandedListItem.model_validate(base)
        for change in ({'active':False},{'persistence_hits':0}):
            with self.assertRaises(ValueError):ExpandedListItem.model_validate({**base,**change})

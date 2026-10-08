import unittest
from research.signal_context_enrichment import compact, events_from

class ContextEnrichmentTests(unittest.TestCase):
    def test_missing_metrics_are_not_zero(self):
        self.assertEqual(compact(None),'—')
        self.assertEqual(compact(float('nan')),'—')
        self.assertEqual(compact(0),'Rp 0,00')

    def test_event_dates_use_event_not_payment_date(self):
        actions={'dividend':[{'ex_date':'2026-03-31','payment_date':'2026-04-10','dividend_amount':50},{'ex_date':'2026-09-30','payment_date':'2026-10-08','dividend_amount':100}], 'agm':[{'agm_date':'2026-04-01','agm_place':'Jakarta'}], 'bonus':None}
        rows=events_from(actions)
        self.assertEqual([r['date'] for r in rows],['2026-09-30','2026-04-01'])
        self.assertIn('2026-10-08',rows[0]['detail'])

    def test_repeated_dividend_feeds_do_not_duplicate_event(self):
        row={'ex_date':'2026-07-01','payment_date':'2026-07-15','dividend_amount':0}
        rows=events_from({'dividend':[row], 'upcoming_dividend':[row]})
        self.assertEqual(len(rows),1)
        self.assertIn('Rp 0,00',rows[0]['detail'])

if __name__=='__main__':unittest.main()

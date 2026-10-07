import unittest
import pandas as pd
from research.signal_json_valid_baseline import select_history
from research.signal_detector_valid_baseline import evaluate_day
from research.signal_detector_v0_2 import evaluate_day as frozen

class ValidBaselineTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame([{'date':pd.Timestamp('2026-01-01')+pd.Timedelta(days=i),'close':100+i/10,'high':102+i/10,'low':98+i/10,'volume':1000+i,'turnover_idr':100000+i*100,'transaction_count':100+i,'avg_trade_value_idr':1000+i,'top5_net_buy_share':.1,'net_foreign_inflow':0,'foreign_share':.2} for i in range(45)])
    def test_complete_history_matches_frozen_detector(self):
        frame=self.frame()
        self.assertEqual(frozen(frame,35),evaluate_day(frame,35,frame.iloc[15:35]))
    def test_uses_only_preceding_valid_observations(self):
        frame=self.frame();frame.loc[25,'turnover_idr']=None
        selected=select_history(frame,35,['turnover_idr'],30)
        self.assertEqual(len(selected),20)
        self.assertNotIn(25,selected.index)
        self.assertEqual(selected.index.max(),34)
        self.assertEqual(selected.index.min(),14)
        frame.loc[35:,'turnover_idr']=999999999
        self.assertEqual(selected.to_dict('records'),select_history(frame,35,['turnover_idr'],30).to_dict('records'))
    def test_does_not_borrow_observations_older_than_cap(self):
        frame=self.frame();frame.loc[10:29,'turnover_idr']=None
        self.assertLess(len(select_history(frame,35,['turnover_idr'],25)),20)
        with self.assertRaises(ValueError):select_history(frame,35,['turnover_idr'],19)

    def test_missing_activity_does_not_compress_price_or_volume_calendar(self):
        frame=self.frame();frame.loc[25,'turnover_idr']=None;frame.loc[25,'volume']=99999
        history=select_history(frame,35,['turnover_idr','volume','transaction_count','avg_trade_value_idr','top5_net_buy_share'],25)
        value=evaluate_day(frame,35,history)
        self.assertEqual(value['relative_volume'],round(frame.iloc[35]['volume']/frame.iloc[15:35]['volume'].median(),4))
        from research.signal_detector_v0_2 import compression_score
        price=compression_score(frame,35)
        self.assertEqual(value['current_5d_range_pct'],round(price['current_5d_range_pct'],4))
        self.assertEqual(value['baseline_5d_range_pct'],round(price['baseline_5d_range_pct'],4))

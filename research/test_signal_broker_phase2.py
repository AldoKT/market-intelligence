import unittest
from research.signal_broker_phase2 import broker_view, broker_history, session_quality


def row(code,day,bval,sval,blot=1,slot=1):
    return {'symbol':'ANTM','date':day,'broker_code':code,'bval':bval,'sval':sval,'blot':blot,'slot':slot,
            'bfreq':1,'sfreq':1,'nval':bval-sval,'nlot':blot-slot}


class BrokerTests(unittest.TestCase):
    def test_full_table_retains_net_flat_and_unknown_registry(self):
        rows=[row('XX','2026-10-01',100,100)]+[row(str(i),'2026-10-01',10*i,0) for i in range(1,8)]
        brokers,summary=broker_view(rows,{})
        self.assertEqual(len(brokers),8)
        flat=next(r for r in brokers if r['broker_code']=='XX')
        self.assertEqual(flat['net_role'],'NET_FLAT')
        self.assertEqual(flat['registry_status'],'UNLISTED_CODE')
        self.assertEqual(len(summary['top5_gross_buy_codes']),5)
        self.assertAlmostEqual(sum(r['buy_value_share_pct'] for r in brokers),100)

    def test_aggregate_price_weighted_by_lots_and_never_average_daily_price(self):
        rows=[row('AA','2026-10-01',1000,0,1,0),row('AA','2026-10-02',9000,0,3,0)]
        brokers,_=broker_view(rows,{})
        self.assertEqual(brokers[0]['weighted_buy_price_per_share'],25)
        self.assertIsNone(brokers[0]['weighted_sell_price_per_share'])
        self.assertEqual(brokers[0]['observed_sessions'],2)

    def test_absence_and_bad_scope_break_directional_continuity(self):
        dates=['2026-10-01','2026-10-02','2026-10-05','2026-10-06']
        sessions={dates[0]:[row('AA',dates[0],200,100)],dates[1]:[row('BB',dates[1],200,100)],
                  dates[2]:[row('AA',dates[2],100,200)],dates[3]:[row('AA',dates[3],200,100)]}
        quality={d:{'status':'RECONCILED_RESEARCH_CANDIDATE'} for d in dates}
        quality[dates[3]]['status']='VOLUME_SCOPE_MISMATCH'
        history=broker_history('AA',dates,sessions,quality)
        self.assertEqual(history['adjacent_net_buy_sell_switches'],0)
        self.assertEqual(history['series'][1]['observation'],'NOT_RETURNED')
        self.assertIsNone(history['series'][1]['bval'])
        self.assertEqual(history['max_consecutive_reconciled_net_buy_sessions'],1)
        self.assertEqual(history['reconciled_observed_sessions'],2)

    def test_observed_directional_switch_count(self):
        dates=['2026-10-01','2026-10-02']
        sessions={dates[0]:[row('AA',dates[0],200,100)],dates[1]:[row('AA',dates[1],100,200)]}
        history=broker_history('AA',dates,sessions,{d:{'status':'RECONCILED_RESEARCH_CANDIDATE'} for d in dates})
        self.assertEqual(history['adjacent_net_buy_sell_switches'],1)

    def test_duplicates_and_bad_net_rejected(self):
        a=row('AA','2026-10-01',100,50)
        with self.assertRaises(ValueError):broker_view([a,a],{})
        a['nval']=0
        with self.assertRaises(ValueError):broker_view([a],{})

    def test_missing_and_volume_mismatch_preserve_quality(self):
        self.assertEqual(session_quality([],{'volume':100})['status'],'BROKER_DATA_MISSING')
        rows=[row('AA','2026-10-01',100,100)]
        quality=session_quality(rows,{'volume':200})
        self.assertEqual(quality['status'],'VOLUME_SCOPE_MISMATCH')
        self.assertFalse(quality['scope_verified'])


if __name__=='__main__':unittest.main()

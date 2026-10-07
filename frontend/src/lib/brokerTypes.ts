export interface BrokerRow {
  broker_code:string; broker_name:string|null; registry_status:string;
  broker_company_origin:string; cohort:string|null;
  bval:number|null;sval:number|null;nval:number|null;blot:number|null;slot:number|null;nlot:number|null;bfreq:number|null;sfreq:number|null;
  gross_value_idr:number|null;net_role:string;weighted_buy_price_per_share:number|null;weighted_sell_price_per_share:number|null;
  buy_value_share_pct:number|null;sell_value_share_pct:number|null;observed_sessions:number;
  net_buy_sessions:number;net_sell_sessions:number;net_flat_sessions:number;
}
export interface BrokerQuality {status:string;scope_verified:boolean;broker_volume_shares:number|null;daily_volume_shares:number;buy_sell_balanced:boolean|null;}
export interface BrokerSummary {
  returned_broker_count:number;totals:Record<string,number|null>;top5_gross_buy_codes:string[];top5_gross_sell_codes:string[];
  top5_net_buy_codes:string[];top5_net_sell_codes:string[];top5_gross_buy_share_pct:number|null;top5_gross_sell_share_pct:number|null;
}
export interface BrokerHistoryPoint {
  date:string;observation:string;session_quality?:string;net_role:string|null;
  bval:number|null;sval:number|null;nval:number|null;blot:number|null;slot:number|null;nlot:number|null;bfreq:number|null;sfreq:number|null;
}
export interface BrokerHistory {
  broker_code:string;series:BrokerHistoryPoint[];max_consecutive_reconciled_net_buy_sessions?:number;
  max_consecutive_reconciled_net_sell_sessions?:number;adjacent_net_buy_sell_switches?:number;
}
export interface BrokerEpisodeRef {
  investigation_id:string;symbol:string;start:string;last_observed_date:string;last_state:string;observed_sessions:number;end_status:string;
}
export interface BrokerIndex {
  symbol:string;as_of:string;signal_snapshot:string;default_date:string|null;dates:string[];episodes:BrokerEpisodeRef[];
}
export interface BrokerPayload {
  symbol:string;date?:string;start?:string;last_observed_date?:string;investigation_id?:string;last_state?:string;
  brokers:BrokerRow[];summary:BrokerSummary;quality?:BrokerQuality;quality_by_session?:Record<string,BrokerQuality>;
  signal_context?:{spot_hit:boolean|null;lifecycle_state_v2:string|null;evaluation_status:string};broker_histories?:BrokerHistory[];
}

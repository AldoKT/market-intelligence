const COMPANY_NAMES: Record<string,string> = {
  ADRO: "PT Alamtri Resources Indonesia Tbk.",
  AMMN: "PT Amman Mineral Internasional Tbk.",
  ANTM: "PT Aneka Tambang Tbk.",
  ASII: "PT Astra International Tbk.",
  BBCA: "PT Bank Central Asia Tbk.",
  BBNI: "PT Bank Negara Indonesia (Persero) Tbk.",
  BBRI: "PT Bank Rakyat Indonesia (Persero) Tbk.",
  BMRI: "PT Bank Mandiri (Persero) Tbk.",
  BRMS: "PT Bumi Resources Minerals Tbk.",
  BSDE: "PT Bumi Serpong Damai Tbk.",
  CPIN: "PT Charoen Pokphand Indonesia Tbk.",
  CTRA: "PT Ciputra Development Tbk.",
  EMTK: "PT Elang Mahkota Teknologi Tbk.",
  GOTO: "PT GoTo Gojek Tokopedia Tbk.",
  ICBP: "PT Indofood CBP Sukses Makmur Tbk.",
  INCO: "PT Vale Indonesia Tbk.",
  INDF: "PT Indofood Sukses Makmur Tbk.",
  ISAT: "PT Indosat Tbk.",
  KLBF: "PT Kalbe Farma Tbk.",
  MDKA: "PT Merdeka Copper Gold Tbk.",
  MIKA: "PT Mitra Keluarga Karyasehat Tbk.",
  MYOR: "PT Mayora Indah Tbk.",
  NCKL: "PT Trimegah Bangun Persada Tbk.",
  PGAS: "PT Perusahaan Gas Negara Tbk.",
  PTBA: "PT Bukit Asam Tbk.",
  TINS: "PT Timah Tbk.",
  TLKM: "PT Telkom Indonesia (Persero) Tbk.",
  UNTR: "PT United Tractors Tbk."
};

export function companyName(symbol:string, supplied?:string|null){
  return supplied || COMPANY_NAMES[symbol.toUpperCase()] || symbol.toUpperCase();
}

export function humanGroup(value?:string|null){
  if(!value) return "Unmapped";
  return value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
}

// Mirrors scripts/prepare_data.py :: OBLAST_TO_ETHNO.
// Used to group oblast-keyed singers into the ethno regions the map
// displays. Keep in sync with the Python side.
export const OBLAST_TO_ETHNO: Record<string, string> = {
  Zhytomyr: "Polissia",
  Chernihiv: "Polissia",
  Rivne: "Polissia",
  Volyn: "Volyn",
  Lviv: "Halychyna",
  "Ivano-Frankivsk": "Halychyna",
  Ternopil: "Halychyna",
  Vinnytska: "Podillia",
  Khmelnytskyi: "Podillia",
  "Podillia (historical)": "Podillia",
  Kyiv: "Naddniprianshchyna",
  Poltava: "Naddniprianshchyna",
  Cherkasy: "Naddniprianshchyna",
  Dnipropetrovsk: "Naddniprianshchyna",
  Kirovohrad: "Naddniprianshchyna",
  Kharkiv: "Slobozhanshchyna",
  Sumy: "Slobozhanshchyna",
  Luhansk: "Slobozhanshchyna",
  Mykolaiv: "Pivden",
  Kherson: "Pivden",
  Crimea: "Pivden",
  Odesa: "Pivden",
  Zaporizhzhia: "Pivden",
  Donetsk: "Pivden",
  Sevastopol: "Pivden",
};

export function ethnoForOblast(oblast: string | null | undefined): string | null {
  if (!oblast) return null;
  return OBLAST_TO_ETHNO[oblast] ?? null;
}

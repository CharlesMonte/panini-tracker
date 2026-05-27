export type Person = {
  id: number;
  name: string;
  display_order: number;
  active: boolean;
};

export type Sticker = {
  sticker_id?: number;
  id?: number;
  album_order?: number;
  display_code: string;
  sticker_code: string;
  category_code?: string;
  category_name?: string;
  player_name?: string;
  team_name?: string;
  label?: string;
  is_foil?: boolean;
  is_team_photo?: boolean;
  is_emblem?: boolean;
  quantity?: number;
  duplicate_count?: number;
};

export type PersonStats = {
  person_id: number;
  person_name: string;
  owned_distinct: number;
  total_copies: number;
  duplicates: number;
  duplicate_rate: number;
  missing: number;
  total_stickers: number;
  completion: number;
};

export type ActionRow = {
  id: number;
  date: string;
  action: string;
  action_label: string;
  personne?: string;
  sticker?: string;
  nom?: string;
  avant?: number;
  après?: number;
  delta?: number;
  batch_id?: string;
  annulable: boolean;
};

export type TradeableSticker = Sticker & {
  sticker_id: number;
  label: string;
  giver_quantity: number;
};

export type SaleCandidate = TradeableSticker & {
  seller_id: number;
  seller: string;
  buyer_id: number;
  buyer: string;
  seller_quantity: number;
  seller_keeps_after_sale: number;
  price: number;
};

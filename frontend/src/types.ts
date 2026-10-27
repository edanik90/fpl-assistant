export type Position = "GK" | "DEF" | "MID" | "FWD";
export type Player = {
  id: number;
  source_player_id: string;
  name: string;
  short_name: string;
  club: string;
  club_code: string;
  color: string;
  position: Position;
  price_tenths: number;
};
export type Pick = {
  slot: number;
  player_id: number;
  is_captain: boolean;
  is_vice_captain: boolean;
  purchase_price_tenths: number;
  selling_price_tenths: number;
};
export type Fixture = {
  id: number;
  gameweek: number;
  home_club: string;
  home_code: string;
  away_club: string;
  away_code: string;
};
export type Workspace = { name: string; notes: string; updated_at: string };
export type Overview = {
  snapshot: {
    id: number;
    source: string;
    season: string;
    gameweek: number;
    created_at: string;
    bank_tenths: number;
    free_transfers: number;
  };
  workspace: Workspace;
  players: Player[];
  picks: Pick[];
  fixtures: Fixture[];
};

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
  purchase_price_tenths: number | null;
  selling_price_tenths: number | null;
};
export type Fixture = {
  id: number;
  gameweek: number | null;
  source_fixture_id: number | null;
  kickoff_time: string | null;
  home_club: string;
  home_code: string;
  away_club: string;
  away_code: string;
};
export type Workspace = { name: string; notes: string; updated_at: string };
export type Snapshot = {
  id: number;
  source: string;
  season: string;
  gameweek: number;
  created_at: string;
  label: string | null;
  captured_at: string | null;
  kind: string | null;
  bank_tenths: number | null;
  free_transfers: number | null;
};
export type CorrectionValues = {
  bank_tenths: number | null;
  free_transfers: number | null;
  transfer_hits: number | null;
  chip: string | null;
  picks: Pick[];
};
export type Overview = {
  snapshot: Snapshot;
  workspace: Workspace;
  players: Player[];
  picks: Pick[];
  fixtures: Fixture[];
  correction_revision: number;
  correction_reason: string | null;
  transfer_hits: number | null;
  chip: string | null;
  history_count: number;
};

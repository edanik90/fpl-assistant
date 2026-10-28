import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleHelp,
  Database,
  LayoutGrid,
  List,
  LoaderCircle,
  NotebookPen,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  Wallet,
  X,
} from "lucide-react";
import type {
  Fixture,
  Overview,
  Pick,
  Player,
  Position,
  Workspace,
} from "./types";
import "./styles.css";

const positions: Position[] = ["GK", "DEF", "MID", "FWD"];
const money = (value: number) => `£${(value / 10).toFixed(1)}m`;
const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok)
    throw new Error(
      response.status === 422
        ? "Check the workspace name and notes, then try again."
        : "The app could not complete this request. Check that it is running and try again.",
    );
  return response.json() as Promise<T>;
}

function opponent(player: Player, fixtures: Fixture[]) {
  const fixture = fixtures.find(
    (f) => f.home_code === player.club_code || f.away_code === player.club_code,
  );
  return fixture
    ? fixture.home_code === player.club_code
      ? `${fixture.away_code} (H)`
      : `${fixture.home_code} (A)`
    : "No fixture";
}

function Shirt({ color, small = false }: { color: string; small?: boolean }) {
  return (
    <svg
      className={small ? "shirt small" : "shirt"}
      viewBox="0 0 64 64"
      aria-hidden="true"
    >
      <path
        d="M19 7 9 12 2 27l12 6 5-8v34h26V25l5 8 12-6-7-15-10-5-6 5H25Z"
        fill={color}
        stroke="rgba(0,0,0,.12)"
        strokeWidth="2"
      />
      <path
        d="m24 8 8 8 8-8M19 25v34M45 25v34"
        fill="none"
        stroke="rgba(255,255,255,.4)"
        strokeWidth="2"
      />
      <path d="M29 29h6v10h-6z" fill="rgba(255,255,255,.85)" />
    </svg>
  );
}

function PlayerDetail({
  player,
  pick,
  fixtures,
  close,
}: {
  player: Player;
  pick?: Pick;
  fixtures: Fixture[];
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="player-dialog"
      onCancel={close}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
      aria-labelledby="player-title"
    >
      <button
        className="icon-button modal-close"
        onClick={close}
        aria-label="Close player details"
      >
        <X size={20} />
      </button>
      <div className="detail-shirt">
        <Shirt color={player.color} />
      </div>
      <span className="eyebrow">
        {player.club} · {player.position}
      </span>
      <h2 id="player-title">{player.name}</h2>
      <p className="muted">Fictional player · demonstration data</p>
      <dl className="detail-stats">
        <div>
          <dt>Current price</dt>
          <dd>{money(player.price_tenths)}</dd>
        </div>
        <div>
          <dt>Example fixture</dt>
          <dd>{opponent(player, fixtures)}</dd>
        </div>
        {pick && (
          <>
            <div>
              <dt>Purchase price</dt>
              <dd>{money(pick.purchase_price_tenths)}</dd>
            </div>
            <div>
              <dt>Selling price</dt>
              <dd>{money(pick.selling_price_tenths)}</dd>
            </div>
          </>
        )}
      </dl>
      <p className="info-note">
        {pick ? "This player is in your demo squad. " : ""}Transfer editing and
        expected points will be added in later milestones.
      </p>
      <button className="button primary full" onClick={close}>
        Back to workspace
      </button>
    </dialog>
  );
}

function App() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const [page, setPage] = useState<"squad" | "players" | "workspace">("squad");
  const [view, setView] = useState<"pitch" | "list">("pitch");
  const [selected, setSelected] = useState<Player | null>(null);
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState<Position | "ALL">("ALL");
  const [sort, setSort] = useState("name");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");
  const dirty =
    !!data && (name !== data.workspace.name || notes !== data.workspace.notes);

  async function load() {
    setError("");
    try {
      const result = await request<Overview>("/api/overview");
      setData(result);
      setName(result.workspace.name);
      setNotes(result.workspace.notes);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Unable to load the workspace.",
      );
    }
  }
  useEffect(() => {
    void load();
  }, []);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setSaveMessage("");
    setSaveError("");
    try {
      const workspace = await request<Workspace>("/api/workspace", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, notes }),
      });
      setData((current) => current && { ...current, workspace });
      setName(workspace.name);
      setNotes(workspace.notes);
      setSaveMessage("Saved to your workspace.");
    } catch (e) {
      setSaveError(
        e instanceof Error
          ? e.message
          : "Unable to save. Your edits are still here.",
      );
    } finally {
      setSaving(false);
    }
  }

  const notesForm = (expanded = false) => (
    <form onSubmit={save} className="notes-form">
      {expanded && (
        <>
          <label htmlFor="workspace-name">Workspace name</label>
          <input
            id="workspace-name"
            value={name}
            maxLength={60}
            required
            disabled={saving}
            onChange={(e) => {
              setName(e.target.value);
              setSaveMessage("");
            }}
          />
        </>
      )}
      <label htmlFor="planning-notes">
        {expanded ? "Planning notes" : "A little space for your next move."}
      </label>
      <textarea
        id="planning-notes"
        value={notes}
        maxLength={5000}
        disabled={saving}
        rows={expanded ? 7 : 3}
        placeholder="Watchlist, captain ideas, things to check…"
        onChange={(e) => {
          setNotes(e.target.value);
          setSaveMessage("");
        }}
      />
      <div className="save-row">
        <span className="muted">
          {dirty ? "Unsaved changes" : "Stored locally"}
        </span>
        <button
          type="submit"
          className="button primary compact"
          disabled={saving || !dirty || !name.trim()}
        >
          {saving ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <Check size={15} />
          )}
          {saving ? "Saving…" : expanded ? "Save workspace" : "Save notes"}
        </button>
      </div>
      <div
        aria-live="polite"
        className={saveError ? "save-status error-text" : "save-status"}
      >
        {saveError || saveMessage}
      </div>
    </form>
  );

  function playerTable(players: Player[]) {
    return (
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Player</th>
              <th>Position</th>
              <th>Price</th>
              <th>Fixture</th>
              <th>Squad</th>
            </tr>
          </thead>
          <tbody>
            {players.map((player) => {
              const pick = data?.picks.find((p) => p.player_id === player.id);
              return (
                <tr key={player.id}>
                  <td>
                    <button
                      className="table-player"
                      onClick={() => setSelected(player)}
                    >
                      <Shirt color={player.color} small />
                      <span>
                        <strong>{player.name}</strong>
                        <small>{player.club}</small>
                      </span>
                    </button>
                  </td>
                  <td>
                    <span className="position-label">{player.position}</span>
                  </td>
                  <td className="numeric">{money(player.price_tenths)}</td>
                  <td>{opponent(player, data?.fixtures ?? [])}</td>
                  <td>
                    {pick ? (
                      <span className="squad-tag">
                        {pick.slot <= 11 ? "Starting XI" : "Bench"}
                        {pick.is_captain
                          ? " · C"
                          : pick.is_vice_captain
                            ? " · V"
                            : ""}
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {players.length === 0 && (
          <div className="empty-state">
            <Search size={26} />
            <h3>No matching players</h3>
            <p>Try another name, club, or position.</p>
            <button
              className="button secondary"
              onClick={() => {
                setSearch("");
                setPosition("ALL");
              }}
            >
              Clear filters
            </button>
          </div>
        )}
      </div>
    );
  }

  const picks =
    data?.picks.map((pick) => ({
      ...pick,
      player: data.players.find((p) => p.id === pick.player_id)!,
    })) ?? [];
  const starters = picks.filter((p) => p.slot <= 11);
  const formation = positions
    .slice(1)
    .map((p) => starters.filter((pick) => pick.player.position === p).length)
    .join("–");
  const filteredPlayers = (data?.players ?? [])
    .filter(
      (p) =>
        (position === "ALL" || p.position === position) &&
        `${p.name} ${p.club}`
          .toLowerCase()
          .includes(search.trim().toLowerCase()),
    )
    .sort((a, b) =>
      sort === "price"
        ? b.price_tenths - a.price_tenths || a.name.localeCompare(b.name)
        : a.name.localeCompare(b.name),
    );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("squad");
          }}
          aria-label="FPL Assistant home"
        >
          <span className="brand-mark">
            f<span>pl</span>
            <i />
          </span>
          <span>
            FPL <b>Assistant</b>
          </span>
        </a>
        <div className="sidebar-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            onClick={() => setPage("squad")}
            aria-current={page === "squad" ? "page" : undefined}
          >
            <LayoutGrid size={19} />
            My squad
            <ChevronRight className="nav-chevron" size={15} />
          </button>
          <button
            onClick={() => setPage("players")}
            aria-current={page === "players" ? "page" : undefined}
          >
            <Users size={19} />
            Player library
          </button>
          <button
            onClick={() => setPage("workspace")}
            aria-current={page === "workspace" ? "page" : undefined}
          >
            <Settings2 size={19} />
            Workspace
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="private-note">
            <ShieldCheck size={22} />
            <strong>Your team. Your space.</strong>
            <p>A private place to think through your next gameweek.</p>
          </div>
          <div className="local-status">
            <span className="status-dot" />
            Local workspace <span className="version">v0.1</span>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <span>{data?.workspace.name ?? "FPL Assistant"}</span>
          </div>
          <span className="demo-badge">
            <span />
            DEMO DATA
          </span>
        </header>
        <main>
          {!data ? (
            <div className="loading-card" role="status">
              {error ? (
                <>
                  <CircleHelp size={32} />
                  <h1>Let’s reconnect.</h1>
                  <p>{error}</p>
                  <button
                    className="button primary"
                    onClick={() => void load()}
                  >
                    Try again
                  </button>
                </>
              ) : (
                <>
                  <LoaderCircle className="spin" size={28} />
                  <p>Opening your workspace…</p>
                </>
              )}
            </div>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    SEASON {data.snapshot.season}{" "}
                    <span className="eyebrow-dot">·</span> DEMONSTRATION
                  </div>
                  <h1>
                    {page === "squad"
                      ? "A clearer view of your squad."
                      : page === "players"
                        ? "Find your next possibility."
                        : "Make this space yours."}
                  </h1>
                  <p>
                    {page === "squad"
                      ? "Your starting XI, your bench, and a little room to plan ahead."
                      : page === "players"
                        ? "Explore the fictional player catalogue and inspect individual prices."
                        : "Keep your planning notes close and see where your data lives."}
                  </p>
                </div>
                {page === "squad" && (
                  <button
                    className="button secondary"
                    onClick={() => setPage("players")}
                  >
                    Browse players
                    <ArrowUpRight size={16} />
                  </button>
                )}
              </div>
              <div className="demo-notice">
                <Database size={16} />
                <span>
                  You’re exploring a sample squad. All players, clubs, and
                  fixtures are fictional.
                </span>
                <span className="notice-end">No FPL account connected</span>
              </div>

              {page === "squad" && (
                <>
                  <section
                    className="stats-grid"
                    aria-label="Demo squad summary"
                  >
                    <div className="stat">
                      <span>
                        Squad value <Users size={16} />
                      </span>
                      <strong>
                        {money(
                          picks.reduce(
                            (sum, p) => sum + p.player.price_tenths,
                            0,
                          ),
                        )}
                      </strong>
                      <small>Current demo player prices</small>
                    </div>
                    <div className="stat">
                      <span>
                        In the bank <Wallet size={16} />
                      </span>
                      <strong>{money(data.snapshot.bank_tenths)}</strong>
                      <small>Sample available balance</small>
                    </div>
                    <div className="stat">
                      <span>
                        Free transfers <ArrowRight size={16} />
                      </span>
                      <strong>
                        {data.snapshot.free_transfers}
                        <em>available</em>
                      </strong>
                      <small>Transfer editing coming next</small>
                    </div>
                    <div className="stat">
                      <span>
                        Formation <LayoutGrid size={16} />
                      </span>
                      <strong>{formation}</strong>
                      <small>11 starters · 4 substitutes</small>
                    </div>
                  </section>
                  <div className="dashboard-grid">
                    <section className="card squad-card">
                      <div className="card-header">
                        <div>
                          <h2>Your demo squad</h2>
                          <p>
                            Gameweek {data.snapshot.gameweek} <span>·</span>{" "}
                            Select a player to explore
                          </p>
                        </div>
                        <div className="view-switch" aria-label="Squad display">
                          <button
                            aria-label="Pitch view"
                            aria-pressed={view === "pitch"}
                            onClick={() => setView("pitch")}
                          >
                            <LayoutGrid size={16} />
                          </button>
                          <button
                            aria-label="List view"
                            aria-pressed={view === "list"}
                            onClick={() => setView("list")}
                          >
                            <List size={17} />
                          </button>
                        </div>
                      </div>
                      {view === "pitch" ? (
                        <>
                          <div className="pitch">
                            <div className="pitch-lines" aria-hidden="true">
                              <div className="goal-area top" />
                              <div className="center-line" />
                              <div className="center-circle" />
                              <div className="goal-area bottom" />
                            </div>
                            <div className="pitch-label">
                              STARTING XI <span>{formation}</span>
                            </div>
                            {positions.map((pos) => (
                              <div className="pitch-row" key={pos}>
                                {starters
                                  .filter((p) => p.player.position === pos)
                                  .map((p) => (
                                    <button
                                      className="pitch-player"
                                      key={p.player_id}
                                      onClick={() => setSelected(p.player)}
                                      aria-label={`View ${p.player.name}${p.is_captain ? ", captain" : p.is_vice_captain ? ", vice-captain" : ""}`}
                                    >
                                      <div className="kit-wrap">
                                        <Shirt color={p.player.color} />
                                        {(p.is_captain ||
                                          p.is_vice_captain) && (
                                          <span
                                            className={`captain ${p.is_vice_captain ? "vice" : ""}`}
                                          >
                                            {p.is_captain ? "C" : "V"}
                                          </span>
                                        )}
                                      </div>
                                      <strong>{p.player.short_name}</strong>
                                      <small>
                                        {opponent(p.player, data.fixtures)}
                                      </small>
                                    </button>
                                  ))}
                              </div>
                            ))}
                          </div>
                          <div className="bench">
                            <div className="bench-heading">
                              <span>THE BENCH</span>
                              <span>In substitute order</span>
                            </div>
                            <div className="bench-players">
                              {picks
                                .filter((p) => p.slot > 11)
                                .map((p, i) => (
                                  <button
                                    className="bench-player"
                                    key={p.player_id}
                                    onClick={() => setSelected(p.player)}
                                    aria-label={`View ${p.player.name}, substitute`}
                                  >
                                    <span className="bench-order">
                                      {i === 0 ? "GK" : i}
                                    </span>
                                    <Shirt color={p.player.color} small />
                                    <strong>{p.player.short_name}</strong>
                                    <small>
                                      {opponent(p.player, data.fixtures)}
                                    </small>
                                  </button>
                                ))}
                            </div>
                          </div>
                        </>
                      ) : (
                        playerTable(picks.map((p) => p.player))
                      )}
                      <div className="card-foot">
                        <span className="captain-key">C</span> Captain{" "}
                        <span className="captain-key vice">V</span> Vice-captain{" "}
                        <span className="foot-right">
                          Example lineup · read only
                        </span>
                      </div>
                    </section>
                    <aside className="right-rail">
                      <section className="card notes-card">
                        <div className="section-title">
                          <NotebookPen size={19} />
                          <h2>Manager’s notebook</h2>
                        </div>
                        {notesForm()}
                      </section>
                      <section className="card fixtures-card">
                        <div className="card-header">
                          <div>
                            <h2>On the fixture board</h2>
                            <p>
                              Gameweek {data.snapshot.gameweek} · fictional
                              fixtures
                            </p>
                          </div>
                        </div>
                        <div className="fixture-list">
                          {data.fixtures.map((f) => (
                            <div className="fixture" key={f.id}>
                              <span>
                                {f.home_club}
                                <small>{f.home_code}</small>
                              </span>
                              <span className="vs">vs</span>
                              <span>
                                {f.away_club}
                                <small>{f.away_code}</small>
                              </span>
                            </div>
                          ))}
                        </div>
                        <p className="fixture-note">H = home · A = away</p>
                      </section>
                      <div className="next-card">
                        <span className="eyebrow">UP NEXT</span>
                        <h3>Your team, brought into focus.</h3>
                        <p>
                          Snapshot imports and saved transfer drafts are the
                          next steps for this workspace.
                        </p>
                        <button onClick={() => setPage("workspace")}>
                          See what’s included <ArrowRight size={15} />
                        </button>
                      </div>
                    </aside>
                  </div>
                </>
              )}

              {page === "players" && (
                <section className="card library-card">
                  <div className="library-toolbar">
                    <label className="search-box">
                      <Search size={18} />
                      <span className="sr-only">Search players or clubs</span>
                      <input
                        value={search}
                        maxLength={100}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search players or clubs…"
                      />
                    </label>
                    <div
                      className="position-filters"
                      aria-label="Filter by position"
                    >
                      {(["ALL", ...positions] as const).map((p) => (
                        <button
                          key={p}
                          onClick={() => setPosition(p)}
                          aria-pressed={position === p}
                        >
                          {p === "ALL" ? "All" : p}
                        </button>
                      ))}
                    </div>
                    <label className="sort-control">
                      <SlidersHorizontal size={16} />
                      <span className="sr-only">Sort players</span>
                      <select
                        value={sort}
                        onChange={(e) => setSort(e.target.value)}
                      >
                        <option value="name">Name A–Z</option>
                        <option value="price">Highest price</option>
                      </select>
                    </label>
                  </div>
                  <div className="result-count" role="status">
                    {filteredPlayers.length}{" "}
                    {filteredPlayers.length === 1 ? "player" : "players"}{" "}
                    <span>· Fictional catalogue</span>
                  </div>
                  {playerTable(filteredPlayers)}
                </section>
              )}

              {page === "workspace" && (
                <div className="workspace-grid">
                  <section className="card workspace-card">
                    <div className="section-title">
                      <NotebookPen size={20} />
                      <h2>Your workspace</h2>
                    </div>
                    <p className="muted">
                      Your name and notes are saved on this device’s app server.
                    </p>
                    {notesForm(true)}
                    <p className="last-saved">
                      Last saved: {date(data.workspace.updated_at)}
                    </p>
                  </section>
                  <div className="workspace-stack">
                    <section className="card workspace-card">
                      <div className="section-title">
                        <Database size={19} />
                        <h2>Data & storage</h2>
                      </div>
                      <dl className="data-list">
                        <div>
                          <dt>Source</dt>
                          <dd>Synthetic demo</dd>
                        </div>
                        <div>
                          <dt>Created</dt>
                          <dd>{date(data.snapshot.created_at)}</dd>
                        </div>
                        <div>
                          <dt>Catalogue</dt>
                          <dd>
                            {data.players.length} players ·{" "}
                            {data.fixtures.length} fixtures
                          </dd>
                        </div>
                        <div>
                          <dt>Connection</dt>
                          <dd>
                            <span className="status-dot" />
                            Local API connected
                          </dd>
                        </div>
                      </dl>
                      <p className="info-note">
                        Notes persist in the app’s SQLite database. Demo data is
                        separate from your notes and is only seeded once.
                      </p>
                    </section>
                    <section className="card workspace-card">
                      <h2>Built in this milestone</h2>
                      <ul className="included-list">
                        <li>
                          <Check size={16} />
                          Demo squad and player library
                        </li>
                        <li>
                          <Check size={16} />
                          Saved workspace name and notes
                        </li>
                        <li>
                          <Check size={16} />
                          Persistent database and health check
                        </li>
                      </ul>
                      <p className="info-note">
                        Next: file imports, manual corrections, saved drafts,
                        and explainable predictions. These features are not
                        available yet.
                      </p>
                    </section>
                  </div>
                </div>
              )}
              <footer>
                <span>
                  FPL Assistant <span className="footer-dot">·</span> Made for a
                  more considered gameweek.
                </span>
                <span>
                  Private by design <ShieldCheck size={14} />
                </span>
              </footer>
            </>
          )}
        </main>
      </div>
      {selected && data && (
        <PlayerDetail
          player={selected}
          pick={data.picks.find((p) => p.player_id === selected.id)}
          fixtures={data.fixtures}
          close={() => setSelected(null)}
        />
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

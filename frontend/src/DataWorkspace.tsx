import { useEffect, useState } from "react";
import { Database, FileUp, History, Save } from "lucide-react";
import { jsonWrite, request } from "./api";
import type { CorrectionValues, Overview, Snapshot } from "./types";

const moneyInput = (n: number | null) =>
  n === null ? "" : (n / 10).toFixed(1);
const fromMoney = (s: string) =>
  s.trim() === "" ? null : Math.round(Number(s) * 10);
const optionalInt = (s: string) => (s.trim() === "" ? null : Number(s));
const effective = (data: Overview): CorrectionValues => ({
  bank_tenths: data.snapshot.bank_tenths,
  free_transfers: data.snapshot.free_transfers,
  transfer_hits: data.transfer_hits,
  chip: data.chip,
  picks: data.picks,
});
const displayDate = (s: string) => new Date(s).toLocaleString();

function PriceInput({
  value,
  label,
  onChange,
}: {
  value: number | null;
  label: string;
  onChange: (value: number | null) => void;
}) {
  const [text, setText] = useState(moneyInput(value));
  useEffect(() => {
    setText((current) =>
      fromMoney(current) === value ? current : moneyInput(value),
    );
  }, [value]);
  return (
    <input
      aria-label={label}
      type="number"
      min="0"
      max="1000"
      step="0.1"
      placeholder="Unknown"
      value={text}
      onChange={(e) => {
        setText(e.target.value);
        onChange(fromMoney(e.target.value));
      }}
    />
  );
}

function CorrectionEditor({
  data,
  onChange,
  setDirty,
  disabled,
  onBusyChange,
}: {
  data: Overview;
  onChange: (data: Overview) => void;
  setDirty: (dirty: boolean) => void;
  disabled: boolean;
  onBusyChange: (busy: boolean) => void;
}) {
  const [values, setValues] = useState<CorrectionValues>(() => effective(data));
  const [bank, setBank] = useState(moneyInput(values.bank_tenths));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [history, setHistory] = useState<
    { revision: number; reason: string; created_at: string }[]
  >([]);
  const dirty =
    JSON.stringify(values) !== JSON.stringify(effective(data)) ||
    reason !== "" ||
    bank !== moneyInput(data.snapshot.bank_tenths);
  useEffect(() => {
    setDirty(dirty);
    return () => setDirty(false);
  }, [dirty, setDirty]);
  useEffect(() => {
    void request<typeof history>(
      `/api/snapshots/${data.snapshot.id}/corrections`,
    )
      .then(setHistory)
      .catch(() =>
        setError("Could not load correction history. Reload to try again."),
      );
  }, [data.snapshot.id, data.correction_revision]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    onBusyChange(true);
    setError("");
    setMessage("");
    try {
      const result = await request<Overview>(
        `/api/snapshots/${data.snapshot.id}/corrections`,
        jsonWrite({
          expected_revision: data.correction_revision,
          reason,
          values: { ...values, bank_tenths: fromMoney(bank) },
        }),
      );
      onChange(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save corrections.");
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  }
  async function restore() {
    setBusy(true);
    setError("");
    try {
      const original = await request<{ values: CorrectionValues }>(
        `/api/snapshots/${data.snapshot.id}/original`,
      );
      setValues(original.values);
      setBank(moneyInput(original.values.bank_tenths));
      setReason("Restore original snapshot values");
      setMessage(
        "Original values loaded below. Save to record a new correction revision.",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to load original.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card import-card">
      <div className="section-title">
        <Save size={19} />
        <h2>Correct your actual squad</h2>
      </div>
      <p className="muted">
        Use this for missing or outdated snapshot values. Prices are in £
        millions; leave unknown values blank. This records your actual team,
        rather than a proposed transfer plan.
      </p>
      <form onSubmit={save}>
        <fieldset disabled={busy || disabled} className="plain-fieldset">
          <div className="data-fields">
            <label>
              Bank (£m)
              <input
                type="number"
                min="0"
                max="1000"
                step="0.1"
                value={bank}
                onChange={(e) => setBank(e.target.value)}
                placeholder="Unknown"
              />
            </label>
            <label>
              Free transfers
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={values.free_transfers ?? ""}
                onChange={(e) =>
                  setValues({
                    ...values,
                    free_transfers: optionalInt(e.target.value),
                  })
                }
                placeholder="Unknown"
              />
            </label>
            <label>
              Transfer hit (points)
              <input
                type="number"
                min="0"
                max="1000"
                step="1"
                value={values.transfer_hits ?? ""}
                onChange={(e) =>
                  setValues({
                    ...values,
                    transfer_hits: optionalInt(e.target.value),
                  })
                }
                placeholder="Unknown"
              />
            </label>
            <label>
              Chip state
              <input
                maxLength={40}
                value={values.chip ?? ""}
                onChange={(e) =>
                  setValues({ ...values, chip: e.target.value || null })
                }
                placeholder="Unknown; enter none if confirmed"
              />
            </label>
          </div>
          <div className="table-scroll correction-table">
            <table>
              <thead>
                <tr>
                  <th>Slot</th>
                  <th>Player</th>
                  <th>Purchase (£m)</th>
                  <th>Selling (£m)</th>
                  <th>C</th>
                  <th>V</th>
                </tr>
              </thead>
              <tbody>
                {values.picks.map((pick, index) => (
                  <tr key={pick.slot}>
                    <td>
                      {pick.slot}
                      {pick.slot > 11 ? " · bench" : ""}
                    </td>
                    <td>
                      <select
                        aria-label={`Player in slot ${pick.slot}`}
                        value={pick.player_id}
                        onChange={(e) => {
                          const picks = [...values.picks];
                          picks[index] = {
                            ...pick,
                            player_id: Number(e.target.value),
                            purchase_price_tenths: null,
                            selling_price_tenths: null,
                          };
                          setValues({ ...values, picks });
                        }}
                      >
                        {[...data.players]
                          .sort((a, b) => a.name.localeCompare(b.name))
                          .map((player) => (
                            <option key={player.id} value={player.id}>
                              {player.name} · {player.position} ·{" "}
                              {player.club_code}
                            </option>
                          ))}
                      </select>
                    </td>
                    {(
                      ["purchase_price_tenths", "selling_price_tenths"] as const
                    ).map((field) => (
                      <td key={field}>
                        <PriceInput
                          label={`${field === "purchase_price_tenths" ? "Purchase" : "Selling"} price slot ${pick.slot}`}
                          value={pick[field]}
                          onChange={(value) => {
                            const picks = [...values.picks];
                            picks[index] = { ...pick, [field]: value };
                            setValues({ ...values, picks });
                          }}
                        />
                      </td>
                    ))}
                    {(["is_captain", "is_vice_captain"] as const).map(
                      (field) => (
                        <td key={field}>
                          <input
                            type="radio"
                            name={field}
                            aria-label={`${field === "is_captain" ? "Captain" : "Vice-captain"} slot ${pick.slot}`}
                            checked={pick[field]}
                            onChange={() =>
                              setValues({
                                ...values,
                                picks: values.picks.map((p) => ({
                                  ...p,
                                  [field]: p.slot === pick.slot,
                                })),
                              })
                            }
                          />
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="info-note">
            Slots 1–11 are starters; 12–15 are ordered substitutes. Corrections
            check identity, unique slots, and captain/vice-captain.
            Season-specific squad, club and formation rules arrive with drafts
            in milestone 3. Selling prices are entered explicitly and never
            inferred from market value.
          </p>
          <label className="data-label">
            Reason for correction
            <input
              required
              maxLength={500}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Bank and selling prices confirmed in my team"
            />
          </label>
          <div className="data-actions">
            <button
              className="button primary"
              type="submit"
              disabled={!dirty || !reason.trim()}
            >
              Save correction
            </button>
            <button
              className="button secondary"
              type="button"
              onClick={() => void restore()}
            >
              Load original values
            </button>
          </div>
        </fieldset>
        <p role="status" className={error ? "error-text" : "save-status"}>
          {busy ? "Saving…" : error || message}
        </p>
      </form>
      <div className="correction-history">
        <h3>
          <History size={17} /> Correction history · revision{" "}
          {data.correction_revision}
        </h3>
        {history.length ? (
          <ol>
            {history.map((h) => (
              <li key={h.revision}>
                <strong>Revision {h.revision}</strong> ·{" "}
                {displayDate(h.created_at)}
                <p>{h.reason}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="muted">
            Original snapshot. No manual corrections saved.
          </p>
        )}
      </div>
    </section>
  );
}

function ImportForm({
  onChange,
  disabled,
  onBusyChange,
}: {
  onChange: (data: Overview) => void;
  disabled: boolean;
  onBusyChange: (busy: boolean) => void;
}) {
  const [mode, setMode] = useState("bundle");
  const [label, setLabel] = useState("");
  const [season, setSeason] = useState("");
  const [week, setWeek] = useState("");
  const [captured, setCaptured] = useState("");
  const [kind, setKind] = useState("deadline");
  const [files, setFiles] = useState<Record<string, File[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function parse(file: File | undefined): Promise<unknown> {
    if (!file) throw new Error("Select all required JSON files.");
    try {
      return JSON.parse(await file.text());
    } catch {
      throw new Error(`${file.name} is not valid JSON.`);
    }
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    onBusyChange(true);
    setError("");
    try {
      const all = Object.values(files).flat();
      if (all.reduce((n, f) => n + f.size, 0) > 8 * 1024 * 1024)
        throw new Error("Files exceed 8 MiB. Import fewer history files.");
      let body: unknown;
      if (mode === "bundle") body = await parse(files.bundle?.[0]);
      else
        body = {
          label,
          season,
          gameweek: Number(week),
          captured_at: new Date(captured).toISOString(),
          kind,
          bootstrap: await parse(files.bootstrap?.[0]),
          fixtures: await parse(files.fixtures?.[0]),
          team: await parse(files.team?.[0]),
          player_histories: await Promise.all(
            (files.histories ?? []).map(parse),
          ),
        };
      if (
        new TextEncoder().encode(JSON.stringify(body)).length >
        8 * 1024 * 1024
      )
        throw new Error("JSON upload exceeds 8 MiB.");
      const result = await request<Overview>("/api/imports", jsonWrite(body));
      onChange(result);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Import failed. Your saved data is unchanged.",
      );
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  }
  function fileInput(
    key: string,
    text: string,
    multiple = false,
    required = true,
  ) {
    return (
      <label className="data-label">
        {text}
        <input
          type="file"
          accept=".json,application/json"
          multiple={multiple}
          required={required}
          onChange={(e) =>
            setFiles((current) => ({
              ...current,
              [key]: Array.from(e.target.files ?? []),
            }))
          }
        />
      </label>
    );
  }
  return (
    <section className="card import-card">
      <div className="section-title">
        <FileUp size={20} />
        <h2>Import a snapshot</h2>
      </div>
      <p className="muted">
        Select JSON files already on your device. No FPL account connection is
        needed. Each new import is saved as a separate version.
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={busy || disabled} className="plain-fieldset">
          <label className="data-label">
            Import format
            <select
              value={mode}
              onChange={(e) => {
                setMode(e.target.value);
                setFiles({});
                setError("");
              }}
            >
              <option value="bundle">One snapshot bundle</option>
              <option value="files">Separate FPL JSON files</option>
            </select>
          </label>
          {mode === "bundle" ? (
            fileInput("bundle", "Snapshot bundle (.json)")
          ) : (
            <>
              <div className="data-fields">
                <label>
                  Snapshot name
                  <input
                    required
                    maxLength={80}
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                  />
                </label>
                <label>
                  Season
                  <input
                    required
                    pattern="20[0-9]{2}/[0-9]{2}"
                    placeholder="2026/27"
                    value={season}
                    onChange={(e) => setSeason(e.target.value)}
                  />
                </label>
                <label>
                  Gameweek
                  <input
                    required
                    type="number"
                    min="1"
                    max="60"
                    step="1"
                    value={week}
                    onChange={(e) => setWeek(e.target.value)}
                  />
                </label>
                <label>
                  Data captured (local time)
                  <input
                    required
                    type="datetime-local"
                    value={captured}
                    onChange={(e) => setCaptured(e.target.value)}
                  />
                </label>
                <label>
                  Team snapshot describes
                  <select
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    <option value="deadline">A gameweek deadline</option>
                    <option value="current">Current team at capture</option>
                    <option value="manual">Manually assembled team</option>
                  </select>
                </label>
              </div>
              {fileInput("bootstrap", "Bootstrap catalogue (.json)")}
              {fileInput("fixtures", "Fixtures array (.json)")}
              {fileInput("team", "Team snapshot with picks (.json)")}
              {fileInput(
                "histories",
                "Player summaries with history (optional, multiple .json files)",
                true,
                false,
              )}
            </>
          )}
          <p className="info-note">
            Public gameweek picks describe the deadline squad and may miss later
            transfers. Missing bank, free transfers, hit, chip and
            purchase/selling prices stay unknown. Confirm them in manual
            corrections after import.
          </p>
          <div className="data-actions">
            <button className="button primary" type="submit">
              <FileUp size={16} />
              {busy ? "Validating…" : "Validate & import"}
            </button>
            <a
              className="button secondary"
              href="/examples/snapshot.json"
              download="fictional-snapshot.json"
            >
              Download fictional example
            </a>
          </div>
        </fieldset>
        <p role="status" className="error-text">
          {error}
        </p>
      </form>
    </section>
  );
}

export function DataWorkspace({
  data,
  onChange,
}: {
  data: Overview;
  onChange: (data: Overview) => void;
}) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [resetKey, setResetKey] = useState(0);
  useEffect(() => {
    void request<Snapshot[]>("/api/snapshots")
      .then(setSnapshots)
      .catch(() => setError("Could not load saved snapshots."));
  }, [data.snapshot.id]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  function changed(result: Overview) {
    setDirty(false);
    setMessage("Saved locally. Your selected snapshot is ready in My squad.");
    onChange(result);
  }
  async function select(id: number) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      changed(
        await request<Overview>(
          "/api/selection",
          jsonWrite({ snapshot_id: id }, "PUT"),
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to select snapshot.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="data-workspace">
      <section className="card import-card">
        <div className="section-title">
          <Database size={20} />
          <h2>Saved snapshots</h2>
        </div>
        <label className="data-label">
          Selected snapshot
          <select
            value={data.snapshot.id}
            disabled={busy || dirty}
            onChange={(e) => void select(Number(e.target.value))}
          >
            {snapshots.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label ?? "Synthetic demo"} · {s.season} · GW {s.gameweek} · #
                {s.id}
              </option>
            ))}
          </select>
        </label>
        <dl className="snapshot-metadata">
          <div>
            <dt>Source</dt>
            <dd>
              {data.snapshot.source} · {data.snapshot.kind ?? "demonstration"}
            </dd>
          </div>
          <div>
            <dt>Captured</dt>
            <dd>
              {data.snapshot.captured_at
                ? displayDate(data.snapshot.captured_at)
                : "Synthetic example"}
            </dd>
          </div>
          <div>
            <dt>Imported</dt>
            <dd>{displayDate(data.snapshot.created_at)}</dd>
          </div>
          <div>
            <dt>Contents</dt>
            <dd>
              {data.players.length} players · {data.fixtures.length} fixtures ·{" "}
              {data.history_count}{" "}
              {data.history_count === 1 ? "match record" : "match records"}
            </dd>
          </div>
        </dl>
        <a
          href={`/api/snapshots/${data.snapshot.id}/original`}
          target="_blank"
          rel="noreferrer"
        >
          View original JSON
        </a>
        <p className="info-note">
          Original snapshots are immutable. Corrections are stored as separate
          revisions for each snapshot. Imported season and capture time are
          supplied by you; confirm the files belong together. Personal files are
          stored only in your local app database.
        </p>
        <p role="status" className={error ? "error-text" : "save-status"}>
          {error || message}
        </p>
        {dirty && (
          <p className="info-note">
            You have unsaved corrections. Save them or use Discard edits before
            switching snapshots or importing.
          </p>
        )}
        {dirty && (
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => {
              setDirty(false);
              setResetKey((n) => n + 1);
              setMessage("Unsaved corrections discarded.");
            }}
          >
            Discard edits
          </button>
        )}
      </section>
      <ImportForm
        onChange={changed}
        disabled={dirty || busy}
        onBusyChange={setBusy}
      />
      <CorrectionEditor
        key={`${data.snapshot.id}:${data.correction_revision}:${resetKey}`}
        data={data}
        onChange={changed}
        setDirty={setDirty}
        disabled={busy}
        onBusyChange={setBusy}
      />
    </div>
  );
}

"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Play, Plus } from "lucide-react";
import type { Event } from "@/lib/aws";
import { isCreditEvent, matchStatsGame, playerLabel, recordedGoals, summarizeGames, type GoalCredit, type StatPlayer } from "@/lib/game-stats";
import type { PublicMatch } from "@/lib/match-access";
import { PlayerStandings } from "./player-standings";

const timestamp = (time: number) => `${Math.floor(time / 60)}:${String(Math.floor(time % 60)).padStart(2, "0")}`;

export function MatchGameStats({ match, onSave, onWatch }: {
  match: PublicMatch;
  onSave: (match: PublicMatch) => void;
  onWatch: (event: Event) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<GoalCredit[]>([]);
  const [draftRevision, setDraftRevision] = useState(match.revision);
  const [roster, setRoster] = useState<StatPlayer[]>([]);
  const [newPlayers, setNewPlayers] = useState<StatPlayer[]>([]);
  const [newName, setNewName] = useState("");
  const [names, setNames] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    try { setNames(JSON.parse(localStorage.getItem("touchline-player-names") ?? "{}") ?? {}); }
    catch { /* Use the player profiles when browser storage is blocked. */ }
  }, []);
  const candidates = match.events.filter(isCreditEvent).sort((a, b) => a.time - b.time);
  const eventById = new Map(candidates.map((event) => [event.id, event]));
  const goals = recordedGoals(match).sort((a, b) => (eventById.get(a.eventId)?.time ?? 0) - (eventById.get(b.eventId)?.time ?? 0));
  const profiles = new Map([...match.stats?.players ?? [], ...roster, ...newPlayers].map((player) => [player.id, player]));
  const label = (id: string) => names[id] || playerLabel(profiles.get(id) ?? { id });
  const standings = summarizeGames([matchStatsGame(match)]).players;
  const choices = [...profiles.values()].sort((a, b) => label(a.id).localeCompare(label(b.id)));

  async function openEditor() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/stats/players");
      if (!response.ok) throw Error("Player profiles are temporarily unavailable.");
      const data: { players: StatPlayer[]; aliases: Record<string, string> } = await response.json();
      setRoster(data.players);
      setDraftRevision(match.revision);
      setDraft(goals.map((goal) => ({
        ...goal,
        scorer: goal.scorer ? data.aliases[goal.scorer] ?? goal.scorer : undefined,
        assists: goal.assists.map((id) => data.aliases[id] ?? id),
      })));
      setNewPlayers([]);
      setNewName("");
      setEditing(true);
    } catch (error) { setMessage((error as Error).message); }
    finally { setBusy(false); }
  }

  function changeGoal(id: string, goal: GoalCredit | null) {
    setDraft((current) => [...current.filter((row) => row.eventId !== id), ...(goal ? [goal] : [])]);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`/api/matches/${encodeURIComponent(match.id)}/stats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: draftRevision, goals: draft, newPlayers }),
      });
      const result: { match?: PublicMatch; error?: string } = await response.json();
      if (!response.ok || !result.match) throw Error(result.error ?? "Could not save game stats.");
      onSave(result.match);
      setEditing(false);
      setMessage("Game stats saved.");
    } catch (error) { setMessage((error as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <section className="panel match-game-stats" aria-labelledby="game-stats-heading">
      <div className="sectionline">
        <h2 id="game-stats-heading">Game stats</h2>
        {match.canEdit && ["ready", "needs_review", "failed"].includes(match.status) && candidates.length > 0 &&
          <button type="button" className="secondary goal-small" disabled={busy}
            onClick={() => editing ? setEditing(false) : void openEditor()}>{editing ? "Cancel" : "Edit stats"}</button>}
      </div>
      <div className="goal-metrics" aria-label="Game totals">
        <div><strong>{goals.length}</strong><span>{match.stats ? "Goals" : "Detected goals"}</span></div>
        <div><strong>{goals.reduce((sum, goal) => sum + goal.assists.length, 0)}</strong><span>Credited assists</span></div>
        <div><strong>{goals.filter((goal) => !goal.scorer).length}</strong><span>Unassigned scorers</span></div>
      </div>
      {message && <p role="status">{message}</p>}
      {editing ? (
        <form className="match-stat-editor" onSubmit={save}>
          <p className="goal-log-help">Select the plays that were goals and credit their scorers and assists.</p>
          <div className="match-stat-new">
            <label>New player<input value={newName} maxLength={60} onChange={(event) => setNewName(event.target.value)} /></label>
            <button type="button" className="secondary goal-small" disabled={!newName.trim() || busy}
              onClick={() => {
                setNewPlayers([...newPlayers, { id: `player-${crypto.randomUUID()}`, name: newName.trim() }]);
                setNewName("");
              }}><Plus size={15} />Add player</button>
          </div>
          {candidates.map((event) => {
            const goal = draft.find((row) => row.eventId === event.id);
            const slots = [goal?.assists[0] ?? "", goal?.assists[1] ?? ""];
            function setCredit(index: number, value: string) {
              if (!goal) return;
              const scorer = index === 0 ? value || undefined : goal.scorer;
              if (index) slots[index - 1] = value;
              changeGoal(event.id, { ...goal, scorer, assists: [...new Set(slots)].filter((id) => id && id !== scorer) });
            }
            return <fieldset key={event.id} className="match-stat-row">
              <legend><label><input type="checkbox" checked={Boolean(goal)} disabled={busy}
                onChange={({ target }) => changeGoal(event.id, target.checked ? { eventId: event.id, assists: [] } : null)} /> Goal at {timestamp(event.time)}</label></legend>
              <button type="button" className="secondary goal-small" onClick={() => onWatch(event)}><Play size={14} />Preview</button>
              {goal && <div className="match-stat-picks">
                {["Scorer", "First assist", "Second assist"].map((role, index) => (
                  <label key={role}>{role}<select value={index ? slots[index - 1] : goal.scorer ?? ""} disabled={busy}
                    onChange={(e) => setCredit(index, e.target.value)}>
                    <option value="">{index ? "None" : "Unassigned"}</option>
                    {choices.map((player) => <option key={player.id} value={player.id}>{label(player.id)}</option>)}
                  </select></label>
                ))}
              </div>}
            </fieldset>;
          })}
          <button type="submit" className="primary goal-small" disabled={busy}>{busy ? "Saving…" : "Save stats"}</button>
        </form>
      ) : goals.length ? <>
        {standings.length > 0 && <div className="match-player-totals">
          <h3 id="game-player-totals">Player totals</h3>
          <PlayerStandings headingId="game-player-totals" players={standings} />
        </div>}
        <ol className="stats-game-list match-goal-list">
          {goals.map((goal) => {
            const event = eventById.get(goal.eventId);
            if (!event) return null;
            return <li key={goal.eventId}>
              <button type="button" className="goal-watch" aria-label={`Watch goal at ${timestamp(event.time)}`} onClick={() => onWatch(event)}><Play size={16} />{timestamp(event.time)}</button>
              <div><strong>{goal.scorer ? label(goal.scorer) : "Scorer unassigned"}</strong>
                <p>{goal.assists.length ? `Assists · ${goal.assists.map(label).join(" · ")}` : "No assists credited"}</p></div>
            </li>;
          })}
        </ol>
      </> : <p className="goal-log-help">No goals recorded for this game.</p>}
    </section>
  );
}

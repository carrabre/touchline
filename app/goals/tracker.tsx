"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowDown, ArrowUpRight, Download, Play, UserRound } from "lucide-react";
import { CopyGameLink } from "@/app/components/copy-game-link";
import { gameHref } from "@/lib/game-paths";
import { rankPlayers } from "@/lib/game-stats";

type Player = { id: string; photo: string; name?: string };
type Goal = {
  number: number;
  clip: number;
  sourceTime: string;
  reelTime: number;
  title: string;
  detail: string;
  scorer: string;
  assists: string[];
  attribution: "clear" | "likely";
};
type ReviewedMatch = {
  id: string;
  date: string;
  title: string;
  reel: string;
  download: string;
  poster: string;
  players: Player[];
  playerAliases?: Record<string, string>;
  goals: Goal[];
  replays: { number: number; title: string; sourceTime: string; outcome: "goal" | "excluded"; video: string }[];
};

const statColumns = ["goals", "assists"] as const;

const storageKey = "touchline-player-names";

export function GoalTracker({ match }: { match: ReviewedMatch }) {
  const video = useRef<HTMLVideoElement>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [filter, setFilter] = useState("");
  const [sortBy, setSortBy] = useState<(typeof statColumns)[number]>("goals");
  const [activeGoal, setActiveGoal] = useState<number | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [nameError, setNameError] = useState("");
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (!saved) return;
      const savedNames: Record<string, string> = JSON.parse(saved) ?? {};
      for (const [alias, player] of Object.entries(match.playerAliases ?? {})) {
        if (!savedNames[player] && savedNames[alias]) savedNames[player] = savedNames[alias];
        delete savedNames[alias];
      }
      setNames(savedNames);
    } catch {
      // Playback and stats remain available when browser storage is blocked.
    }
  }, [match.playerAliases]);

  const players = new Map(match.players.map((player) => [player.id, player]));
  const name = (id: string) => names[id] || players.get(id)?.name || `Player ${id.slice(1)}`;
  const visible = match.goals.filter((goal) =>
    !filter || goal.scorer === filter || goal.assists.includes(filter));
  const totalAssists = match.goals.reduce((total, goal) => total + goal.assists.length, 0);
  const rankedPlayers = rankPlayers(match.players.map((player) => ({
    ...player,
    goals: match.goals.filter((goal) => goal.scorer === player.id).length,
    assists: match.goals.filter((goal) => goal.assists.includes(player.id)).length,
  })), sortBy);

  function saveNames(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextNames = { ...names };
    for (const player of match.players) {
      const value = draft[player.id]?.trim();
      if (value) nextNames[player.id] = value;
      else delete nextNames[player.id];
    }
    try {
      localStorage.setItem(storageKey, JSON.stringify(nextNames));
    } catch {
      setNameError("Your browser blocked saving player names.");
      return;
    }
    setNames(nextNames);
    setEditing(false);
  }

  function play(goal: Goal) {
    const player = video.current;
    if (!player) return;
    setActiveGoal(goal.number);
    player.currentTime = goal.reelTime + 0.08;
    void player.play().catch(() => {});
    player.focus({ preventScroll: true });
    player.scrollIntoView({ block: "center" });
  }

  function playerLabel(id: string) {
    const player = players.get(id);
    return <span className="goal-person">{player && <img src={player.photo} alt="" loading="lazy" decoding="async" width="32" height="32" />}{name(id)}</span>;
  }

  return (
    <>
      <div className="pagehead goal-heading">
        <div>
          <h1>{match.title}</h1>
          <p>Game stats <span aria-hidden="true">·</span> {match.date}</p>
        </div>
        <div className="match-actions">
          <CopyGameLink href={gameHref(match.id)} />
          <a className="secondary" href="#highlight-reel"><Play size={17} />Watch reel</a>
        </div>
      </div>

      <section className="goal-overview" aria-label="Match totals">
        <div className="goal-metrics">
          <div><strong>{match.goals.length}</strong><span>Goals</span></div>
          <div><strong>{totalAssists}</strong><span>Credited assists</span></div>
          <div><strong>{match.goals.filter((goal) => goal.attribution === "likely").length}</strong><span>Provisional scorer credits</span></div>
        </div>
      </section>

      <section className="goal-section" aria-labelledby="player-heading">
        <div className="sectionline">
          <h2 id="player-heading">Player rankings</h2>
          <button className="secondary goal-small" type="button" aria-expanded={editing}
            onClick={() => { setDraft({ ...names }); setNameError(""); setEditing(!editing); }}>
            <UserRound size={16} />{editing ? "Close" : "Edit names"}
          </button>
        </div>
        {editing &&
          <form className="panel goal-name-form" onSubmit={saveNames}>
            <p>Names are saved in this browser. Player totals follow the profile across jersey colors.</p>
            <div className="goal-name-grid">
              {match.players.map((player) => (
                <label key={player.id} className="field">
                  <span className="goal-person"><img src={player.photo} alt="" loading="lazy" decoding="async" width="32" height="32" />Player {player.id.slice(1)}</span>
                  <input maxLength={60} value={draft[player.id] ?? ""} placeholder={`Player ${player.id.slice(1)}`}
                    onChange={(event) => setDraft({ ...draft, [player.id]: event.target.value })} />
                </label>
              ))}
            </div>
            {nameError && <p role="alert">{nameError}</p>}
            <button className="primary goal-small" type="submit">Save names</button>
          </form>
        }
        <div className="goal-rankings">
          <table aria-labelledby="player-heading">
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Player</th>
                {statColumns.map((stat) => (
                  <th key={stat} scope="col" className="goal-stat"
                    aria-sort={sortBy === stat ? "descending" : undefined}>
                    <button type="button" className="goal-sort" onClick={() => setSortBy(stat)}>
                      {stat === "goals" ? "Goals" : "Assists"}
                      {sortBy === stat && <ArrowDown size={14} aria-hidden />}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rankedPlayers.map((player) => (
                <tr key={player.id}>
                  <td className="goal-rank">{player.rank}</td>
                  <th scope="row">
                    <a className="goal-player-link" href="#goal-log" onClick={() => setFilter(player.id)}
                      aria-label={`View plays for ${name(player.id)}`}>
                      {playerLabel(player.id)}<ArrowUpRight size={15} aria-hidden />
                    </a>
                  </th>
                  <td className="goal-stat">{player.goals}</td>
                  <td className="goal-stat">{player.assists}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="highlight-reel" className="goal-section goal-reel" aria-labelledby="reel-heading" tabIndex={-1}>
        <div className="goal-reel-label">
          <div>
            <h2 id="reel-heading">Highlight reel</h2>
            {activeGoal !== null && <span role="status">Play #{activeGoal}</span>}
          </div>
          <a className="secondary goal-small" href={match.download} download="Touchline - Indoor Soccer Highlights.mp4">
            <Download size={17} />Download reel
          </a>
        </div>
        <video ref={video} src={match.reel} poster={match.poster} controls playsInline preload="metadata"
          aria-label={`${match.title} highlight reel`} tabIndex={0} />
      </section>

      <section id="goal-log" className="goal-section" aria-labelledby="log-heading" tabIndex={-1}>
        <div className="sectionline goal-log-title">
          <h2 id="log-heading">Goal log</h2>
          <label className="goal-filter">Player
            <select value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="">All players</option>
              {match.players.map((player) => <option key={player.id} value={player.id}>{name(player.id)}</option>)}
            </select>
          </label>
        </div>
        <p className="goal-log-help">Tap a play to jump to it in the reel. Provisional credits mark plays where the last touch or player identity is partly obscured. The final pass is listed first.</p>
        <ol className="goal-log">
          {visible.map((goal) => (
            <li key={goal.number} className="goal-row">
              <button className="goal-watch" aria-label={`Watch play ${goal.number}, ${goal.title}`} onClick={() => play(goal)}>
                <Play size={17} aria-hidden /><span>#{String(goal.number).padStart(2, "0")}</span>
              </button>
              <div className="goal-description">
                <strong>{goal.title}</strong>
                <small>Clip {goal.clip} · {goal.sourceTime}</small>
                <p>{goal.detail}</p>
              </div>
              <div className="goal-credit">
                <small>Scorer {goal.attribution === "likely" && <span className="goal-provisional">· provisional</span>}</small>
                {playerLabel(goal.scorer)}
              </div>
              <div className="goal-credit">
                <small>Assists</small>
                {goal.assists.length ? goal.assists.map((id) => <div key={id}>{playerLabel(id)}</div>) :
                  <span className="goal-unclear">None credited</span>}
              </div>
            </li>
          ))}
        </ol>
      </section>
      <section className="goal-section" aria-labelledby="goal-reviews-heading">
        <div className="sectionline"><h2 id="goal-reviews-heading">Goal-line replays</h2></div>
        <div className="goal-review-list">
          {match.replays.map((replay) => (
            <a key={replay.number} className="secondary goal-small" href={replay.video} target="_blank" rel="noreferrer"
              title={`${replay.sourceTime} · ${replay.title}`}>
              <Play size={15} />#{replay.number} · {replay.outcome === "goal" ? "Goal" : "Ruled out"}
            </a>
          ))}
        </div>
      </section>
    </>
  );
}

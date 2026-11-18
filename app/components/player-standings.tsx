"use client";

import { useEffect, useState } from "react";
import { ArrowDown, UserRound } from "lucide-react";
import { playerLabel, rankPlayers, type StatPlayer } from "@/lib/game-stats";

type Standing = StatPlayer & { goals: number; assists: number };

const noAliases: Record<string, string> = {};

export function PlayerStandings({ players, headingId, aliases = noAliases }: {
  players: Standing[]; headingId: string; aliases?: Record<string, string>;
}) {
  const [stat, setStat] = useState<"goals" | "assists">("goals");
  const [names, setNames] = useState<Record<string, string>>({});
  useEffect(() => {
    try {
      const saved: Record<string, string> = JSON.parse(localStorage.getItem("touchline-player-names") ?? "{}") ?? {};
      for (const [alias, player] of Object.entries(aliases)) {
        if (!saved[player] && saved[alias]) saved[player] = saved[alias];
      }
      setNames(saved);
    } catch {
      // Default labels stay available when browser storage is blocked.
    }
  }, [aliases]);

  if (!players.length) return <p className="goal-log-help">Player standings will appear once goals or assists are credited.</p>;
  return (
    <div className="goal-rankings">
      <table aria-labelledby={headingId}>
        <thead><tr>
          <th scope="col">Rank</th><th scope="col">Player</th>
          {(["goals", "assists"] as const).map((key) => (
            <th key={key} scope="col" className="goal-stat" aria-sort={stat === key ? "descending" : undefined}>
              <button type="button" className="goal-sort" onClick={() => setStat(key)}>
                {key === "goals" ? "Goals" : "Assists"}{stat === key && <ArrowDown size={14} aria-hidden />}
              </button>
            </th>
          ))}
        </tr></thead>
        <tbody>{rankPlayers(players, stat).map((player) => (
          <tr key={player.id}>
            <td className="goal-rank">{player.rank}</td>
            <th scope="row"><span className="goal-person">
              {player.photo ? <img src={player.photo} alt="" loading="lazy" width={32} height={32} /> : <UserRound size={23} aria-hidden />}
              {names[player.id] || playerLabel(player)}
            </span></th>
            <td className="goal-stat">{player.goals}</td><td className="goal-stat">{player.assists}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

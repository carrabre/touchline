import type { Metadata } from "next";
import { ArrowUpRight } from "lucide-react";
import { StatsShell } from "@/app/components/stats-shell";
import { gameHref } from "@/lib/game-paths";
import { summarizeGames } from "@/lib/game-stats";
import { listStatsGames } from "@/lib/shared-games";
import { PlayerStandings } from "@/app/components/player-standings";
import "@/app/goals/tracker.css";

export const metadata: Metadata = { title: "Leaderboard · Touchline" };
export const dynamic = "force-dynamic";

export default async function LeaderboardPage() {
  const games = await listStatsGames().catch(() => null);
  const totals = games ? summarizeGames(games) : null;
  const countedGames = games?.filter((game) => game.goals.length) ?? [];

  return (
    <StatsShell leaderboard>
      <div className="pagehead goal-heading">
        <div><h1>Leaderboard</h1><p>Player totals across all games</p></div>
      </div>
      {totals ? <>
        <section className="goal-overview" aria-label="Leaderboard totals">
          <div className="goal-metrics">
            <div><strong>{countedGames.length}</strong><span>{countedGames.length === 1 ? "Game with goals" : "Games with goals"}</span></div>
            <div><strong>{totals.totalGoals}</strong><span>Goals</span></div>
            <div><strong>{totals.assists}</strong><span>Credited assists</span></div>
          </div>
        </section>
        <section className="goal-section" aria-labelledby="leaderboard-ranks">
          <div className="sectionline"><h2 id="leaderboard-ranks">Player standings</h2></div>
          {totals.totalGoals > totals.credited && <p className="goal-log-help">{totals.totalGoals - totals.credited} {totals.totalGoals - totals.credited === 1 ? "goal is" : "goals are"} awaiting a scorer.</p>}
          <PlayerStandings headingId="leaderboard-ranks" players={totals.players} aliases={totals.aliases} />
        </section>
        {countedGames.length > 0 && (
          <section className="goal-section" aria-labelledby="leaderboard-games">
            <div className="sectionline"><h2 id="leaderboard-games">Game stats</h2></div>
            <ul className="stats-game-list">
              {countedGames.map((game) => (
                <li key={game.id}><a href={gameHref(game.id)}>
                  <strong>{game.title}</strong><span>{game.goals.length} {game.goals.length === 1 ? "goal" : "goals"} <ArrowUpRight size={16} aria-hidden /></span>
                </a></li>
              ))}
            </ul>
          </section>
        )}
      </> : <p role="status">The leaderboard is temporarily unavailable.</p>}
    </StatsShell>
  );
}

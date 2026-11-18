import type { Event, Match } from "./aws";

export type StatPlayer = { id: string; name?: string; photo?: string };
export type GoalCredit = { eventId: string; scorer?: string; assists: string[] };
export type MatchStats = { players: StatPlayer[]; goals: GoalCredit[] };
export type StatsGame = {
  id: string;
  title: string;
  date: string;
  players: StatPlayer[];
  playerAliases?: Record<string, string>;
  goals: { scorer?: string; assists: string[] }[];
};

export function recordedGoals(match: Pick<Match, "events" | "stats">): GoalCredit[] {
  if (!match.stats) {
    return match.events
      .filter((event) => event.kind === "goal" && event.reviewOutcome !== "unconfirmed")
      .map((event) => ({ eventId: event.id, assists: [] }));
  }
  const available = new Set(match.events.map((event) => event.id));
  return match.stats.goals.filter((goal) => available.has(goal.eventId));
}

export function matchStatsGame(match: Pick<Match, "id" | "title" | "created" | "stats" | "events" | "status">): StatsGame {
  return {
    id: match.id,
    title: match.title,
    date: new Date(match.created).toISOString(),
    players: match.stats?.players ?? [],
    goals: match.stats || ["ready", "needs_review"].includes(match.status) ? recordedGoals(match) : [],
  };
}

export function summarizeGames(games: StatsGame[]) {
  const players = new Map<string, StatPlayer>();
  const aliases: Record<string, string> = {};
  for (const game of games) {
    Object.assign(aliases, game.playerAliases);
    for (const player of game.players) {
      const previous = players.get(player.id);
      players.set(player.id, {
        id: player.id,
        name: previous?.name ?? player.name,
        photo: previous?.photo ?? player.photo,
      });
    }
  }
  const canonical = (id: string) => Object.hasOwn(aliases, id) ? aliases[id] : id;
  const totals = new Map<string, { goals: number; assists: number }>();
  let totalGoals = 0;
  let credited = 0;
  let assists = 0;
  function count(id: string, stat: "goals" | "assists") {
    if (!players.has(id)) return false;
    const total = totals.get(id) ?? { goals: 0, assists: 0 };
    total[stat]++;
    totals.set(id, total);
    return true;
  }
  for (const game of games) {
    for (const goal of game.goals) {
      totalGoals++;
      const scorer = goal.scorer ? canonical(goal.scorer) : undefined;
      if (scorer && count(scorer, "goals")) credited++;
      for (const id of new Set(goal.assists.map(canonical))) {
        if (id !== scorer && count(id, "assists")) assists++;
      }
    }
  }
  return {
    totalGoals,
    credited,
    assists,
    aliases,
    roster: [...players.values()].filter((player) => canonical(player.id) === player.id),
    players: [...totals].map(([id, total]) => ({ ...players.get(id)!, ...total })),
  };
}

export const playerLabel = (player: StatPlayer) => player.name ?? `Player ${player.id.slice(1)}`;

export function isCreditEvent(event: Event) {
  return ["goal", "possible_goal", "manual"].includes(event.kind) || event.manual === true;
}

export function rankPlayers<Player extends { id: string; goals: number; assists: number }>(
  players: Player[], stat: "goals" | "assists",
) {
  const secondary = stat === "goals" ? "assists" : "goals";
  const ordered = [...players].sort((a, b) => b[stat] - a[stat] || b[secondary] - a[secondary] || a.id.localeCompare(b.id));
  let rank = 0;
  return ordered.map((player, index) => {
    const previous = ordered[index - 1];
    if (!previous || previous.goals !== player.goals || previous.assists !== player.assists) rank = index + 1;
    return { ...player, rank };
  });
}

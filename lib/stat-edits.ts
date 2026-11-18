import { z } from "zod";
import type { Event } from "./aws";
import { isCreditEvent, type MatchStats, type StatPlayer } from "./game-stats";

const id = z.string().min(1).max(128);
export const statEdit = z.object({
  revision: z.number().int().nonnegative(),
  goals: z.array(z.object({ eventId: id, scorer: id.optional(), assists: z.array(id).max(2) })).max(100),
  newPlayers: z.array(z.object({
    id: z.string().regex(/^player-[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/),
    name: z.string().trim().min(1).max(60),
  })).max(100),
});

export function buildMatchStats(
  edit: z.infer<typeof statEdit>, events: Event[], roster: StatPlayer[], aliases: Record<string, string>,
): MatchStats | null {
  const profiles = new Map(roster.map((player) => [player.id, player]));
  for (const player of edit.newPlayers) {
    if (profiles.has(player.id)) return null;
    profiles.set(player.id, player);
  }
  const candidates = new Set(events.filter(isCreditEvent).map((event) => event.id));
  const seen = new Set<string>();
  const selected = new Set<string>();
  const resolve = (key: string) => Object.hasOwn(aliases, key) ? aliases[key] : key;
  const goals: MatchStats["goals"] = [];
  for (const goal of edit.goals) {
    if (!candidates.has(goal.eventId) || seen.has(goal.eventId)) return null;
    seen.add(goal.eventId);
    const scorer = goal.scorer ? resolve(goal.scorer) : undefined;
    const helpers = goal.assists.map(resolve);
    if (new Set(helpers).size !== helpers.length || helpers.includes(scorer ?? "")) return null;
    if (scorer) selected.add(scorer);
    for (const helper of helpers) selected.add(helper);
    goals.push({ ...goal, scorer, assists: helpers });
  }
  const players: StatPlayer[] = [];
  for (const key of selected) {
    const player = profiles.get(key);
    if (!player) return null;
    players.push(player);
  }
  return { goals, players };
}

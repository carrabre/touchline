import "server-only";
import { z } from "zod";
import { db, signed } from "@/lib/aws";

import { isReviewedGameId } from "@/lib/game-paths";
const mediaKey = z.string().max(300);
const playerId = z.string().regex(/^P\d{2,5}$/);
const time = z.string().regex(/^\d{2}:\d{2}\.\d$/);
const record = z.object({
  id: z.string().refine(isReviewedGameId),
  title: z.string().max(100),
  date: z.string().max(100),
  reel: mediaKey,
  playback: mediaKey.optional(),
  poster: mediaKey,
  players: z.array(z.object({ id: playerId, photo: mediaKey, name: z.string().min(1).max(60).optional() })).max(100),
  playerAliases: z.record(playerId, playerId).optional(),
  goals: z.array(z.object({
    number: z.number().int().positive(),
    clip: z.number().int().positive(),
    sourceTime: time,
    reelTime: z.number().nonnegative(),
    title: z.string().max(160),
    detail: z.string().max(800),
    scorer: playerId,
    assists: z.array(playerId).max(2),
    attribution: z.enum(["clear", "likely"]),
  })).max(200),
  replays: z.array(z.object({
    number: z.number().int().positive(),
    sourceTime: time,
    title: z.string().max(160),
    outcome: z.enum(["goal", "excluded"]),
    video: mediaKey,
  })).max(20),
}).refine((doc) => {
  const players = new Set(doc.players.map((player) => player.id));
  const plays = new Set(doc.goals.map((goal) => goal.number));
  const aliases = Object.entries(doc.playerAliases ?? {});
  const keys = [doc.reel, doc.playback ?? doc.reel, doc.poster,
    ...doc.players.map((player) => player.photo), ...doc.replays.map((replay) => replay.video)];
  return keys.every((key) => key.startsWith(`reviewed/${doc.id}/`))
    && players.size === doc.players.length && plays.size === doc.goals.length
    && aliases.every(([alias, target]) => !players.has(alias) && players.has(target)) && doc.goals.every(
    (goal) => players.has(goal.scorer) && new Set(goal.assists).size === goal.assists.length
      && goal.assists.every((id) => players.has(id) && id !== goal.scorer),
  );
});

export const parseReviewedRecord = (doc: unknown) => record.parse(doc);

export async function loadReviewedRecord(id: string) {
  if (!isReviewedGameId(id)) return null;
  const result = await db("GetItem", { Key: { id: { S: id } }, ConsistentRead: true });
  if (!result.Item || result.Item.stage.S !== "reviewed") return null;
  const doc = parseReviewedRecord(JSON.parse(result.Item.doc.S));
  return doc.id === id ? doc : null;
}

export async function reviewedMediaKey(id: string, asset: string) {
  const doc = await loadReviewedRecord(id);
  if (!doc) return null;
  if (asset === "reel") return doc.playback ?? doc.reel;
  if (asset === "poster") return doc.poster;
  if (asset.startsWith("player-")) {
    return doc.players.find((player) => player.id === asset.slice(7))?.photo ?? null;
  }
  return doc.replays.find((replay) => asset === `replay-${replay.number}`)?.video ?? null;
}

export function reviewedStatsGame(doc: z.infer<typeof record>) {
  const prefix = `/api/playback/${encodeURIComponent(doc.id)}`;
  return { id: doc.id, title: doc.title, date: doc.date, goals: doc.goals, playerAliases: doc.playerAliases,
    players: doc.players.map((player) => ({ ...player, photo: `${prefix}/player-${player.id}` })) };
}

export async function loadReviewedMatch(doc: z.infer<typeof record>) {
  const prefix = `/api/playback/${encodeURIComponent(doc.id)}`;
  const download = await signed(doc.reel, "GET", "?response-content-disposition=attachment%3B%20filename%3D%22Touchline%20Highlights.mp4%22");
  return {
    ...reviewedStatsGame(doc), download,
    reel: `${prefix}/reel`, poster: `${prefix}/poster`,
    replays: doc.replays.map((replay) => ({ ...replay, video: `${prefix}/replay-${replay.number}` })),
  };
}

import "server-only";
import { z } from "zod";
import { db, signed } from "@/lib/aws";

import { gameHref, REVIEWED_MATCH_ID } from "@/lib/game-paths";
const mediaPrefix = `reviewed/${REVIEWED_MATCH_ID}/`;
const mediaKey = z.string().startsWith(mediaPrefix).max(300);
const playerId = z.string().regex(/^P\d{2,5}$/);
const time = z.string().regex(/^\d{2}:\d{2}\.\d$/);
const record = z.object({
  id: z.literal(REVIEWED_MATCH_ID),
  title: z.string().max(100),
  date: z.string().max(100),
  reel: mediaKey,
  playback: mediaKey.optional(),
  poster: mediaKey,
  players: z.array(z.object({ id: playerId, photo: mediaKey })).max(100),
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
  return players.size === doc.players.length && plays.size === doc.goals.length && doc.goals.every(
    (goal) => players.has(goal.scorer) && new Set(goal.assists).size === goal.assists.length
      && goal.assists.every((id) => players.has(id) && id !== goal.scorer),
  );
});

async function loadReviewedRecord() {
  const result = await db("GetItem", { Key: { id: { S: REVIEWED_MATCH_ID } }, ConsistentRead: true });
  if (!result.Item || result.Item.stage.S !== "reviewed") return null;
  return record.parse(JSON.parse(result.Item.doc.S));
}

export async function reviewedMediaKey(asset: string) {
  const doc = await loadReviewedRecord();
  if (!doc) return null;
  if (asset === "reel") return doc.playback ?? doc.reel;
  if (asset === "poster") return doc.poster;
  return doc.replays.find((replay) => asset === `replay-${replay.number}`)?.video ?? null;
}

export async function loadReviewedMatch() {
  const doc = await loadReviewedRecord();
  if (!doc) return null;
  const prefix = `${gameHref(doc.id)}/play`;
  const [download, players] = await Promise.all([
    signed(doc.reel, "GET", "?response-content-disposition=attachment%3B%20filename%3D%22Touchline%20Highlights.mp4%22"),
    Promise.all(doc.players.map(async ({ id, photo }) => ({ id, photo: await signed(photo) }))),
  ]);
  return {
    id: doc.id, date: doc.date, title: doc.title, goals: doc.goals, players, download,
    reel: `${prefix}/reel`, poster: `${prefix}/poster`,
    replays: doc.replays.map((replay) => ({ ...replay, video: `${prefix}/replay-${replay.number}` })),
  };
}

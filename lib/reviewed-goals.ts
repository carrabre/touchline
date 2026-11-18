import "server-only";
import { z } from "zod";
import { db, signed } from "@/lib/aws";

import { REVIEWED_MATCH_ID } from "@/lib/game-paths";
const mediaPrefix = `reviewed/${REVIEWED_MATCH_ID}/`;
const mediaKey = z.string().startsWith(mediaPrefix).max(300);
const playerId = z.string().regex(/^P\d{2,5}$/);
const time = z.string().regex(/^\d{2}:\d{2}\.\d$/);
const record = z.object({
  id: z.literal(REVIEWED_MATCH_ID),
  title: z.string().max(100),
  date: z.string().max(100),
  reel: mediaKey,
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

export async function loadReviewedMatch() {
  const result = await db("GetItem", { Key: { id: { S: REVIEWED_MATCH_ID } }, ConsistentRead: true });
  if (!result.Item || result.Item.stage.S !== "reviewed") return null;
  const doc = record.parse(JSON.parse(result.Item.doc.S));
  const [reel, download, poster, players, replays] = await Promise.all([
    signed(doc.reel),
    signed(doc.reel, "GET", "?response-content-disposition=attachment%3B%20filename%3D%22Touchline%20Highlights.mp4%22"),
    signed(doc.poster),
    Promise.all(doc.players.map(async ({ id, photo }) => ({ id, photo: await signed(photo) }))),
    Promise.all(doc.replays.map(async (replay) => ({ ...replay, video: await signed(replay.video) }))),
  ]);
  return { ...doc, reel, download, poster, players, replays };
}

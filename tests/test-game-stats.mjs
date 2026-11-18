import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";
import * as zod from "zod";
import * as gameStats from "../lib/game-stats.ts";
import * as gamePaths from "../lib/game-paths.ts";
import * as matchAccess from "../lib/match-access.ts";

function load(path, dependencies) {
  const source = ts.transpileModule(readFileSync(new URL(path, import.meta.url), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = {};
  new Function("require", "exports", source)((name) => dependencies[name], module);
  return module;
}

const edits = load("../lib/stat-edits.ts", { zod, "./game-stats": gameStats });
const roster = [{ id: "P01", photo: "/photo" }, { id: "P05" }, { id: "P06" }];
const aliases = { P07: "P01" };
const game = {
  id: "uploaded-game", title: "Second match", created: 0, owner: "uploader", status: "ready", revision: 2,
  reelKey: "reel.mp4", events: [
    { id: "e1", kind: "goal" },
    { id: "e2", kind: "possible_goal", reviewOutcome: "unconfirmed" },
    { id: "e3", kind: "manual", manual: true },
  ],
};
const reviewed = {
  id: "reviewed-first-game", title: "First match", date: "November 16, 2026", players: roster, playerAliases: aliases,
  goals: [{ scorer: "P01", assists: ["P05"] }, { scorer: "P05", assists: [] }],
};

test("confirmed credits follow the same player across games and the leaderboard leaves unassigned goals out of player totals", () => {
  const next = {
    ...game,
    stats: { players: roster, goals: [
      { eventId: "e1", scorer: "P07", assists: ["P05", "P06"] },
      { eventId: "e2", assists: [] },
      { eventId: "removed", scorer: "P05", assists: [] },
    ] },
  };
  const totals = gameStats.summarizeGames([reviewed, gameStats.matchStatsGame(next)]);
  assert.equal(totals.totalGoals, 4);
  assert.equal(totals.credited, 3);
  assert.equal(totals.assists, 3);
  assert.deepEqual(totals.players.map(({ id, goals, assists }) => [id, goals, assists]), [
    ["P01", 2, 0], ["P05", 1, 2], ["P06", 0, 1],
  ]);
  assert.equal(gameStats.recordedGoals(next).length, 2);
  assert.deepEqual(gameStats.recordedGoals(game), [{ eventId: "e1", assists: [] }]);
  assert.deepEqual(gameStats.matchStatsGame({ ...game, status: "analysis" }).goals, []);
  assert.deepEqual(gameStats.recordedGoals({ ...game, stats: { players: [], goals: [] } }), []);
});

test("the stat editor rejects unknown plays, duplicate credits and assists for a scorer's former profile", () => {
  const build = (goals) => edits.buildMatchStats({ goals, newPlayers: [], revision: 2 }, game.events, roster, aliases);
  assert.equal(build([{ eventId: "wrong", scorer: "P01", assists: [] }]), null);
  assert.equal(build([{ eventId: "e1", scorer: "P99", assists: [] }]), null);
  assert.equal(build([{ eventId: "e1", scorer: "P01", assists: ["P07"] }]), null);
  assert.equal(build([{ eventId: "e1", scorer: "P01", assists: [] }, { eventId: "e1", assists: [] }]), null);
  assert.deepEqual(build([{ eventId: "e2", scorer: "P07", assists: ["P05"] }]).goals, [
    { eventId: "e2", scorer: "P01", assists: ["P05"] },
  ]);
});

test("only the uploader can save stats, the write is conditional, and it keeps the video", async () => {
  let write;
  const { POST } = load("../app/api/matches/[id]/stats/route.ts", {
    "@/lib/aws": {
      owned: async (_id, owner) => {
        if (owner !== game.owner) throw Error("Match not found.");
        return structuredClone(game);
      },
      put: async (match, condition, values) => { write = { match, condition, values }; },
    },
    "@/lib/game-paths": gamePaths,
    "@/lib/game-stats": gameStats,
    "@/lib/match-access": matchAccess,
    "@/lib/runtime-config": { requestOwner: (request) => request.headers.get("test-owner") },
    "@/lib/shared-games": { listStatsGames: async () => [reviewed] },
    "@/lib/stat-edits": edits,
  });
  const call = (owner, revision) => POST(new Request("https://test.example/api/matches/uploaded-game/stats", {
    method: "POST", headers: { origin: "https://test.example", "test-owner": owner },
    body: JSON.stringify({ revision, goals: [{ eventId: "e2", scorer: "P01", assists: ["P05"] }], newPlayers: [] }),
  }), { params: Promise.resolve({ id: game.id }) });
  assert.equal((await call("viewer", 2)).status, 404);
  assert.equal((await call("uploader", 1)).status, 409);
  assert.equal(write, undefined);
  assert.equal((await call("uploader", 2)).status, 200);
  assert.equal(write.match.reelKey, "reel.mp4");
  assert.equal(write.match.revision, 3);
  assert.equal(write.values[":r"].N, "2");
  assert.match(write.condition, /revision = :r AND #s = :s/);
  assert.deepEqual(write.match.stats.goals, [{ eventId: "e2", scorer: "P01", assists: ["P05"] }]);
});

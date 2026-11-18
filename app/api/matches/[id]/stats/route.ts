import { owned, put } from "@/lib/aws";
import { isGameId } from "@/lib/game-paths";
import { summarizeGames } from "@/lib/game-stats";
import { isPublicMatch, publicMatch } from "@/lib/match-access";
import { requestOwner } from "@/lib/runtime-config";
import { listStatsGames } from "@/lib/shared-games";
import { buildMatchStats, statEdit } from "@/lib/stat-edits";

const failure = (error: string, status: number) =>
  Response.json({ error }, { status, headers: { "Cache-Control": "no-store" } });

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const owner = requestOwner(request);
  const origin = request.headers.get("origin");
  if (!owner) return failure("Open your match library to start a session.", 401);
  if (origin && origin !== new URL(request.url).origin) return failure("Cross-site request rejected.", 403);
  if (!isGameId(id)) return failure("Match not found.", 404);

  try {
    const match = await owned(id, owner);
    if (!isPublicMatch(match)) return failure("Match not found.", 404);
    if (!["ready", "needs_review", "failed"].includes(match.status)) {
      return failure("Wait for processing to finish before saving stats.", 409);
    }
    const parsed = statEdit.safeParse(await request.json().catch(() => null));
    if (!parsed.success) return failure("Choose valid goals, player profiles and up to two assists per goal.", 400);
    const revision = match.revision;
    if (parsed.data.revision !== revision) return failure("This match changed. Refresh before saving stats.", 409);
    const { roster, aliases } = summarizeGames(await listStatsGames());
    const profiles = new Map((match.stats?.players ?? []).map((player) => [player.id, player]));
    for (const player of roster) profiles.set(player.id, player);
    const stats = buildMatchStats(parsed.data, match.events, [...profiles.values()], aliases);
    if (!stats) return failure("Choose a unique play and distinct player profiles for each goal.", 400);
    const updated = { ...match, stats, revision: revision + 1 };
    await put(updated, "revision = :r AND #s = :s",
      { ":r": { N: String(revision) }, ":s": { S: match.status } }, { "#s": "stage" });
    return Response.json({ match: publicMatch(updated, owner) }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    if (error instanceof Error && error.message === "Match not found.") return failure(error.message, 404);
    if (error instanceof Error && error.message.includes("ConditionalCheckFailed")) {
      return failure("This match changed. Refresh before saving stats.", 409);
    }
    return failure("Game stats are temporarily unavailable.", 503);
  }
}

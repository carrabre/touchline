import { summarizeGames } from "@/lib/game-stats";
import { listStatsGames } from "@/lib/shared-games";

export async function GET() {
  try {
    const { roster, aliases } = summarizeGames(await listStatsGames());
    return Response.json({ players: roster, aliases }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ error: "Player profiles are temporarily unavailable." }, { status: 503 });
  }
}

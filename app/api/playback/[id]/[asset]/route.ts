import { get } from "@/lib/aws";
import { isGameId } from "@/lib/game-paths";
import { isPublicMatch } from "@/lib/match-access";
import { mediaResponse } from "@/lib/media-response";

export const maxDuration = 300;

async function playback(request: Request, { params }: { params: Promise<{ id: string; asset: string }> }) {
  const { id, asset } = await params;
  if (!isGameId(id) || (asset !== "reel" && asset !== "source")) return new Response(null, { status: 404 });

  const match = await get(id).catch(() => null);
  if (!match || !isPublicMatch(match) || match.status === "uploading") return new Response(null, { status: 404 });

  const key = asset === "reel" ? match.reelKey : match.key;
  return key ? mediaResponse(request, key) : new Response(null, { status: 404 });
}

export { playback as GET, playback as HEAD };

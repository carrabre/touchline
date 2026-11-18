import { isReviewedGameId } from "@/lib/game-paths";

async function legacyPlayback(request: Request, { params }: { params: Promise<{ id: string; asset: string }> }) {
  const { id, asset } = await params;
  if (!isReviewedGameId(id)) return new Response(null, { status: 404 });
  return Response.redirect(new URL(`/api/playback/${encodeURIComponent(id)}/${encodeURIComponent(asset)}`, request.url), 307);
}

export { legacyPlayback as GET, legacyPlayback as HEAD };

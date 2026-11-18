import { cookies } from "next/headers";
import { REVIEWED_MATCH_ID } from "@/lib/game-paths";
import { mediaResponse } from "@/lib/media-response";
import { hasReviewAccess, REVIEW_COOKIE } from "@/lib/review-access";
import { reviewedMediaKey } from "@/lib/reviewed-goals";

export const maxDuration = 300;

async function playback(request: Request, { params }: { params: Promise<{ id: string; asset: string }> }) {
  const { id, asset } = await params;
  if (id !== REVIEWED_MATCH_ID || !hasReviewAccess((await cookies()).get(REVIEW_COOKIE)?.value)) {
    return new Response(null, { status: 404, headers: { "Cache-Control": "private, no-store" } });
  }
  const key = await reviewedMediaKey(asset).catch(() => null);
  return key ? mediaResponse(request, key) : new Response(null, { status: 404 });
}

export { playback as GET, playback as HEAD };

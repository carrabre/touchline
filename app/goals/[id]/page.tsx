import { notFound, redirect } from "next/navigation";
import { gameHref, isReviewedGameId } from "@/lib/game-paths";

export default async function LegacyGamePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!isReviewedGameId(id)) notFound();
  redirect(gameHref(id));
}

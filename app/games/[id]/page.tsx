import type { Metadata } from "next";
import { cache } from "react";
import { notFound, redirect } from "next/navigation";
import { MatchStudio } from "@/app/components/match-studio";
import { get } from "@/lib/aws";
import { gameHref, isGameId, REVIEWED_MATCH_ID } from "@/lib/game-paths";
import { isPublicMatch, publicMatch } from "@/lib/match-access";

export const dynamic = "force-dynamic";

type PageProps = { params: Promise<{ id: string }> };

const loadGame = cache(async (id: string) => {
  if (!isGameId(id) || id.startsWith("validation-") || id === REVIEWED_MATCH_ID) return null;
  const match = await get(id);
  return match && isPublicMatch(match) ? publicMatch(match, "") : null;
});

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const match = await loadGame(id);
  return {
    title: match ? `${match.title} · Touchline` : "Game · Touchline",
    ...(match ? { description: "Watch the game and its highlights on Touchline." } : {}),
  };
}

export default async function GamePage({ params }: PageProps) {
  const { id } = await params;
  if (id === REVIEWED_MATCH_ID) redirect(gameHref(id));

  const match = await loadGame(id);
  if (!match) notFound();

  return <MatchStudio initialMatch={match} />;
}

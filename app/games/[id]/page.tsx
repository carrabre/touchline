import type { Metadata } from "next";
import { cache } from "react";
import { notFound } from "next/navigation";
import { StatsShell } from "@/app/components/stats-shell";
import { GoalTracker } from "@/app/goals/tracker";
import { loadReviewedMatch, loadReviewedRecord } from "@/lib/reviewed-goals";
import "@/app/goals/tracker.css";
import { MatchStudio } from "@/app/components/match-studio";
import { get } from "@/lib/aws";
import { isGameId, isReviewedGameId } from "@/lib/game-paths";
import { isPublicMatch, publicMatch } from "@/lib/match-access";

export const dynamic = "force-dynamic";

type PageProps = { params: Promise<{ id: string }> };

const loadGame = cache(async (id: string) => {
  if (!isGameId(id) || id.startsWith("validation-") || isReviewedGameId(id)) return null;
  const match = await get(id);
  return match && isPublicMatch(match) ? publicMatch(match, "") : null;
});

const loadReviewed = cache(loadReviewedRecord);

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const match = isReviewedGameId(id) ? await loadReviewed(id) : await loadGame(id);
  return {
    title: match ? `${match.title} · Touchline` : "Game · Touchline",
    ...(match ? { description: "Watch the game and its highlights on Touchline." } : {}),
  };
}

export default async function GamePage({ params }: PageProps) {
  const { id } = await params;
  if (isReviewedGameId(id)) {
    const doc = await loadReviewed(id);
    if (!doc) notFound();
    const match = await loadReviewedMatch(doc);
    return <StatsShell><GoalTracker match={match} /></StatsShell>;
  }

  const match = await loadGame(id);
  if (!match) notFound();

  return <MatchStudio initialMatch={match} />;
}

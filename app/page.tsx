import { redirect } from "next/navigation";
import { listReviewedGames } from "@/lib/shared-games";
import { MatchStudio } from "./components/match-studio";
import { gameHref, isGameId } from "@/lib/game-paths";

export default async function Home({ searchParams }: {
  searchParams: Promise<{ match?: string | string[]; view?: string | string[] }>;
}) {
  const { match, view } = await searchParams;
  if (typeof match === "string" && isGameId(match)) redirect(gameHref(match));

  const reviewedGames = await listReviewedGames().then((games) => games
    .map(({ id, title, date, goals }) => ({ id, title, date, goals: goals.length }))
    .sort((a, b) => Date.parse(b.date) - Date.parse(a.date))).catch(() => []);
  return <MatchStudio reviewedGames={reviewedGames} initialView={view === "new" ? "new" : "library"} />;
}

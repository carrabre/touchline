import { redirect } from "next/navigation";
import { MatchStudio } from "./components/match-studio";
import { gameHref, isGameId } from "@/lib/game-paths";

export default async function Home({ searchParams }: {
  searchParams: Promise<{ match?: string | string[] }>;
}) {
  const { match } = await searchParams;
  if (typeof match === "string" && isGameId(match)) redirect(gameHref(match));

  return <MatchStudio />;
}

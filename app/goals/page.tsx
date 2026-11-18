import { redirect } from "next/navigation";
import { gameHref, REVIEWED_MATCH_ID } from "@/lib/game-paths";

export default function GoalsPage() {
  redirect(gameHref(REVIEWED_MATCH_ID));
}

import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Film, Scissors, Trophy } from "lucide-react";
import { hasReviewAccess, REVIEW_COOKIE } from "@/lib/review-access";
import { loadReviewedMatch } from "@/lib/reviewed-goals";
import { GoalAccess } from "./access";
import { GoalTracker } from "./tracker";
import "./tracker.css";

export const metadata: Metadata = {
  title: "Goal tracker · Touchline",
  robots: { index: false, follow: false },
};

export default async function GoalsPage() {
  const access = hasReviewAccess((await cookies()).get(REVIEW_COOKIE)?.value);
  const match = access ? await loadReviewedMatch().catch(() => null) : null;

  return (
    <div className="shell">
      <aside className="rail" aria-label="Touchline navigation">
        <a className="brand" href="/">
          <span className="brandmark"><Scissors size={22} /></span>
          touchline<span className="brand-period">.</span>
        </a>
        <a className="nav" href="/" aria-label="Match library"><Film size={19} />Match library</a>
        <a className="nav chosen" href="/goals" aria-current="page" aria-label="Goal tracker">
          <Trophy size={19} />Goal tracker
        </a>
      </aside>
      <main className="goal-main">
        <header className="topbar"><span>MATCH STUDIO</span></header>
        {match ? <GoalTracker match={match} /> : access ?
          <div className="pagehead"><div><h1>Goal tracker</h1><p>The match is temporarily unavailable.</p></div></div> :
          <GoalAccess />}
        <footer>TOUCHLINE</footer>
      </main>
    </div>
  );
}

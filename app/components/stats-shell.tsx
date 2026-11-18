import { Film, Trophy } from "lucide-react";
import type { ReactNode } from "react";

export function StatsShell({ leaderboard = false, children }: { leaderboard?: boolean; children: ReactNode }) {
  return (
    <div className="shell">
      <aside className="rail" aria-label="Touchline navigation">
        <a className="brand" href="/">
          <span className="brandmark"><img src="/favicon.svg?v=soccer-2" alt="" width={25} height={25} /></span>
          touchline<span className="brand-period">.</span>
        </a>
        <a className={leaderboard ? "nav" : "nav chosen"} href="/" aria-label="All games"><Film size={19} />All games</a>
        <a className={leaderboard ? "nav chosen" : "nav"} href="/leaderboard" aria-label="Leaderboard" aria-current={leaderboard ? "page" : undefined}>
          <Trophy size={19} />Leaderboard
        </a>
      </aside>
      <main className="goal-main">
        <header className="topbar"><span>TOUCHLINE / MATCH STUDIO</span></header>
        {children}
        <footer>TOUCHLINE</footer>
      </main>
    </div>
  );
}

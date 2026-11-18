import { ArrowLeft } from "lucide-react";

export default function GameNotFound() {
  return <main className="unavailable-game">
    <h1>Game not found</h1>
    <p>This game may have been removed or the link may be incorrect.</p>
    <a className="secondary" href="/"><ArrowLeft size={16} />All games</a>
  </main>;
}

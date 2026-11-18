"use client";

import { useState } from "react";
import { Link2 } from "lucide-react";

export function CopyGameLink({ href }: { href: string }) {
  const [copied, setCopied] = useState(false);
  const [manualUrl, setManualUrl] = useState("");

  async function copy() {
    const url = new URL(href, location.origin).href;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setManualUrl("");
    } catch {
      setCopied(false);
      setManualUrl(url);
    }
  }

  return (
    <div className="copy-game-link">
      <button type="button" className="secondary" onClick={copy}>
        <Link2 size={17} /><span aria-live="polite">{copied ? "Link copied" : "Copy game link"}</span>
      </button>
      {manualUrl && <input aria-label="Game link" readOnly autoFocus value={manualUrl} onFocus={(event) => event.target.select()} />}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

export function GoalAccess() {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const unlock = useCallback(async (accessKey: string) => {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/reviewed-goals/access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: accessKey.trim() }),
      });
      if (response.ok) {
        location.replace(location.pathname);
      } else {
        setError(response.status === 403 ? "That access key did not match." : "The leaderboard is temporarily unavailable.");
      }
    } catch {
      setError("Could not connect. Try again.");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    const fragment = new URLSearchParams(location.hash.slice(1)).get("access");
    if (fragment) {
      history.replaceState(null, "", location.pathname);
      void unlock(fragment);
    }
  }, [unlock]);

  function submit(event: FormEvent) {
    event.preventDefault();
    void unlock(key);
  }

  return <div className="pagehead goal-heading">
    <form className="panel goal-access" onSubmit={submit}>
      <h1>Stats leaderboard</h1>
      <p>Open the private leaderboard with your access key.</p>
      <label className="field">
        Access key
        <input type="password" name="access" autoComplete="off" required maxLength={90}
          value={key} onChange={(event) => setKey(event.target.value)} disabled={busy} />
      </label>
      {error && <p role="alert">{error}</p>}
      <button className="primary" disabled={busy} type="submit">{busy ? "Opening…" : "Open leaderboard"}</button>
    </form>
  </div>;
}

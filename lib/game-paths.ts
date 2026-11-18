export const REVIEWED_MATCH_ID = "reviewed-2026-11-16-indoor";

export function isGameId(id: string): boolean {
  return /^[A-Za-z0-9_-]{1,128}$/.test(id);
}

export function gameHref(id: string): string {
  return `/${id === REVIEWED_MATCH_ID ? "goals" : "games"}/${encodeURIComponent(id)}`;
}

export function gameIdFromPath(pathname: string): string | null {
  const id = /^\/games\/([^/]+)\/?$/.exec(pathname)?.[1];
  return id && isGameId(id) ? id : null;
}

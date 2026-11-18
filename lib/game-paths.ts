export function isGameId(id: string): boolean {
  return /^[A-Za-z0-9_-]{1,128}$/.test(id);
}

export function isReviewedGameId(id: string): boolean {
  return id.startsWith("reviewed-") && isGameId(id);
}

export function gameHref(id: string): string {
  return `/games/${encodeURIComponent(id)}`;
}

export function gameIdFromPath(pathname: string): string | null {
  const id = /^\/games\/([^/]+)\/?$/.exec(pathname)?.[1];
  return id && isGameId(id) ? id : null;
}

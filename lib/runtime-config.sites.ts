import { env } from 'cloudflare:workers';
export function runtimeConfig(): Record<string, string | undefined> {
  return env as unknown as Record<string, string>;
}
export function requestOwner(request: Request): string | null {
  return request.headers.get('oai-authenticated-user-id');
}

import type { Match } from './aws';

export function isPublicMatch(match: Match): boolean {
  return match.status !== 'discarded' && !match.id.startsWith('validation-');
}
export function publicMatch(match: Match, owner: string) {
  const { owner: uploader, key, uploadId, metrics, ...details } = match;
  return { ...details, canEdit: uploader === owner };
}

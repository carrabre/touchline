import type { Match } from './aws';

// Keep previous game links working while removing the old entries from the shared library.
const unlistedMatchIds = new Set([
  '66850c8ca9ff0445856fef8cd1424bca', // YouTube import
  'daf390518e04ab394d97f6e71c774ea8', // Baltijos vs Džiugas
  '7828de3bb1f20aea08f578c91ed531d2', // Campeonato
  '7067ca2868ed18a1a053a75b1f8980cf', // Background completion verification
  '3828c97c106f64c5219227d571e4bbf8', // Background transfer verification
  '6a5e48e04b0ad9af7269ad3c1507a0e8', // IMG_6349 review
  '7f2b396e868ac316df852dea3df658cb', // Lexington verification
  '9ce7abe60314133366d91377bc592a85', // Wilmington verification
  '43012324f1f6e9588a95646823d830a7', // Winchester verification
  '6b03387d097bc99603286104097ea2ab', // Three-goal sample
  'b59c08433fb990da01d8d150a7cbe7f2', // Three-goal sample
]);

export function isPublicMatch(match: Match): boolean {
  return match.status !== 'discarded' && match.status !== 'reviewed' && !match.id.startsWith('validation-');
}
export function isLibraryMatch(match: Match): boolean {
  return isPublicMatch(match) && !unlistedMatchIds.has(match.id);
}

export function publicMatch(match: Match, owner: string) {
  const { owner: uploader, key, uploadId, metrics, ...details } = match;
  return { ...details, canEdit: uploader === owner };
}

export type PublicMatch = ReturnType<typeof publicMatch>;

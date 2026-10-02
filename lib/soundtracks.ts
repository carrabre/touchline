import catalog from '../worker/tracks/catalog.json';
export const soundtracks = catalog;
export const musicChoices = new Set(['random', ...catalog.map(track => track.id)]);

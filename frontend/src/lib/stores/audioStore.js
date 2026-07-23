import { writable } from 'svelte/store';

export const currentTrack = writable(null); // { title: '', audioUrl: '', feedTitle: '' }
export const isPlaying = writable(false);
export const playbackTime = writable(0);
export const duration = writable(0);

export const selectedVoice = writable(localStorage.getItem('vos_podcast_voice') || 'marie');

export function sanitizeTextForSpeech(text) {
  if (!text) return "";
  let clean = text.replace(/<[^>]+>/g, ' ');
  clean = clean.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  clean = clean.replace(/https?:\/\/\S+/gi, '');
  clean = clean.replace(/www\.\S+/gi, '');
  clean = clean.replace(/[a-zA-Z0-9.-]+\.(?:com|ch|fr|net|org|html|php)\S*/gi, '');
  clean = clean.replace(/Suisse\s*-\s*Radio\s*Télévision\s*Suisse\s*:\s*/gi, '');
  return clean.replace(/\s+/g, ' ').trim();
}

export function playTrack(title, audioUrl, feedTitle = 'Vos Podcast') {
  currentTrack.set({ title, audioUrl, feedTitle });
  isPlaying.set(true);
}

export function saveVoiceSetting(voiceKey) {
  selectedVoice.set(voiceKey);
  localStorage.setItem('vos_podcast_voice', voiceKey);
}

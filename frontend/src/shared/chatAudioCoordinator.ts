/**
 * Один активный <audio> в чатах: при старте воспроизведения остальные ставим на pause.
 */
let currentPlaying: HTMLAudioElement | null = null;

export function notifyChatAudioPlay(el: HTMLAudioElement): void {
  if (currentPlaying && currentPlaying !== el) {
    try {
      currentPlaying.pause();
    } catch {
      /* ignore */
    }
  }
  currentPlaying = el;
}

export function notifyChatAudioStopped(el: HTMLAudioElement): void {
  if (currentPlaying === el) {
    currentPlaying = null;
  }
}

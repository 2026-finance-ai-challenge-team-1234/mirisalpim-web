// 앱 전체가 공유하는 오디오 요소 하나.
//
// ⚠️ 모바일 브라우저는 사용자 탭 핸들러 안에서 시작되지 않은 play() 를 막는다
// (데스크톱 Chrome 은 Media Engagement Index 때문에 그냥 통과시켜서 모바일에서만 드러난다).
// 게다가 iOS 의 잠금 해제는 "요소 단위"라, 문장마다 new Audio() 를 새로 만들면 앞
// 문장이 재생됐더라도 다음 문장은 다시 막힌다 - 스피커를 껐다 켤 때만 한 번씩
// 들리던 증상이 이것이었다.
//
// 그래서 요소를 하나만 만들어 두고, 사용자 제스처에서 unlockAudio() 로 한 번 열어둔 뒤
// 이후에는 src 만 갈아 끼운다. 한 번 열린 요소는 제스처 밖에서도 재생할 수 있다.

//: 잠금 해제용 10ms 무음 WAV. 소리가 나면 안 되므로 전 구간이 0 이다.
const SILENT_WAV =
  "data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

let player = null;
let unlocked = false;

/** 공유 오디오 요소. 없으면 만든다. */
export function getAudioPlayer() {
  if (!player) {
    player = new Audio();
    player.preload = "auto";
  }
  return player;
}

export function isAudioUnlocked() {
  return unlocked;
}

/**
 * 자동 재생 잠금을 푼다. **반드시 사용자 제스처(탭/클릭) 핸들러 안에서** 동기적으로 불러야 한다.
 *
 * 성공 여부를 boolean 으로 돌려주되 예외는 던지지 않는다 - 실패해도 자막으로 진행하면 되고,
 * 호출부가 매번 catch 를 달 이유가 없다.
 */
export function unlockAudio() {
  if (unlocked) return Promise.resolve(true);

  const el = getAudioPlayer();
  el.src = SILENT_WAV;
  let started;
  try {
    started = el.play();
  } catch {
    return Promise.resolve(false);
  }
  // 구형 브라우저는 play() 가 Promise 를 돌려주지 않는다.
  if (!started || typeof started.then !== "function") {
    unlocked = true;
    return Promise.resolve(true);
  }
  return started
    .then(() => {
      el.pause();
      el.currentTime = 0;
      unlocked = true;
      return true;
    })
    .catch(() => false);
}

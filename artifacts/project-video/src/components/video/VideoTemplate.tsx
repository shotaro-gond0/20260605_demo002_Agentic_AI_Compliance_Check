import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useVideoPlayer } from '@/lib/video';
import { Scene1 } from './video_scenes/Scene1';
import { Scene2 } from './video_scenes/Scene2';
import { Scene3 } from './video_scenes/Scene3';
import { Scene4 } from './video_scenes/Scene4';
import { Scene5 } from './video_scenes/Scene5';

export const SCENE_DURATIONS: Record<string, number> = {
  intro: 4000,
  upload: 4500,
  extract: 5000,
  risk: 5000,
  report: 4500,
};

const SCENE_COMPONENTS: Record<string, React.ComponentType> = {
  intro: Scene1,
  upload: Scene2,
  extract: Scene3,
  risk: Scene4,
  report: Scene5,
};

const SCENE_START_SEC: Record<string, number> = (() => {
  const out: Record<string, number> = {};
  let cumulativeMs = 0;
  for (const [key, ms] of Object.entries(SCENE_DURATIONS)) {
    out[key] = cumulativeMs / 1000;
    cumulativeMs += ms;
  }
  return out;
})();

const AUDIO_SEEK_EPSILON_SEC = 0.18;

export default function VideoTemplate({
  durations = SCENE_DURATIONS,
  loop = true,
  muted = false,
  onSceneChange,
}: {
  durations?: Record<string, number>;
  loop?: boolean;
  muted?: boolean;
  onSceneChange?: (sceneKey: string) => void;
} = {}) {
  const { currentScene, currentSceneKey } = useVideoPlayer({ durations, loop });

  useEffect(() => {
    onSceneChange?.(currentSceneKey);
  }, [currentSceneKey, onSceneChange]);

  const baseSceneKey = currentSceneKey.replace(/_r[12]$/, '') as keyof typeof SCENE_DURATIONS;
  const sceneIndex = Object.keys(SCENE_DURATIONS).indexOf(baseSceneKey);
  const SceneComponent = SCENE_COMPONENTS[baseSceneKey];

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.volume = 0.45;
    const targetTime = SCENE_START_SEC[baseSceneKey] ?? 0;
    if (Math.abs(audio.currentTime - targetTime) > AUDIO_SEEK_EPSILON_SEC) {
      audio.currentTime = targetTime;
    }
    audio.play().catch(() => {});
  }, [currentSceneKey, baseSceneKey, muted]);

  return (
    <div className="w-full h-screen overflow-hidden relative bg-black font-body text-white">
      {/* Persistent Background */}
      <div className="absolute inset-0 z-0">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url(${import.meta.env.BASE_URL}images/tech-bg.png)`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />

        {/* Animated grid lines */}
        <motion.div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage:
              'linear-gradient(rgba(0, 240, 255, 0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 240, 255, 0.2) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
          animate={{ y: [0, 40], x: [0, 40] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        />

        {/* Drifting glow */}
        <motion.div
          className="absolute w-[80vw] h-[80vh] rounded-full blur-[120px] opacity-10"
          style={{ background: 'radial-gradient(circle, #00f0ff, transparent 60%)' }}
          animate={{
            x: sceneIndex % 2 === 0 ? '10vw' : '40vw',
            y: sceneIndex % 2 === 0 ? '10vh' : '-20vh',
            scale: sceneIndex === 3 ? 1.5 : 1,
          }}
          transition={{ duration: 4, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute w-[60vw] h-[60vh] rounded-full blur-[100px] opacity-10"
          style={{ background: 'radial-gradient(circle, #39ff14, transparent 60%)' }}
          animate={{
            x: sceneIndex % 2 === 1 ? '50vw' : '80vw',
            y: sceneIndex % 2 === 1 ? '50vh' : '80vh',
            scale: sceneIndex === 4 ? 2 : 1,
          }}
          transition={{ duration: 5, ease: 'easeInOut' }}
        />
      </div>

      <AnimatePresence mode="popLayout">
        {SceneComponent && <SceneComponent key={currentSceneKey} />}
      </AnimatePresence>

      <audio
        ref={audioRef}
        src={`${import.meta.env.BASE_URL}audio/bg_music.mp3`}
        preload="auto"
        autoPlay
        muted={muted}
      />
    </div>
  );
}

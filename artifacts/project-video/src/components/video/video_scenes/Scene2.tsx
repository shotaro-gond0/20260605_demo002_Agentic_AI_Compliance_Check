import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export function Scene2() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 1000),
      setTimeout(() => setPhase(3), 1800),
      setTimeout(() => setPhase(4), 3800),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  const docs = ['Word', 'PDF', 'TXT'];

  return (
    <motion.div 
      className="absolute inset-0 flex items-center justify-between px-[10vw] z-10"
      initial={{ opacity: 0, x: 50 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, scale: 0.9, filter: 'blur(20px)' }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="w-1/2">
        <motion.div
          className="font-mono text-primary text-[1.2vw] mb-4 uppercase"
          initial={{ opacity: 0, x: -20 }}
          animate={phase >= 1 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
        >
          &gt; Step 01: Data Input
        </motion.div>
        
        <motion.h2 
          className="text-[3.5vw] font-bold leading-tight mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ delay: 0.1 }}
        >
          Upload Document<br/>
          <span className="text-secondary-foreground text-[2vw]">議事録ファイルをアップロード</span>
        </motion.h2>

        <div className="flex gap-4">
          {docs.map((doc, i) => (
            <motion.div
              key={doc}
              className="px-6 py-2 border border-primary/30 rounded-full font-mono text-[1vw] text-primary bg-primary/5"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={phase >= 2 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
              transition={{ delay: i * 0.1, type: "spring" }}
            >
              .{doc.toLowerCase()}
            </motion.div>
          ))}
        </div>
      </div>

      <div className="w-[35vw] h-[35vw] relative flex items-center justify-center">
        <motion.div 
          className="absolute inset-0 border-[1px] border-primary/20 rounded-full border-dashed"
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div 
          className="absolute inset-[10%] border-[1px] border-accent/20 rounded-full"
          animate={{ rotate: -360 }}
          transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
        />

        <motion.div
          className="w-[15vw] h-[20vw] bg-[#111] border border-primary/40 rounded-lg flex flex-col items-center justify-center relative overflow-hidden"
          initial={{ opacity: 0, y: 50, rotateX: 30 }}
          animate={phase >= 3 ? { opacity: 1, y: 0, rotateX: 0 } : { opacity: 0, y: 50, rotateX: 30 }}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        >
          <motion.div 
            className="absolute bottom-0 left-0 w-full bg-primary/20"
            initial={{ height: "0%" }}
            animate={phase >= 3 ? { height: "100%" } : { height: "0%" }}
            transition={{ delay: 0.5, duration: 1.5, ease: "easeInOut" }}
          />
          <div className="font-mono text-primary text-[3vw] z-10">DOC</div>
          <div className="font-mono text-xs text-white/50 z-10 mt-2">UPLOADING...</div>
        </motion.div>
      </div>
    </motion.div>
  );
}

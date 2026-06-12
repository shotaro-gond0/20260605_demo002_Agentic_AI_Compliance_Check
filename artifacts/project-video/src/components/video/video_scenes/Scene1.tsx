import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export function Scene1() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1200),
      setTimeout(() => setPhase(3), 2000),
      setTimeout(() => setPhase(4), 3500),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10"
      initial={{ opacity: 0, scale: 1.1 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, y: -50, filter: 'blur(10px)' }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="text-center relative">
        <motion.div
          className="font-mono text-primary text-[1.5vw] mb-4 tracking-widest uppercase opacity-80"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 0.8, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ duration: 0.6 }}
        >
          // INITIALIZING_SYSTEM
        </motion.div>

        <div className="overflow-hidden mb-6">
          <motion.h1 
            className="text-[4vw] font-black leading-tight"
            initial={{ y: "100%" }}
            animate={phase >= 2 ? { y: "0%" } : { y: "100%" }}
            transition={{ type: "spring", stiffness: 100, damping: 20 }}
          >
            Agentic AI
          </motion.h1>
          <motion.h1 
            className="text-[4vw] font-black leading-tight text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent"
            initial={{ y: "100%" }}
            animate={phase >= 2 ? { y: "0%" } : { y: "100%" }}
            transition={{ type: "spring", stiffness: 100, damping: 20, delay: 0.1 }}
          >
            Compliance Check Tool
          </motion.h1>
        </div>

        <motion.div
          className="flex justify-center items-center gap-4 mt-8"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={phase >= 3 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
          transition={{ duration: 0.6, type: "spring", bounce: 0.4 }}
        >
          <div className="h-[2px] w-12 bg-primary"></div>
          <span className="font-mono text-[1.2vw] text-accent tracking-wider uppercase">
            Risk Assessment Automated
          </span>
          <div className="h-[2px] w-12 bg-primary"></div>
        </motion.div>
      </div>
      
      {/* Decorative scanner line */}
      <motion.div 
        className="absolute top-0 left-0 w-full h-[2px] bg-primary opacity-50 shadow-[0_0_15px_#00f0ff]"
        animate={{ top: ['0%', '100%'] }}
        transition={{ duration: 3, ease: 'linear', repeat: Infinity }}
      />
    </motion.div>
  );
}

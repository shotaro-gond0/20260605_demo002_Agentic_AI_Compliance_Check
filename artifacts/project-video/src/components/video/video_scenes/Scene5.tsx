import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export function Scene5() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 500),
      setTimeout(() => setPhase(2), 1200),
      setTimeout(() => setPhase(3), 2000),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, filter: 'blur(20px)' }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <motion.div
        className="mb-8 relative"
        initial={{ scale: 0, rotate: -180 }}
        animate={phase >= 1 ? { scale: 1, rotate: 0 } : { scale: 0, rotate: -180 }}
        transition={{ type: "spring", stiffness: 200, damping: 20 }}
      >
        <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 border border-primary/50 flex items-center justify-center shadow-[0_0_40px_rgba(0,240,255,0.3)]">
          <img 
            src={`${import.meta.env.BASE_URL}images/secure-lock.png`} 
            alt="Secure Lock" 
            className="w-20 h-20 object-contain drop-shadow-[0_0_10px_#39ff14]"
          />
        </div>
      </motion.div>

      <div className="text-center">
        <motion.div
          className="font-mono text-primary text-[1.2vw] mb-4 uppercase"
          initial={{ opacity: 0 }}
          animate={phase >= 2 ? { opacity: 1 } : { opacity: 0 }}
        >
          &gt; Step 04: Report Generation
        </motion.div>
        
        <motion.h2 
          className="text-[4vw] font-black leading-tight mb-4"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 2 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        >
          PDF Report Output<br/>
          <span className="text-secondary-foreground text-[2vw]">日本語PDFレポートを出力</span>
        </motion.h2>

        <motion.div
          className="mt-8"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={phase >= 3 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.9 }}
        >
          <div className="inline-block px-8 py-3 bg-white text-black font-bold font-mono text-[1.5vw] tracking-wider relative overflow-hidden">
            <motion.div 
              className="absolute inset-0 bg-accent mix-blend-multiply"
              animate={{ x: ['-100%', '100%'] }}
              transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            />
            STAY COMPLIANT.
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}

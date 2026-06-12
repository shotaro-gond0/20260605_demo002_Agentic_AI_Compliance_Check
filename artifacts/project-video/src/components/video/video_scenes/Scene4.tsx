import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export function Scene4() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 1200),
      setTimeout(() => setPhase(3), 2000),
      setTimeout(() => setPhase(4), 2800),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  return (
    <motion.div 
      className="absolute inset-0 flex items-center px-[10vw] justify-between z-10"
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, scale: 1.1, filter: 'blur(20px)' }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="w-1/2">
        <motion.div
          className="font-mono text-warning text-[1.2vw] mb-4 uppercase"
          initial={{ opacity: 0, x: -20 }}
          animate={phase >= 1 ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
        >
          &gt; Step 03: Compliance Engine
        </motion.div>
        
        <motion.h2 
          className="text-[3.5vw] font-bold leading-tight mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ delay: 0.1 }}
        >
          EU AI Act<br/>Risk Assessment<br/>
          <span className="text-secondary-foreground text-[2vw]">リスクレベルを自動判定</span>
        </motion.h2>

        <motion.div 
          className="mt-8 font-mono text-[1.5vw] text-white/70"
          initial={{ opacity: 0 }}
          animate={phase >= 2 ? { opacity: 1 } : { opacity: 0 }}
        >
          Analyzing parameters against EU regulatory framework...
        </motion.div>
      </div>

      <div className="w-[40vw]">
        <div className="bg-[#111] border border-white/10 rounded-xl p-8 shadow-2xl relative overflow-hidden">
          {/* Scanner effect over card */}
          {phase >= 2 && phase < 4 && (
            <motion.div 
              className="absolute left-0 right-0 h-[2px] bg-primary shadow-[0_0_10px_#00f0ff] z-20"
              initial={{ top: '0%' }}
              animate={{ top: '100%' }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            />
          )}

          <div className="space-y-6">
            <div>
              <div className="flex justify-between font-mono text-[1vw] mb-2 text-white/50">
                <span>RISK LEVEL SCAN</span>
                <span>STATUS</span>
              </div>
              
              {/* Risk Meter */}
              <div className="h-4 bg-black rounded-full overflow-hidden flex">
                <motion.div 
                  className="h-full bg-error"
                  initial={{ width: '0%' }}
                  animate={phase >= 2 ? { width: '10%' } : { width: '0%' }}
                  transition={{ duration: 0.5 }}
                />
                <motion.div 
                  className="h-full bg-warning"
                  initial={{ width: '0%' }}
                  animate={phase >= 2 ? { width: '30%' } : { width: '0%' }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                />
                <motion.div 
                  className="h-full bg-accent"
                  initial={{ width: '0%' }}
                  animate={phase >= 3 ? { width: '60%' } : { width: '0%' }}
                  transition={{ duration: 1, delay: 0.5, type: 'spring' }}
                />
              </div>
            </div>

            {/* Assessment Results */}
            <motion.div 
              className="p-4 rounded bg-black/50 border border-white/5"
              initial={{ opacity: 0, y: 20 }}
              animate={phase >= 3 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full border-2 border-accent flex items-center justify-center">
                  <motion.div 
                    className="w-6 h-6 bg-accent rounded-full"
                    animate={phase >= 4 ? { scale: [1, 1.2, 1] } : { scale: 0 }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                </div>
                <div>
                  <div className="font-mono text-accent text-[1.5vw] font-bold">MINIMAL RISK</div>
                  <div className="text-[1vw] text-white/50">No prohibited practices detected.</div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

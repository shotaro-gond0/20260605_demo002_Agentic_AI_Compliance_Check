import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

export function Scene3() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 400),
      setTimeout(() => setPhase(2), 1000),
      setTimeout(() => setPhase(3), 1500),
      setTimeout(() => setPhase(4), 4200),
    ];
    return () => timers.forEach(t => clearTimeout(t));
  }, []);

  const nodes = [
    "AI Purpose",
    "Data Types",
    "Target Users",
    "Integration",
    "Automation",
    "Decision Mkg"
  ];

  return (
    <motion.div 
      className="absolute inset-0 flex flex-col items-center justify-center z-10"
      initial={{ opacity: 0, scale: 1.2, filter: 'blur(20px)' }}
      animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
      exit={{ opacity: 0, y: -50 }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="text-center mb-12">
        <motion.div
          className="font-mono text-accent text-[1.2vw] mb-4 uppercase"
          initial={{ opacity: 0, y: -20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: -20 }}
        >
          &gt; Step 02: LangGraph Processing
        </motion.div>
        
        <motion.h2 
          className="text-[3.5vw] font-bold leading-tight"
          initial={{ opacity: 0, y: 20 }}
          animate={phase >= 1 ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
          transition={{ delay: 0.1 }}
        >
          Extracting 6 Parameters<br/>
          <span className="text-secondary-foreground text-[2vw]">AIアプリの情報を6項目抽出</span>
        </motion.h2>
      </div>

      <div className="relative w-[60vw] h-[30vh]">
        {/* Central Core */}
        <motion.div 
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-accent rounded-full shadow-[0_0_30px_#39ff14] z-20 flex items-center justify-center font-mono text-black font-bold"
          initial={{ scale: 0 }}
          animate={phase >= 2 ? { scale: 1 } : { scale: 0 }}
          transition={{ type: "spring", bounce: 0.5 }}
        >
          AI
        </motion.div>

        {/* Nodes */}
        {nodes.map((node, i) => {
          const angle = (i * 60) * (Math.PI / 180);
          const radiusX = 350;
          const radiusY = 150;
          const x = Math.cos(angle) * radiusX;
          const y = Math.sin(angle) * radiusY;

          return (
            <motion.div key={i}>
              {/* Connecting Line */}
              {phase >= 3 && (
                <svg className="absolute inset-0 w-full h-full pointer-events-none z-0 overflow-visible" style={{ left: '50%', top: '50%' }}>
                  <motion.line 
                    x1="0" y1="0" 
                    x2={x} y2={y} 
                    stroke="rgba(57, 255, 20, 0.4)" 
                    strokeWidth="2"
                    initial={{ strokeDasharray: 400, strokeDashoffset: 400 }}
                    animate={{ strokeDashoffset: 0 }}
                    transition={{ duration: 0.8, delay: i * 0.1 }}
                  />
                </svg>
              )}
              
              {/* Node Label */}
              <motion.div
                className="absolute flex items-center justify-center bg-black border border-accent text-white font-mono text-[1vw] px-4 py-2 rounded shadow-[0_0_10px_rgba(57,255,20,0.2)] z-10 whitespace-nowrap"
                style={{ 
                  left: `calc(50% + ${x}px)`, 
                  top: `calc(50% + ${y}px)`,
                  transform: 'translate(-50%, -50%)'
                }}
                initial={{ opacity: 0, scale: 0 }}
                animate={phase >= 3 ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0 }}
                transition={{ type: "spring", delay: 0.4 + (i * 0.1) }}
              >
                {node}
              </motion.div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

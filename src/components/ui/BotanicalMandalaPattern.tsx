import React from 'react';

export const BotanicalMandalaPattern = () => {
  const mainPetals = Array.from({ length: 16 }).map((_, i) => (
    <g key={`main-${i}`} transform={`rotate(${i * 22.5} 150 0)`}>
       {/* Botanical leaf */}
       <path d="M 150 0 C 165 30, 160 70, 150 90 C 140 70, 135 30, 150 0 Z" fill="currentColor" opacity="0.08" />
       {/* Stem/vein */}
       <line x1="150" y1="15" x2="150" y2="75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.25" />
    </g>
  ));

  const secondaryLeaves = Array.from({ length: 16 }).map((_, i) => (
    <g key={`sec-${i}`} transform={`rotate(${i * 22.5 + 11.25} 150 0)`}>
       {/* Geometric overlapping petal */}
       <path d="M 150 40 C 158 55, 155 75, 150 85 C 145 75, 142 55, 150 40 Z" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.25" />
       {/* Small accent dot */}
       <circle cx="150" cy="100" r="2.5" fill="currentColor" opacity="0.4" />
    </g>
  ));

  const outerArcs = Array.from({ length: 32 }).map((_, i) => (
    <g key={`outer-${i}`} transform={`rotate(${i * 11.25} 150 0)`}>
       {/* Outer rays */}
       <path d="M 150 120 L 150 135" stroke="currentColor" strokeWidth="1.5" opacity="0.2" strokeLinecap="round" />
       <circle cx="150" cy="145" r="1.5" fill="currentColor" opacity="0.35" />
       {/* Tiny digital/tech scanning arc fragment */}
       <path d="M 148 160 A 160 160 0 0 1 152 160" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.4" />
    </g>
  ));

  const backgroundRings = (
    <>
      <circle cx="150" cy="0" r="40" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.15" />
      <circle cx="150" cy="0" r="90" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 6" fill="none" opacity="0.3" />
      <circle cx="150" cy="0" r="120" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.1" />
      <circle cx="150" cy="0" r="160" stroke="currentColor" strokeWidth="1.5" strokeDasharray="1 10" fill="none" opacity="0.4" />
      <circle cx="150" cy="0" r="210" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.05" />
    </>
  );

  return (
    <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden -mx-4 px-4 sm:mx-0 sm:px-0">
      {/* Background Soft Glows for Depth */}
      <div className="absolute -top-32 right-10 w-96 h-96 bg-primary rounded-full blur-[120px] opacity-[0.15]" />
      <div className="absolute top-0 -left-20 w-72 h-72 bg-primary-light rounded-full blur-[100px] opacity-[0.15]" />

      {/* SVG Mandala */}
      <svg 
        className="absolute top-0 left-0 w-full h-[280px] text-primary"
        viewBox="0 0 300 280"
        preserveAspectRatio="xMidYMin slice"
        style={{ 
          maskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.85) 45%, transparent 95%)', 
          WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.85) 45%, transparent 95%)' 
        }}
      >
        {/* Main Central Mandala */}
        {backgroundRings}
        {mainPetals}
        {secondaryLeaves}
        {outerArcs}
        
        {/* Secondary Corner Mandalas for layered depth */}
        <g transform="translate(360, -20) scale(0.6)">
           {backgroundRings}
           {mainPetals}
           {secondaryLeaves}
        </g>
        <g transform="translate(-80, 20) scale(0.4) rotate(45)">
           {backgroundRings}
           {mainPetals}
           {outerArcs}
        </g>
      </svg>
    </div>
  );
};

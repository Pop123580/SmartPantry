import { Leaf } from 'lucide-react';

const AuthMandalaBg = () => {
  const petals = Array.from({ length: 12 }).map((_, i) => (
    <g key={`petal-${i}`} transform={`rotate(${i * 30} 50 50)`}>
       <path d="M 50 50 C 65 75, 60 110, 50 130 C 40 110, 35 75, 50 50 Z" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.15" />
       <circle cx="50" cy="140" r="1.5" fill="currentColor" opacity="0.4" />
    </g>
  ));

  return (
    <svg className="absolute w-[180%] h-[180%] text-primary opacity-[0.2]" 
         style={{ maskImage: 'radial-gradient(circle at center, rgba(0,0,0,1) 0%, rgba(0,0,0,0.6) 40%, transparent 80%)' }}
         viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice">
       <circle cx="50" cy="50" r="20" stroke="currentColor" strokeWidth="0.5" strokeDasharray="1 3" fill="none" opacity="0.4" />
       <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth="0.5" fill="none" opacity="0.1" />
       <circle cx="50" cy="50" r="60" stroke="currentColor" strokeWidth="1" strokeDasharray="2 6" fill="none" opacity="0.3" />
       {petals}
    </svg>
  );
};

export const AuthIllustration = () => (
  <div className="absolute inset-0 overflow-hidden flex items-center justify-center bg-background hidden md:flex">
    <div className="absolute top-10 left-10 w-64 h-64 bg-primary rounded-full blur-[100px] opacity-20" />
    <div className="absolute bottom-10 right-10 w-80 h-80 bg-primary-light rounded-full blur-[120px] opacity-15" />
    
    <AuthMandalaBg />
    
    <div className="relative z-10 flex flex-col items-center justify-center p-8 text-center max-w-sm">
       <div className="w-24 h-24 bg-primary text-white rounded-[1.5rem] flex items-center justify-center shadow-[6px_6px_0_var(--neo-shadow)] border-2 border-neo-border rotate-[-6deg] mb-8">
         <Leaf className="w-12 h-12" />
       </div>
       <h2 className="text-4xl lg:text-5xl font-black text-text mb-4 drop-shadow-sm uppercase tracking-tight">SmartPantry</h2>
       <p className="text-xl font-bold text-muted">Your kitchen, smarter. Fresh food, zero waste.</p>
    </div>
  </div>
);

export const MobileAuthHeader = ({ title, subtitle }: { title: string, subtitle: string }) => (
  <div className="md:hidden relative w-full h-52 overflow-hidden bg-background flex flex-col items-center justify-center border-b-2 border-neo-border/10 mb-6 shrink-0 rounded-b-[2rem]">
    <div className="absolute -top-10 -left-10 w-48 h-48 bg-primary rounded-full blur-[60px] opacity-20" />
    <div className="absolute bottom-0 right-0 w-48 h-48 bg-primary-light rounded-full blur-[80px] opacity-15" />
    
    <AuthMandalaBg />
    
    <div className="relative z-10 flex flex-col items-center mt-2">
      <div className="w-14 h-14 bg-primary text-white rounded-[1.25rem] flex items-center justify-center shadow-[4px_4px_0_var(--neo-shadow)] border-2 border-neo-border rotate-[-4deg] mb-3">
         <Leaf className="w-7 h-7" />
      </div>
      <h1 className="text-2xl font-black text-text drop-shadow-sm tracking-tight">{title}</h1>
      <p className="text-muted font-bold text-sm mt-1">{subtitle}</p>
    </div>
  </div>
);

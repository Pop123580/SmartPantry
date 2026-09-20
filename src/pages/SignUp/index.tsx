import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, Loader2, Mail, Lock, User } from 'lucide-react';
import { AuthIllustration, MobileAuthHeader } from '../Login/AuthIllustration';
import { useTheme } from '../../hooks/useTheme';
import { useAuth } from '../../hooks/useAuth';

export function SignUp() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { signup, googleLogin, error: authError } = useAuth();
  useTheme();

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!name) {
      setError('Enter your full name');
      return;
    }
    if (!email) {
      setError('Enter your email');
      return;
    }
    if (!password) {
      setError('Enter your password');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    
    setLoading(true);
    const ok = await signup(name, email, password);
    setLoading(false);
    if (ok) {
      navigate('/');
    } else {
      setError(authError || 'Could not create account');
    }
  };

  const handleGoogleAuth = () => {
  setError('');
  setLoading(true);

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  if (!clientId) {
    setError('Google authentication is not configured');
    setLoading(false);
    return;
  }

  if (!window.google) {
    setError('Google authentication is still loading. Please try again.');
    setLoading(false);
    return;
  }

  window.google.accounts.id.initialize({
    client_id: clientId,
    callback: async (response) => {
      const ok = await googleLogin(response.credential);

      setLoading(false);

      if (ok) {
        navigate('/');
      } else {
        setError(authError || 'Google authentication failed');
      }
    },
  });

  window.google.accounts.id.prompt();
};

  return (
    <div className="min-h-[100dvh] w-full flex flex-col md:flex-row bg-background font-sans overflow-x-hidden">
      
      {/* Desktop Illustration (Hidden on mobile) */}
      <div className="hidden md:block md:w-1/2 lg:w-3/5 relative border-r-2 border-neo-border/10">
        <AuthIllustration />
      </div>

      {/* Form Section */}
      <div className="w-full md:w-1/2 lg:w-2/5 flex flex-col min-h-[100dvh] md:min-h-0">
        <MobileAuthHeader title="Join SmartPantry" subtitle="Create your household account" />
        
        <div className="flex-1 flex flex-col justify-start md:justify-center px-5 md:px-12 lg:px-16 pb-8 md:pb-12 pt-2 md:pt-0 w-full max-w-md mx-auto md:max-w-none">
          <div className="hidden md:block mb-8">
            <h1 className="text-4xl font-black text-text tracking-tight mb-2">Sign Up</h1>
            <p className="text-muted font-bold text-lg">Start managing your kitchen today.</p>
          </div>
          
          {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded-[1.25rem] border-2 border-red-200 font-bold mb-5 text-sm flex items-center">
              {error}
            </div>
          )}

          <form onSubmit={handleSignUp} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-black text-text uppercase tracking-wider ml-1">Full Name</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted z-10" />
                <input 
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ajay"
                  className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-neo-border shadow-[3px_3px_0_var(--neo-shadow)] rounded-[1.25rem] focus:outline-none focus:ring-4 focus:ring-primary-soft font-bold text-text placeholder:text-muted transition-all"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-black text-text uppercase tracking-wider ml-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted z-10" />
                <input 
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full pl-12 pr-4 py-3.5 bg-white border-2 border-neo-border shadow-[3px_3px_0_var(--neo-shadow)] rounded-[1.25rem] focus:outline-none focus:ring-4 focus:ring-primary-soft font-bold text-text placeholder:text-muted transition-all"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-black text-text uppercase tracking-wider ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted z-10" />
                <input 
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-12 pr-12 py-3.5 bg-white border-2 border-neo-border shadow-[3px_3px_0_var(--neo-shadow)] rounded-[1.25rem] focus:outline-none focus:ring-4 focus:ring-primary-soft font-bold text-text placeholder:text-muted transition-all"
                  disabled={loading}
                />
                <button 
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 p-1 text-muted hover:text-text transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="neo-button w-full py-4 text-lg mt-4 flex items-center justify-center disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 relative flex items-center justify-center">
             <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t-2 border-neo-border/10"></div>
             </div>
             <div className="relative bg-background px-4 text-sm font-black text-muted uppercase tracking-widest">
                or
             </div>
          </div>

          <button 
             type="button"
             disabled={loading}
             onClick={handleGoogleAuth}
             className="w-full mt-6 py-4 bg-white border-2 border-neo-border shadow-[3px_3px_0_var(--neo-shadow)] rounded-[1.25rem] font-bold text-text hover:bg-gray-50 flex items-center justify-center gap-3 transition-all active:translate-y-1 active:shadow-none disabled:opacity-70"
          >
             <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
             </svg>
             Continue with Google
          </button>

          <div className="mt-8 text-center pb-safe">
            <p className="text-muted font-bold text-sm md:text-base">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:text-primary-dark hover:underline">
                Log In
              </Link>
            </p>
          </div>
        </div>
      </div>

    </div>
  );
}

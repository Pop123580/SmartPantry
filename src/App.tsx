import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { useAuth } from './hooks/useAuth';

const Dashboard = React.lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })));
const Pantry = React.lazy(() => import('./pages/Pantry').then(m => ({ default: m.Pantry })));
const AddGrocery = React.lazy(() => import('./pages/AddGrocery').then(m => ({ default: m.AddGrocery })));
const FoodRescue = React.lazy(() => import('./pages/FoodRescue').then(m => ({ default: m.FoodRescue })));
const Shopping = React.lazy(() => import('./pages/Shopping').then(m => ({ default: m.Shopping })));
const Profile = React.lazy(() => import('./pages/Profile').then(m => ({ default: m.Profile })));
const Login = React.lazy(() => import('./pages/Login').then(m => ({ default: m.Login })));
const SignUp = React.lazy(() => import('./pages/SignUp').then(m => ({ default: m.SignUp })));

function ProtectedLayout() {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return <div className="w-full h-screen flex items-center justify-center"><div className="animate-pulse w-12 h-12 bg-primary rounded-full" /></div>;
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <AppLayout />;
}

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="w-full h-screen flex items-center justify-center"><div className="animate-pulse w-12 h-12 bg-primary rounded-full" /></div>}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/pantry" element={<Pantry />} />
            <Route path="/add" element={<AddGrocery />} />
            <Route path="/rescue" element={<FoodRescue />} />
            <Route path="/shopping" element={<Shopping />} />
            <Route path="/profile" element={<Profile />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;

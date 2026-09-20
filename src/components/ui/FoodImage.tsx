import { useState } from 'react';
import { clsx } from 'clsx';
import { ImageOff } from 'lucide-react';

interface FoodImageProps {
  src?: string;
  alt: string;
  fallbackEmoji?: string;
  className?: string;
}

export function FoodImage({ src, alt, fallbackEmoji = '🍲', className }: FoodImageProps) {
  const [error, setError] = useState(false);
  const [loaded, setLoaded] = useState(false);

  if (!src || error) {
    return (
      <div className={clsx("flex items-center justify-center bg-gray-100 text-gray-300", className)}>
        <span className="text-4xl opacity-50">{fallbackEmoji}</span>
      </div>
    );
  }

  return (
    <div className={clsx("relative overflow-hidden bg-gray-100", className)}>
      {!loaded && (
        <div className="absolute inset-0 animate-pulse bg-gray-200" />
      )}
      <img
        src={src}
        alt={alt}
        className={clsx("w-full h-full object-cover transition-opacity duration-300", loaded ? "opacity-100" : "opacity-0")}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
    </div>
  );
}

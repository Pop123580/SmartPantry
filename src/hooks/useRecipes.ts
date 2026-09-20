import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api/client';
import type { Recipe } from '../types/recipe';

export const useRecipes = () => {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchRecipes = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.recipes.getRecommendedRecipes();
      setRecipes(data);
      setError(null);
    } catch (err: any) {
      setError(err);
      setRecipes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecipes();
  }, [fetchRecipes]);

  const cookRecipe = async (id: string) => {
    await api.recipes.cookRecipe(id);
    // Cooking updates inventory on the backend, so we might want to trigger a global refresh or rely on individual page load
  };

  return { recipes, loading, error, refresh: fetchRecipes, cookRecipe };
};

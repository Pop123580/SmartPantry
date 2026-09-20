import { RecipeApi } from '../../api/recipeApi';
import { Recipe } from '../../../types/recipe';
import { fetchApi } from '../../api/client';

export const fastapiRecipeApi: RecipeApi = {
  getRecommendedRecipes: () => fetchApi('/api/recipes/recommended'),
  getRecipe: (id: string) => fetchApi(`/api/recipes/${id}`),
  cookRecipe: (id: string) => fetchApi(`/api/recipes/${id}/cook`, { method: 'POST' })
};

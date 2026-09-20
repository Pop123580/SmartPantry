import { Recipe } from '../../types/recipe';

export interface RecipeApi {
  getRecommendedRecipes: () => Promise<Recipe[]>;
  getRecipe: (id: string) => Promise<Recipe>;
  cookRecipe: (id: string) => Promise<void>;
}

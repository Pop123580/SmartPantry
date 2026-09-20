# PROPOSED FRONTEND CONTRACT — NOT FINAL BACKEND API

This document describes the expected data shapes and operations the frontend needs. The backend team owns the actual database schemas and FastAPI endpoints. The backend can transform its database representation into these API models.

## Pantry

- `GET /api/pantry` -> `PantryItem[]`
- `GET /api/pantry/:id` -> `PantryItem`
- `POST /api/pantry` -> `PantryItem`
- `PATCH /api/pantry/:id` -> `PantryItem`
- `DELETE /api/pantry/:id`

## Recipes / Food Rescue

- `GET /api/recipes/recommended` -> `Recipe[]`
  (Should include reasoning for recommendation based on expiring items)
- `GET /api/recipes/:id` -> `Recipe`
- `POST /api/recipes/:id/cook`
  (Should decrease the inventory of the ingredients used)

## Shopping

- `GET /api/shopping` -> `ShoppingItem[]`
- `POST /api/shopping` -> `ShoppingItem`
- `DELETE /api/shopping/:id`

## Receipt OCR

- `POST /api/receipt/upload` (multipart/form-data) -> `CreatePantryItemDTO[]`

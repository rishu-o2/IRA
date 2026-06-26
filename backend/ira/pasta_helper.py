
def get_pasta_recipe(type):
    recipes = {
        "carbonara": "Cook spaghetti, fry guanciale, mix eggs and pecorino, combine off-heat with pasta water.",
        "pesto": "Blend fresh basil, pine nuts, garlic, parmesan, and olive oil. Toss with trofie or linguine.",
        "arrabbiata": "Sauté garlic and chili in olive oil, add tomatoes, simmer, and toss with penne."
    }
    return recipes.get(type.lower(), "I don't have that recipe yet, but I can look it up for you!")

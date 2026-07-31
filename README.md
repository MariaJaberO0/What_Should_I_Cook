# 🍳 What Should I Cook?

An intelligent recipe recommender built with Streamlit and AI (DeepSeek).  
Helps you decide what to cook based on available ingredients, meal type, and time.

---

## ✨ Features

### Core Features
- **Select a meal type** – breakfast, lunch, dinner, dessert, or appetizer
- **Set your maximum cooking time** – filter recipes by how long you want to spend
- **Pick ingredients you have** – up to 8 from a comprehensive list
- **AI‑powered ranking** – DeepSeek evaluates recipes based on *core ingredients* and returns the top 5 with natural‑language comments
- **Detailed view** – cooking instructions, ingredient substitutions, and a shopping list

### Visual Features
- **📊 Ingredient Readiness Pie Chart** – Instantly see what percentage of ingredients you have for the selected recipe
- **⏱️ Compare Cooking Times Bar Chart** – Quickly compare preparation times across your top 5 matches
- **🎉 Celebration effect** – Balloons pop when results appear!
- **🎨 Warm, intuitive UI** – Beautiful cards, step indicators, and responsive design

---

## 🛠️ Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Streamlit** | UI framework |
| **Pandas** | Data handling and filtering |
| **Matplotlib** | Data visualization (pie charts) |
| **OpenAI / DeepSeek** | AI reasoning and ranking |
| **python-dotenv** | Secret management |
| **OpenRouter** | API gateway for AI models |

---

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/What_Should_I_Cook.git
   cd What_Should_I_Cook
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your API key:**
   - Create a folder named `secrets` in the root directory.
   - Inside `secrets`, create a file named `.env` with the following content:
     ```
     OPENROUTER_API_KEY=your-api-key-here
     ```

5. **Run the app:**
   ```bash
   streamlit run app.py
   ```

---

## 📁 Project Structure
```
What_Should_I_Cook/
├── app.py                         # Main application
├── recipe_dataset_extended.xlsx   # Recipe dataset
├── secrets/
│   └── .env                       # API key (ignored by Git)
├── requirements.txt               # Python dependencies
├── .gitignore                     # Files ignored by Git
└── README.md                      # This file
```

---

## 🗂️ Dataset
The dataset contains **78 Middle Eastern and international recipes**, including:
- **Ingredients** – comma‑separated list
- **Meal types** – breakfast, lunch, dinner, dessert, appetizer (multiple allowed)
- **Cooking time** – in minutes
- **Image URLs** – from Unsplash, Pexels, and Wikimedia Commons
- **I mede it myself ^_^**
---

## 🤖 AI Prompt Engineering

The AI is instructed to identify **"Core Ingredients"** (proteins, main vegetables, dough) and strictly rejects recipes if the user is missing them. This prevents unrealistic recommendations like suggesting a beef sandwich when the user only has bread and oil.

**Example of the AI's reasoning:**
- User has: `chicken, rice, garlic`
- AI sees recipe `Chicken Kabsa` → Core ingredient is `chicken` → ✅ Good match! → ranks it high
- User has: `olive oil, bread`
- AI sees recipe `Beef Sandwich` → Core ingredient is `beef` → ❌ Missing → excluded entirely

**System Prompt (shortened):**
```
You are a strict but empathetic recipe advisor...
1. Identify the 'Core Ingredient(s)' of each recipe.
2. A recipe is ONLY considered a 'Good Match' if the user has AT LEAST ONE Core Ingredient.
3. Do NOT recommend a recipe just because the user has pantry staples.
4. Rank the recipes from most feasible to least feasible.
5. If a recipe is a poor match, exclude it entirely.
6. Return a JSON array of objects with 'recipe_Id' and 'comment'.
```

---

## 📊 Visual Features Preview

### 1. Ingredient Readiness Pie Chart
When you select a recipe, a pie chart shows you exactly how many ingredients you have and how many you're missing.  
A summary message tells you if you're ready to cook or need to go shopping.

### 2. Compare Cooking Times Bar Chart
On the results page, a bar chart visualizes the cooking times of your top 5 matches – helping you pick the recipe that fits your schedule.

---

## 📦 Requirements

Create a `requirements.txt` file with:
```
streamlit
pandas
openai
python-dotenv
matplotlib
```

---

## 📝 License
MIT License – free to use, modify, and distribute.

---

## 👩‍🍳 Author

Built with ❤️ for home cooks who need inspiration.
Maria Jaber
---

## 🤝 Contributing
Pull requests and suggestions are welcome! If you find a bug or have an idea for a new feature, please tell me

---

**Happy cooking! 🍳**
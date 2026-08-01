# 🍳 شو أطبخ اليوم؟ (What Should I Cook?)

An intelligent recipe recommender built with Streamlit and AI (DeepSeek).  
Helps you decide what to cook based on available ingredients, meal type, time, and even your personal preferences.

> **🌐 Arabic-first**: The app is designed for Arabic speakers, with full RTL support and natural Arabic comments.

---

## ✨ Features

### Core Features
- **Select a meal type** – breakfast, lunch, dinner, dessert, or appetizer (in Arabic)
- **Set your maximum cooking time** – filter recipes by how long you want to spend
- **Pick ingredients you have** – up to 8 from a comprehensive list (in Arabic)
- **AI‑powered ranking** – DeepSeek evaluates recipes based on *core ingredients* (hero ingredients) and returns the top 5 with natural‑language comments in Arabic
- **Detailed view** – cooking instructions, ingredient substitutions, and a shopping list

### Smart AI Assistant
- **Perfect for users who are unsure** – if you don't know what to cook or even what ingredients you have, click **"✨ اسأليني وأنا أختار لك"**
- **Smart questions** – the AI asks about your preferences (light vs. hearty, grilled vs. fried, sweet vs. savory) – not just "do you have eggs?"
- **Virtual recipe generation** – the AI creates 3–5 personalized recipe suggestions, even if they don't exist in the database
- **Hard constraints enforcement** – the wizard respects your "no" answers and will never suggest a recipe containing ingredients you said you don't have

### Visual Features
- **📊 Ingredient Readiness Pie Chart** – Instantly see what percentage of ingredients you have for the selected recipe
- **⏱️ Compare Cooking Times Bar Chart** – Quickly compare preparation times across your top 5 matches (with gradient colors)
- **🎉 Celebration effect** – Balloons pop when results appear!
- **🎨 Warm, artisan‑inspired UI** – Beautiful cards with wood‑tag ingredients, step indicators, and a handcrafted "Recipe Box" feel

---

## 🛠️ Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Streamlit** | UI framework |
| **Pandas** | Data handling and filtering |
| **Matplotlib** | Data visualization (pie charts, bar charts) |
| **OpenAI / DeepSeek** | AI reasoning, ranking, and recipe generation |
| **python-dotenv** | Secret management (API key) |
| **OpenRouter** | API gateway for AI models |
| **re (regex)** | Splitting Arabic/English ingredient lists |

---

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/What_Should_I_Cook.git
   cd What_Should_I_Cook
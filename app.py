import streamlit as st
st.set_page_config(
    page_title="What Should I Cook?",
    page_icon="🍳",   # ← يعمل دائماً
    layout="centered",
    initial_sidebar_state="collapsed"
)
import os

import pandas as pd
import json
from openai import OpenAI
import matplotlib.pyplot as plt
# ------------------------- PAGE CONFIGURATION ------------------------------

# ------------------------- BASE DIRECTORY -----------------------------------
# Anchor every relative path to this script's own folder, not to whatever
# directory the command happens to be launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))




# ------------------------- CUSTOM CSS (loaded from external stylesheet) ----
STYLE_FILE = os.path.join(BASE_DIR, "style.css")

def load_css(file_path):
    """Loads the external stylesheet and injects it into the page."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:   # 👈 إضافة الترميز
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(STYLE_FILE)

# ------------------------- FILE PATHS & SECRETS ----------------------------
DATA_FILE = os.path.join(BASE_DIR, "recipe_dataset.xlsx")

# Load API key from secrets/.env (or use st.secrets)
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(BASE_DIR, "secrets", ".env"))

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("🔑 Missing API key. Please set OPENROUTER_API_KEY in secrets/.env")
    st.stop()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

# ------------------------- CONSTANTS ----------------------------------------
PANTRY_ITEMS = {
    'salt', 'black_pepper', 'olive_oil', 'vegetable_oil', 'water',
    'lemon_juice', 'baking_powder', 'yeast', 'sugar', 'vanilla_extract',
    'cornstarch', 'milk_powder'
}

# ------------------------- HELPER FUNCTIONS --------------------------------
@st.cache_data
def load_data():
    """Loads the Excel dataset. No image extraction needed – uses URLs directly."""
    data = pd.read_excel(DATA_FILE)
    return data

# ------------------------- LOAD DATA ---------------------------------------
df = load_data()
ALL_MEAL_TYPES = ["breakfast", "lunch", "dinner", "dessert", "appetizer"]

def build_ingredient_options(data):
    raw = set()
    for cell in data["ingredients_Items"]:
        for item in str(cell).split(","):
            raw.add(item.strip())
    return {key.replace("_", " ").title(): key for key in sorted(raw)}

INGREDIENT_MAP = build_ingredient_options(df)

# ------------------------- SESSION STATE INIT ------------------------------
if "stage" not in st.session_state:
    st.session_state.stage = "meal_type"
if "filtered" not in st.session_state:
    st.session_state.filtered = df.copy()
if "results" not in st.session_state:
    st.session_state.results = None
if "selected_recipe" not in st.session_state:
    st.session_state.selected_recipe = None
if "error_msg" not in st.session_state:
    st.session_state.error_msg = ""
if "selected_type" not in st.session_state:
    st.session_state.selected_type = ""
if "max_time" not in st.session_state:
    st.session_state.max_time = 60
if "_last_user_items" not in st.session_state:
    st.session_state._last_user_items = []
if "_instructions" not in st.session_state:
    st.session_state._instructions = ""
if "_subs" not in st.session_state:
    st.session_state._subs = ""
if "_shopping_list" not in st.session_state:
    st.session_state._shopping_list = []

# ------------------------- HEADER -------------------------------------------
st.markdown("<h1 style='text-align:center;'>🍳 What Should I Cook?</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#7a6b5e; font-size:1.1rem;'>Find the perfect dish with what you already have.</p>", unsafe_allow_html=True)

# ------------------------- STEP INDICATOR ----------------------------------
def render_steps(current_stage):
    steps = ["meal_type", "ingredients", "results"]
    labels = ["Meal", "Ingredients", "Results"]
    if current_stage in steps:
        current_idx = steps.index(current_stage)
    else:
        current_idx = 0
    if current_stage == "detail":
        current_idx = 2

    cols = st.columns([1, 2, 1, 2, 1])
    with cols[0]:
        st.markdown(f"""
            <div class="step-item">
                <div class="step-circle {'active' if current_idx == 0 else 'completed'}">1</div>
                <div class="step-label {'active' if current_idx == 0 else ''}">Meal</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""<div class="step-line {'completed' if current_idx >= 1 else ''}"></div>""", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
            <div class="step-item">
                <div class="step-circle {'active' if current_idx == 1 else 'completed' if current_idx > 1 else ''}">2</div>
                <div class="step-label {'active' if current_idx == 1 else ''}">Ingredients</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""<div class="step-line {'completed' if current_idx >= 2 else ''}"></div>""", unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f"""
            <div class="step-item">
                <div class="step-circle {'active' if current_idx == 2 else ''}">3</div>
                <div class="step-label {'active' if current_idx == 2 else ''}">Results</div>
            </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# STAGE 1: MEAL TYPE + TIME
# ---------------------------------------------------------------------------
if st.session_state.stage == "meal_type":
    render_steps("meal_type")
    st.markdown("### 😋 What are you in the mood for?")
    selected_type = st.radio(
        "Select your meal type:",
        ALL_MEAL_TYPES,
        index=None,
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("### ⏱️ How much time do you have?")
    max_time = st.slider(
        "Max cooking time (minutes):",
        min_value=5,
        max_value=180,
        value=60,
        step=5,
        label_visibility="collapsed"
    )
    if st.button("👉 Next", disabled=not selected_type, use_container_width=True):
        st.session_state.selected_type = selected_type
        st.session_state.max_time = max_time
        mask = df["meal_Type"].apply(
            lambda x: selected_type in [p.strip() for p in str(x).split(",")]
        )
        time_mask = df["max_Time"] <= max_time
        st.session_state.filtered = df[mask & time_mask]
        st.session_state._debug_count = len(st.session_state.filtered)
        st.session_state.stage = "ingredients"
        st.rerun()

# ---------------------------------------------------------------------------
# STAGE 2: INGREDIENTS
# ---------------------------------------------------------------------------
elif st.session_state.stage == "ingredients":
    render_steps("ingredients")
    st.markdown("### 🧺 What ingredients do you have?")
    st.caption("Pick from the list below (max 8).")

    MAX_INGREDIENT_SELECTIONS = 8
    checked_labels = st.multiselect(
        "Select ingredients you have:",
        options=list(INGREDIENT_MAP.keys()),
        default=[],
        label_visibility="collapsed",
    )
    if len(checked_labels) > MAX_INGREDIENT_SELECTIONS:
        st.session_state.error_msg = f"⚠️ Please select at most {MAX_INGREDIENT_SELECTIONS} items."
    else:
        st.session_state.error_msg = ""
    st.caption(f"📊 {len(checked_labels)} ingredient{'s' if len(checked_labels)!=1 else ''} selected")

    # # Developer debug
    # with st.expander("🔧 Developer tools"):
    #     st.caption(f"After meal+time: {st.session_state._debug_count} recipes")
    #     debug_df = st.session_state.filtered[["recipe_Id", "recipe_Nme", "ingredients_Items", "meal_Type", "max_Time"]]
    #     st.dataframe(debug_df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back", use_container_width=True, key="back_ingredients"):
            st.session_state.stage = "meal_type"
            st.rerun()
    with col2:
        user_items = [INGREDIENT_MAP[label] for label in checked_labels]
        if len(user_items) < 3:
            st.session_state.error_msg = "⚠️ Please select at least 3 ingredients."
        elif len(checked_labels) > MAX_INGREDIENT_SELECTIONS:
            st.session_state.error_msg = f"⚠️ Please select at most {MAX_INGREDIENT_SELECTIONS} ingredients."
        else:
            st.session_state.error_msg = ""

        if st.button("🔍 Find Recipes", disabled=bool(st.session_state.error_msg), use_container_width=True):
            candidates = st.session_state.filtered
            if candidates.empty:
                st.session_state.stage = "no_match"
                st.rerun()

            st.session_state._last_user_items = user_items

            with st.spinner("🧑‍🍳 Asking the AI to find your perfect dishes..."):
                try:
                    selected_type = st.session_state.selected_type
                    max_time = st.session_state.max_time

                    recipes_info = candidates[["recipe_Id", "recipe_Nme", "ingredients_Items", "meal_Type", "max_Time"]].to_dict(orient="records")
                    recipes_json = json.dumps(recipes_info, indent=2)

                    system_prompt = (
                        "You are a strict but empathetic recipe advisor. Your job is to recommend recipes based on the user's ingredients, meal type, and time limit.\n"
                        "Follow these reasoning rules strictly:\n"
                        "1. Identify the 'Core Ingredient(s)' of each recipe. These are the defining components: the main protein (beef, chicken, lamb, fish, eggs), the main carbohydrate/dough (flour, rice, pasta, bread), or the main vegetable (eggplant, okra, tomatoes).\n"
                        "2. A recipe is ONLY considered a 'Good Match' if the user has AT LEAST ONE Core Ingredient. If the user is missing ALL Core Ingredients, reject it entirely and do NOT include it in the output.\n"
                        "3. Do NOT recommend a recipe just because the user has pantry staples (salt, pepper, oil, garlic, onion, lemon juice). These are supporting actors, not the stars.\n"
                        "4. Rank the recipes from the most feasible (user has the core ingredients and most extras) to the least feasible.\n"
                        "5. IMPORTANT: If a recipe is a poor match (e.g., the user is missing multiple key ingredients, or the only overlap is pantry staples), you MUST exclude it entirely. Do not return it in the JSON array. Only return recipes that are at least a 'partial match' (i.e., the user has at least one core ingredient and a reasonable number of the supporting ones).\n"
                        "6. For each selected recipe, write a short, honest, natural-language comment.\n"
                        "Return a JSON array of objects, each with 'recipe_Id' and 'comment'. The array order must reflect your ranking (best match first).\n"
                        "Example: [{\"recipe_Id\": 1, \"comment\": \"Perfect! You have chicken and rice – you can make this easily.\"}, {\"recipe_Id\": 2, \"comment\": \"You have flour and oil, but this also needs yeast. You'd need to buy yeast.\"}]\n"
                        "Do NOT include any other text outside the JSON array."
                    )

                    user_prompt = (
                        f"The user selected meal type: {selected_type}. "
                        f"Maximum cooking time: {max_time} minutes. "
                        f"The user has these ingredients: {user_items}. "
                        f"Here are the candidate recipes (each has recipe_Id, name, ingredients list, meal types, and max time):\n\n{recipes_json}"
                    )

                    response = client.chat.completions.create(
                        model="deepseek/deepseek-chat",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=600,
                        temperature=0.3,
                    )

                    ai_output = response.choices[0].message.content.strip()

                    # Parse AI response
                    ai_items = []
                    try:
                        parsed = json.loads(ai_output)
                        if isinstance(parsed, list):
                            ai_items = [{"recipe_Id": str(item["recipe_Id"]), "comment": item["comment"]}
                                        for item in parsed if "recipe_Id" in item and "comment" in item]
                    except json.JSONDecodeError:
                        start = ai_output.find('[')
                        end = ai_output.rfind(']') + 1
                        if start != -1 and end != -1:
                            try:
                                parsed = json.loads(ai_output[start:end])
                                ai_items = [{"recipe_Id": str(item["recipe_Id"]), "comment": item["comment"]}
                                            for item in parsed if "recipe_Id" in item and "comment" in item]
                            except:
                                ai_items = []

                    valid_ids = set(candidates["recipe_Id"].astype(str))
                    if ai_items:
                        filtered_items = [item for item in ai_items if item["recipe_Id"] in valid_ids]
                        if filtered_items:
                            top_ids = [item["recipe_Id"] for item in filtered_items]
                            comment_map = {item["recipe_Id"]: item["comment"] for item in filtered_items}
                            results = candidates[candidates["recipe_Id"].astype(str).isin(top_ids)]
                            rank_map = {id: i for i, id in enumerate(top_ids)}
                            results = results.copy()
                            results["rank"] = results["recipe_Id"].astype(str).map(rank_map)
                            results = results.sort_values("rank").drop(columns=["rank"])
                            results["comment"] = results["recipe_Id"].astype(str).map(comment_map)
                        else:
                            results = pd.DataFrame()
                    else:
                        results = pd.DataFrame()

                    # Fallback if AI returns nothing
                    if results.empty:
                        st.warning("🤔 The AI couldn't find a perfect match, but here are some ideas based on your ingredients.")
                        user_meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                        def simple_score(row):
                            recipe_ings = str(row["ingredients_Items"]).split(",")
                            recipe_meaningful = [i.strip() for i in recipe_ings if i.strip() not in PANTRY_ITEMS]
                            return len(set(user_meaningful) & set(recipe_meaningful))
                        candidates = candidates.copy()
                        candidates["score"] = candidates.apply(simple_score, axis=1)
                        candidates = candidates.sort_values("score", ascending=False)
                        def gen_comment(row):
                            recipe_ings = str(row["ingredients_Items"]).split(",")
                            meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                            matched = set(meaningful) & set(recipe_ings)
                            if not meaningful:
                                return "You haven't selected any core ingredients."
                            pct = len(matched) / len(meaningful) * 100
                            if pct >= 70:
                                return "Great match – you have most of the key ingredients!"
                            elif pct >= 40:
                                return "Partial match – you'll need a few more items."
                            else:
                                return "This recipe requires many ingredients you don't have – not recommended."
                        candidates["comment"] = candidates.apply(gen_comment, axis=1)
                        results = candidates.head(5).copy()

                    # Ensure exactly 5
                    if len(results) < 5 and not candidates.empty:
                        used_ids = set(results["recipe_Id"].astype(str))
                        remaining = candidates[~candidates["recipe_Id"].astype(str).isin(used_ids)]
                        if not remaining.empty:
                            user_meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                            def simple_score(row):
                                recipe_ings = str(row["ingredients_Items"]).split(",")
                                recipe_meaningful = [i.strip() for i in recipe_ings if i.strip() not in PANTRY_ITEMS]
                                return len(set(user_meaningful) & set(recipe_meaningful))
                            remaining = remaining.copy()
                            remaining["score"] = remaining.apply(simple_score, axis=1)
                            remaining = remaining.sort_values("score", ascending=False)
                            needed = 5 - len(results)
                            extra = remaining.head(needed)
                            def gen_comment(row):
                                recipe_ings = str(row["ingredients_Items"]).split(",")
                                meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                                matched = set(meaningful) & set(recipe_ings)
                                if not meaningful:
                                    return "You haven't selected any core ingredients."
                                pct = len(matched) / len(meaningful) * 100
                                if pct >= 70:
                                    return "Great match – you have most of the key ingredients!"
                                elif pct >= 40:
                                    return "Partial match – you'll need a few more items."
                                else:
                                    return "This recipe requires many ingredients you don't have – not recommended."
                            extra["comment"] = extra.apply(gen_comment, axis=1)
                            results = pd.concat([results, extra], ignore_index=True)

                    st.session_state.results = results
                    st.session_state.stage = "results"
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"AI request failed: {e}. Please try again or adjust your inputs.")
                    st.stop()

    if st.session_state.error_msg:
        st.warning(st.session_state.error_msg)

# ---------------------------------------------------------------------------
# STAGE 3: NO MATCH
# ---------------------------------------------------------------------------
elif st.session_state.stage == "no_match":
    render_steps("ingredients")
    st.warning("😕 No recipes matched your meal type and time preferences.")
    st.caption("Try adjusting your meal type or time limit, then come back.")
    if st.button("⬅ Start over", use_container_width=True):
        st.session_state.stage = "meal_type"
        st.rerun()

# ---------------------------------------------------------------------------
# STAGE 4: RESULTS (with Bar Chart)
# ---------------------------------------------------------------------------
elif st.session_state.stage == "results":
    render_steps("results")
    st.subheader("🏆 Your top matches")
    results = st.session_state.results

    if results.empty:
        st.warning("No recipes matched your criteria. Try adjusting your ingredients or meal type.")
        if st.button("⬅ Try different ingredients"):
            st.session_state.stage = "ingredients"
            st.rerun()
    else:
        for idx, recipe in results.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="recipe-card">
                    <div style="display:flex; flex-wrap:wrap; gap:1rem;">
                        <div style="flex:1; min-width:120px;">
                """, unsafe_allow_html=True)
                if recipe.get("pics"):
                    try:
                        st.image(recipe["pics"], width=140)
                    except Exception:
                        st.caption("📷 image unavailable")
                else:
                    st.caption("📷 image unavailable")
                st.markdown("</div><div style='flex:3;'>", unsafe_allow_html=True)
                st.markdown(f"### {recipe['recipe_Nme'].title()}")
                st.caption(f"{recipe['meal_Type']} · {recipe['max_Time']} min")
                comment = recipe.get("comment", "")
                if comment:
                    st.info(f"💬 {comment}")
                ings = [i.strip() for i in str(recipe["ingredients_Items"]).split(",")]
                tag_html = " ".join([f"<span class='ingredient-tag'>{i.replace('_',' ').title()}</span>" for i in ings[:6]])
                st.markdown(tag_html, unsafe_allow_html=True)
                if len(ings) > 6:
                    st.caption(f"+{len(ings)-6} more")

                if st.button("👨‍🍳 Choose this recipe", key=f"choose_{recipe['recipe_Id']}"):
                    st.session_state.selected_recipe = recipe
                    st.session_state.stage = "detail"
                    st.rerun()
                st.markdown("</div></div></div>", unsafe_allow_html=True)

        # ---- BAR CHART: Compare cooking times (NEW) ----
        if len(results) >= 2:
            st.markdown("---")
            st.subheader("⏱️ Compare Cooking Times")
            chart_data = results[["recipe_Nme", "max_Time"]].copy()
            chart_data["recipe_Nme"] = chart_data["recipe_Nme"].str.title()
            chart_data = chart_data.set_index("recipe_Nme")
            st.bar_chart(chart_data, use_container_width=True)
            st.caption("See which recipe fits your available time best.")

        if st.button("⬅ Try different ingredients", use_container_width=True):
            st.session_state.stage = "ingredients"
            st.rerun()
# ---------------------------------------------------------------------------
# STAGE 5: DETAIL (with Pie Chart)
# ---------------------------------------------------------------------------
elif st.session_state.stage == "detail":
    render_steps("results")
    recipe = st.session_state.selected_recipe
    user_items = st.session_state._last_user_items

    st.markdown(f"""
        <div style="background:white; border-radius:20px; padding:1.5rem; box-shadow:0 8px 24px rgba(0,0,0,0.08);">
            <h2 style="color:#4a3728;">🍽️ {recipe['recipe_Nme'].title()}</h2>
            <p><strong>Meal type:</strong> {recipe['meal_Type']}  |  <strong>Time:</strong> {recipe['max_Time']} min</p>
            <p><strong>Ingredients:</strong> {recipe['ingredients_Items'].replace('_', ' ').replace(',', ', ')}</p>
    """, unsafe_allow_html=True)

    comment = recipe.get("comment", "")
    if comment:
        st.info(f"💬 {comment}")

    if recipe.get("pics"):
        try:
            st.image(recipe["pics"], use_container_width=True)
        except Exception:
            st.caption("Picture not available for this dish yet.")
    else:
        st.caption("Picture not available for this dish yet.")

    st.markdown("---")

    # ---- PIE CHART: Ingredient readiness (NEW) ----
    st.subheader("📊 Ingredient Readiness")
    recipe_items = [i.strip() for i in str(recipe["ingredients_Items"]).split(",")]
    missing = [i for i in recipe_items if i not in user_items and i not in PANTRY_ITEMS]

    total = len(recipe_items)
    available = total - len(missing)

    if total > 0:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 4))
        colors = ['#8fb88e', '#e07c5e']
        
        if len(missing) == 0:
            sizes = [1, 0]
            labels = ['✅ All ingredients available', '']
            colors = ['#8fb88e', '#f0e3dc']
        else:
            sizes = [available, len(missing)]
            labels = [f'✅ Available ({available})', f'❌ Missing ({len(missing)})']

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            colors=colors,
            startangle=90,
            wedgeprops={'edgecolor': 'white', 'linewidth': 2},
            textprops={'fontsize': 12}
        )
        ax.set_title("Available vs Missing Ingredients", fontsize=14, fontweight='bold')
        st.pyplot(fig)
        
        # Show a summary message
        if len(missing) == 0:
            st.success("🎉 You have everything you need! No shopping required.")
        else:
            st.info(f"ℹ️ You have {available} out of {total} ingredients. Scroll down to see substitutions or the shopping list.")
    else:
        st.caption("No ingredients to display.")

    st.markdown("---")

    # ---- FEATURE 1: INSTRUCTIONS ----
    if st.button("📖 Show me how to cook it"):
        with st.spinner("🧑‍🍳 Writing instructions..."):
            try:
                instruction_prompt = (
                    f"Write a clear, step-by-step cooking guide for the recipe '{recipe['recipe_Nme']}'. "
                    f"The ingredients are: {recipe['ingredients_Items']}. "
                    f"The user already has these ingredients: {user_items}. "
                    f"If they are missing something, mention it briefly. Keep it practical and easy to follow."
                )
                resp = client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful cooking assistant. Provide clear, numbered steps."},
                        {"role": "user", "content": instruction_prompt}
                    ],
                    max_tokens=800,
                    temperature=0.5,
                )
                st.session_state._instructions = resp.choices[0].message.content
                st.rerun()
            except Exception as e:
                st.error(f"Could not fetch instructions: {e}")

    if st.session_state._instructions:
        with st.expander("📖 Instructions", expanded=True):
            st.write(st.session_state._instructions)
        if st.button("Clear instructions"):
            st.session_state._instructions = ""
            st.rerun()

    st.markdown("---")

    # ---- FEATURE 2: SUBSTITUTIONS & SHOPPING LIST ----
    if missing:
        if st.button("🔄 Suggest substitutions for missing ingredients"):
            with st.spinner("🔍 Finding swaps..."):
                try:
                    sub_prompt = (
                        f"The user is making '{recipe['recipe_Nme']}'. "
                        f"They are missing these ingredients: {missing}. "
                        f"Suggest common, easy-to-find substitutions for each missing ingredient. "
                        f"Format: 'Missing X → Use Y instead (reason)'. Keep it brief."
                    )
                    resp = client.chat.completions.create(
                        model="deepseek/deepseek-chat",
                        messages=[
                            {"role": "system", "content": "You are a helpful cooking assistant. Provide practical substitutions."},
                            {"role": "user", "content": sub_prompt}
                        ],
                        max_tokens=400,
                        temperature=0.4,
                    )
                    st.session_state._subs = resp.choices[0].message.content
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not fetch substitutions: {e}")

        if st.session_state._subs:
            with st.expander("🔄 Substitutions", expanded=True):
                st.write(st.session_state._subs)
            if st.button("Clear substitutions"):
                st.session_state._subs = ""
                st.rerun()

        if st.button("🛒 Show shopping list (missing items)"):
            st.session_state._shopping_list = missing
            st.rerun()

        if st.session_state._shopping_list:
            with st.expander("🛒 Shopping List", expanded=True):
                for item in st.session_state._shopping_list:
                    st.write(f"- {item.replace('_', ' ').title()}")
            if st.button("Clear shopping list"):
                st.session_state._shopping_list = []
                st.rerun()
    else:
        st.success("✅ You have all the ingredients! No shopping needed.")

    st.markdown("---")

    # ---- YOUTUBE TUTORIAL ----
    query = recipe["recipe_Nme"].replace(" ", "+")
    youtube_url = f"https://www.youtube.com/results?search_query=how+to+cook+{query}"
    st.link_button("🎥 Search YouTube tutorial", youtube_url, use_container_width=True)

    # ---- BACK BUTTON ----
    if st.button("⬅ Back to results", use_container_width=True):
        st.session_state._instructions = ""
        st.session_state._subs = ""
        st.session_state._shopping_list = []
        st.session_state.stage = "results"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
# ---------------------------------------------------------------------------
# STAGE 6: TUTORIAL (kept for compatibility)
# ---------------------------------------------------------------------------
elif st.session_state.stage == "tutorial":
    st.warning("This page is outdated. Please go back.")
    if st.button("⬅ Back"):
        st.session_state.stage = "detail"
        st.rerun()

# ---------------------------------------------------------------------------
# STAGE 7: DONE
# ---------------------------------------------------------------------------
elif st.session_state.stage == "done":
    st.success("🎉 Enjoy your meal! Come back anytime for more inspiration.")
    if st.button("⬅ Find another recipe"):
        st.session_state.stage = "meal_type"
        st.rerun()
        #to run this app, use the command: streamlit run app.py or python -m streamlit run app.py
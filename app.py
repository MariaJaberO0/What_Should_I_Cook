import streamlit as st
import os
import pandas as pd
import json
import re
from openai import OpenAI
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# ------------------------- PAGE CONFIGURATION ------------------------------
st.set_page_config(
    page_title="شو أطبخ اليوم؟",
    page_icon="🍳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ------------------------- BASE DIRECTORY -----------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------- CUSTOM CSS -------------------------------------
STYLE_FILE = os.path.join(BASE_DIR, "style.css")

def load_css(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(STYLE_FILE)

# ------------------------- GLOBAL RTL SUPPORT ------------------------------
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    direction: rtl;
}

.stMarkdown, .stMarkdown p, .stMarkdown li,
h1, h2, h3, h4, h5, h6,
.stCaption, .stAlert, .stException,
label, .stSelectbox label, .stRadio label, .stSlider label {
    direction: rtl;
    text-align: right !important;
}

div[role="radiogroup"] {
    direction: rtl;
}
div[role="radiogroup"] label {
    direction: rtl;
    text-align: right;
}

.stSlider label {
    text-align: right !important;
}

.step-item, .step-label {
    text-align: center;
}

div[data-testid="stAlert"] {
    text-align: right;
    direction: rtl;
}

input, textarea, select {
    text-align: right;
    direction: rtl;
}
</style>
""", unsafe_allow_html=True)

# ------------------------- FILE PATHS & SECRETS ----------------------------
DATA_FILE = os.path.join(BASE_DIR, "recipe_dataset_arabic.xlsx")
load_dotenv(dotenv_path=os.path.join(BASE_DIR, "secrets", ".env"))
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("🔑 مفتاح API مفقود. يرجى تعيين OPENROUTER_API_KEY في ملف secrets/.env")
    st.stop()

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

# ------------------------- CONSTANTS (مكونات المخزن بالعربية) -----------------
PANTRY_ITEMS = {
    'ملح', 'فلفل أسود', 'زيت زيتون', 'زيت قلي', 'ماء',
    'عصير ليمون', 'بيكنج باودر', 'خميرة', 'سكر', 'فانيليا',
    'نشا', 'حليب بودرة'
}

# ------------------------- HELPER FUNCTIONS --------------------------------
@st.cache_data
def load_data():
    data = pd.read_excel(DATA_FILE)
    return data

df = load_data()

ALL_MEAL_TYPES = ["فطور", "غداء", "عشاء", "حلويات", "مقبلات"]

def build_ingredient_options(data):
    raw = set()
    for cell in data["ingredients_Items"]:
        for item in re.split(r'[،,]', str(cell)):
            cleaned = item.strip()
            if cleaned:
                raw.add(cleaned)
    return {key: key for key in sorted(raw)}

INGREDIENT_MAP = build_ingredient_options(df)

def safe_show_image(pics_value, **kwargs):
    if pics_value is None:
        st.caption("📷 لا تتوفر صورة لهذه الوصفة")
        return
    try:
        if pd.isna(pics_value):
            st.caption("📷 لا تتوفر صورة لهذه الوصفة")
            return
    except (TypeError, ValueError):
        pass
    pics_str = str(pics_value).strip()
    if not pics_str or pics_str.lower() in ("nan", "none", ""):
        st.caption("📷 لا تتوفر صورة لهذه الوصفة")
        return
    try:
        st.image(pics_str, **kwargs)
    except Exception:
        st.caption("📷 تعذّر تحميل صورة هذه الوصفة")

def ingredient_count_text(n):
    if n == 0:
        return "لم تختر أي مكون بعد"
    elif n == 1:
        return "تم اختيار مكوّن واحد"
    elif n == 2:
        return "تم اختيار مكوّنَين"
    elif 3 <= n <= 10:
        return f"تم اختيار {n} مكوّنات"
    else:
        return f"تم اختيار {n} مكوّناً"

def match_comment(pct):
    if pct >= 70:
        return "مطابقة ممتازة! تتوفر لديك معظم المكونات الأساسية."
    elif pct >= 40:
        return "مطابقة جزئية — ستحتاج إلى بعض المكونات الإضافية."
    else:
        return "هذه الوصفة تحتاج مكونات كثيرة غير متوفرة لديك، فهي غير موصى بها حالياً."

# ------------------------- SESSION STATE ----------------------------------
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

# ========== NEW SESSION STATE FOR WIZARD ==========
if "wizard_active" not in st.session_state:
    st.session_state.wizard_active = False
if "wizard_step" not in st.session_state:
    st.session_state.wizard_step = 0  # 0=inactive, 1=questions, 2=answers, 3=results
if "wizard_questions" not in st.session_state:
    st.session_state.wizard_questions = []
if "wizard_answers" not in st.session_state:
    st.session_state.wizard_answers = {}
if "wizard_suggestions" not in st.session_state:
    st.session_state.wizard_suggestions = []

# ------------------------- HEADER ------------------------------
st.markdown("<h1 style='text-align:center;'>🍳 شو أطبخ اليوم؟</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center; color:#7a6b5e; font-size:1.1rem;'>"
    "راح نقدم لك خيارات بناءً على المكونات المتوفرة عندك، نوع الوجبة، والوقت المتاح. "
    "</p>",
    unsafe_allow_html=True
)

# ------------------------- STEP INDICATOR ----------------------
def render_steps(current_stage):
    steps = ["meal_type", "ingredients", "results"]
    labels = ["نوع الوجبة", "المكونات", "النتائج"]
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
                <div class="step-label {'active' if current_idx == 0 else ''}">{labels[0]}</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""<div class="step-line {'completed' if current_idx >= 1 else ''}"></div>""", unsafe_allow_html=True)
    with cols[2]:
        st.markdown(f"""
            <div class="step-item">
                <div class="step-circle {'active' if current_idx == 1 else 'completed' if current_idx > 1 else ''}">2</div>
                <div class="step-label {'active' if current_idx == 1 else ''}">{labels[1]}</div>
            </div>
        """, unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f"""<div class="step-line {'completed' if current_idx >= 2 else ''}"></div>""", unsafe_allow_html=True)
    with cols[4]:
        st.markdown(f"""
            <div class="step-item">
                <div class="step-circle {'active' if current_idx == 2 else ''}">3</div>
                <div class="step-label {'active' if current_idx == 2 else ''}">{labels[2]}</div>
            </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# STAGE 1: MEAL TYPE + TIME
# ---------------------------------------------------------------------------
if st.session_state.stage == "meal_type":
    render_steps("meal_type")
    st.markdown("### 🍽 شو الوجبة اللي ناوية تطبخيها؟") 
    selected_type = st.radio(
        "اختر نوع الوجبة:",
        ALL_MEAL_TYPES,
        index=None,
        horizontal=True,
        label_visibility="collapsed"
    )
    st.markdown("### ⏱️ كم من الوقت متاح لديك؟")
    max_time = st.slider(
        "الحد الأقصى لوقت الطهي (بالدقائق):",
        min_value=5,
        max_value=180,
        value=60,
        step=5,
        label_visibility="collapsed"
    )
    if st.button("👉 التالي", disabled=not selected_type, use_container_width=True):
        st.session_state.selected_type = selected_type
        st.session_state.max_time = max_time
        mask = df["meal_Type"].apply(
            lambda x: selected_type in [p.strip() for p in re.split(r'[،,]', str(x))]
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
    st.markdown("### 👩‍🍳 شو المكونات المتوفرة عندك؟")
    st.caption("اختر مكوناتك من القائمة أدناه (بحد أقصى 8 مكونات).")

    MAX_INGREDIENT_SELECTIONS = 8
    checked_labels = st.multiselect(
        "اختر المكونات المتوفرة:",
        options=list(INGREDIENT_MAP.keys()),
        default=[],
        label_visibility="collapsed",
    )
    if len(checked_labels) > MAX_INGREDIENT_SELECTIONS:
        st.session_state.error_msg = f"⚠️ يرجى اختيار {MAX_INGREDIENT_SELECTIONS} مكونات كحد أقصى."
    else:
        st.session_state.error_msg = ""
    st.caption(f"📊 {ingredient_count_text(len(checked_labels))}")

    # Developer debug (اختياري)
    # with st.expander("🔧 أدوات المطور"):
    #     st.caption(f"بعد تصفية الوجبة والوقت: {st.session_state._debug_count} وصفة")
    #     debug_df = st.session_state.filtered[["recipe_Id", "recipe_Nme", "ingredients_Items", "meal_Type", "max_Time"]]
    #     st.dataframe(debug_df, use_container_width=True)

    # =================================================================
    # NEW: WIZARD (AI Assistant) – appears as a separate section
    # =================================================================
    st.markdown("---")
    st.markdown("### 🤔 محتارة؟ دعي الذكاء الاصطناعي يساعدك في الاختيار!")

    if not st.session_state.wizard_active:
        if st.button("✨ اسأليني وأنا أختار لك", use_container_width=True):
            st.session_state.wizard_active = True
            st.session_state.wizard_step = 1
            st.rerun()
    else:
        # --- Wizard Step 1: Generate Questions ---
        if st.session_state.wizard_step == 1:
            with st.spinner("الذكاء الاصطناعي يجهز لك أسئلة مخصصة..."):
                try:
                    meal_type = st.session_state.selected_type
                    max_time = st.session_state.max_time

                    question_prompt = (
                        f"المستخدم يريد تحضير وجبة من نوع '{meal_type}'، ولديه وقت أقصاه {max_time} دقيقة. "
                        "هو حائر ولا يعرف ماذا يختار. قم بإنشاء 3 أسئلة إرشادية ذكية ومتنوعة (أسئلة اختيار من متعدد) "
                        "تساعده في تحديد ما يرغب به. الأسئلة يجب أن تكون حول المكونات المتوفرة (مثل: هل لديك بيض؟) أو التفضيلات (مثل: هل تفضل الحلو أم المالح؟). "
                        "قم بإرجاع مصفوفة JSON تحتوي على 3 كائنات، كل كائن يحتوي على 'question' (نص السؤال) و 'options' (مصفوفة خيارات، على الأقل 2 خيار).\n"
                        "مثال: [{\"question\": \"هل لديك بيض في الثلاجة؟\", \"options\": [\"نعم\", \"لا\"]}, ...]"
                    )
                    resp = client.chat.completions.create(
                        model="deepseek/deepseek-chat",
                        messages=[
                            {"role": "system", "content": "أنت خبير طهي يساعد المستخدم الحائر. أجب فقط بصيغة JSON صالحة."},
                            {"role": "user", "content": question_prompt}
                        ],
                        max_tokens=400,
                        temperature=0.5,
                    )
                    output = resp.choices[0].message.content.strip()
                    start = output.find('[')
                    end = output.rfind(']') + 1
                    if start != -1 and end != -1:
                        st.session_state.wizard_questions = json.loads(output[start:end])
                        st.session_state.wizard_step = 2
                        st.rerun()
                    else:
                        st.error("تعذّر توليد الأسئلة. يرجى المحاولة مرة أخرى.")
                        st.session_state.wizard_active = False
                        st.session_state.wizard_step = 0
                        st.rerun()
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")
                    st.session_state.wizard_active = False
                    st.session_state.wizard_step = 0
                    st.rerun()

        # --- Wizard Step 2: Show Questions ---
        elif st.session_state.wizard_step == 2:
            st.info("📝 أجبِ عن الأسئلة التالية ليساعدني في اقتراح أفضل وصفة لك:")
            questions = st.session_state.wizard_questions
            answers = {}

            for i, q in enumerate(questions):
                answer = st.radio(
                    q["question"],
                    options=q["options"],
                    key=f"wizard_q_{i}",
                    index=None,
                    horizontal=True
                )
                if answer:
                    answers[i] = answer

            col_wiz1, col_wiz2 = st.columns(2)
            with col_wiz1:
                if st.button("🔙 إلغاء", use_container_width=True):
                    st.session_state.wizard_active = False
                    st.session_state.wizard_step = 0
                    st.rerun()
            with col_wiz2:
                if st.button("💡 احصل على اقتراحاتي", disabled=len(answers) < len(questions), use_container_width=True):
                    st.session_state.wizard_answers = answers
                    st.session_state.wizard_step = 3
                    st.rerun()

        # --- Wizard Step 3: Generate Suggestions ---
        elif st.session_state.wizard_step == 3:
            with st.spinner("🧠 الذكاء الاصطناعي يفكر في أفضل الخيارات لك..."):
                try:
                    meal_type = st.session_state.selected_type
                    max_time = st.session_state.max_time
                    answers_text = "\n".join([f"- س: {st.session_state.wizard_questions[i]['question']} ج: {ans}" for i, ans in st.session_state.wizard_answers.items()])

                    suggest_prompt = (
                        f"المستخدم يريد وجبة '{meal_type}' في {max_time} دقيقة.\n"
                        f"إجاباته على الأسئلة:\n{answers_text}\n\n"
                        "بناءً على هذه المعلومات، قم بإنشاء 3-5 اقتراحات لوجبات محددة (قد تكون من معرفتك العامة أو من وصفات مشهورة). "
                        "لكل وجبة، اذكر الاسم، قائمة المكونات الأساسية، وتعليقاً قصيراً عن سبب ملاءمتها.\n"
                        "أعد مصفوفة JSON تحتوي على كائنات، كل كائن يحتوي على: 'name' (اسم الوصفة)، 'ingredients' (مصفوفة نصوص)، 'comment' (تعليق).\n"
                        "مثال: [{\"name\": \"عجة البيض بالجبنة\", \"ingredients\": [\"بيض\", \"جبنة\", \"زيت\"], \"comment\": \"سريعة ولذيذة، تناسب الفطور\"}]"
                    )
                    resp = client.chat.completions.create(
                        model="deepseek/deepseek-chat",
                        messages=[
                            {"role": "system", "content": "أنت خبير طهي مبدع. أجب فقط بصيغة JSON صالحة."},
                            {"role": "user", "content": suggest_prompt}
                        ],
                        max_tokens=600,
                        temperature=0.7,
                    )
                    output = resp.choices[0].message.content.strip()
                    start = output.find('[')
                    end = output.rfind(']') + 1
                    if start != -1 and end != -1:
                        st.session_state.wizard_suggestions = json.loads(output[start:end])
                        st.session_state.wizard_step = 4
                        st.rerun()
                    else:
                        st.error("تعذّر توليد الاقتراحات. حاول مرة أخرى.")
                        st.session_state.wizard_active = False
                        st.session_state.wizard_step = 0
                        st.rerun()
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")
                    st.session_state.wizard_active = False
                    st.session_state.wizard_step = 0
                    st.rerun()

        # --- Wizard Step 4: Show Suggestions ---
        elif st.session_state.wizard_step == 4:
            st.success("✅ إليك بعض الاقتراحات المثالية لك:")
            suggestions = st.session_state.wizard_suggestions

            for idx, sug in enumerate(suggestions):
                with st.container(border=True):
                    st.markdown(f"**{idx+1}. {sug['name']}**")
                    st.caption(f"المكونات: {', '.join(sug['ingredients'])}")
                    st.write(f"💬 {sug.get('comment', '')}")
                    if st.button(f"👨‍🍳 اختر هذه ({sug['name']})", key=f"wizard_choose_{idx}"):
                        # Create a virtual recipe
                        virtual_recipe = {
                            "recipe_Id": f"virtual_{idx}",
                            "recipe_Nme": sug['name'],
                            "ingredients_Items": ', '.join(sug['ingredients']),
                            "meal_Type": st.session_state.selected_type,
                            "max_Time": st.session_state.max_time,
                            "pics": None,
                            "comment": f"تم اقتراحها بواسطة المساعد الذكي بناءً على اختياراتك: {sug.get('comment', '')}",
                            "is_virtual": True
                        }
                        st.session_state.selected_recipe = virtual_recipe
                        st.session_state.stage = "detail"
                        # Reset wizard state
                        st.session_state.wizard_active = False
                        st.session_state.wizard_step = 0
                        st.rerun()

            if st.button("🔄 ابدأ من جديد (مساعد جديد)", use_container_width=True):
                st.session_state.wizard_active = False
                st.session_state.wizard_step = 0
                st.rerun()

        # ================================================================
        # End of Wizard section
        # ================================================================

    # ---------- Regular ingredient-based search (unchanged) ----------
    col1, col2 = st.columns(2)
    with col1:  # العمود الأيمن – زر البحث الأساسي
        user_items = [INGREDIENT_MAP[label] for label in checked_labels]
        if len(user_items) < 3:
            st.session_state.error_msg = "⚠️ يرجى اختيار 3 مكونات على الأقل."
        elif len(checked_labels) > MAX_INGREDIENT_SELECTIONS:
            st.session_state.error_msg = f"⚠️ يرجى اختيار {MAX_INGREDIENT_SELECTIONS} مكونات كحد أقصى."
        else:
            st.session_state.error_msg = ""

        if st.button("🔍 ابحث عن وصفات", disabled=bool(st.session_state.error_msg), use_container_width=True):
            candidates = st.session_state.filtered
            if candidates.empty:
                st.session_state.stage = "no_match"
                st.rerun()

            st.session_state._last_user_items = user_items

            with st.spinner("🤖 جاري البحث عن أفضل الوصفات..."):
                try:
                    selected_type = st.session_state.selected_type
                    max_time = st.session_state.max_time

                    recipes_info = candidates[["recipe_Id", "recipe_Nme", "ingredients_Items", "meal_Type", "max_Time"]].to_dict(orient="records")
                    recipes_json = json.dumps(recipes_info, indent=2, ensure_ascii=False)

                    system_prompt = (
    "You are an empathetic, smart culinary assistant. Your primary goal is to help a user who is confused about what to cook based on their available ingredients. "
    "You will receive a list of candidate recipes (already filtered by meal type and time) and the user's available ingredients.\n\n"
    "Your task is to select matching recipes from the candidates, rank them, and provide helpful, encouraging comments in Arabic.\n\n"
    "Follow these strict rules:\n"
    "1. **Hero Ingredient Analysis & Strict Matching**: Identify the 'hero' core ingredient of each recipe (e.g., Chicken in Kabsa, Ful in Ful Medames, Eggs in Shakshuka). "
    "The user **MUST** possess this hero ingredient in their provided ingredients list.\n"
    "2. **Zero Tolerance for Missing Hero Ingredients**: If the user is missing the hero ingredient, REJECT the recipe entirely. "
    "**DO NOT** suggest the recipe and **DO NOT** suggest substitutes for a missing hero ingredient (e.g., never suggest Ful if they don't have Ful, and never say 'use lentils instead'). If they don't have the hero ingredient, the recipe is invalid.\n"
    "3. **Ignore Staples for Matching**: Salt, pepper, oil, garlic, onion, lemon juice, and water are auxiliary staples. Do not count them as hero ingredients.\n"
    "4. **Smart Ranking & Flexible Count**: Rank the selected recipes from most matching to least matching. "
    "**IMPORTANT**: Return a MAXIMUM of 5 recipes. If only 1, 2, or 3 recipes strictly match the criteria (having the hero ingredient), return *only* those. Do not force 5 recipes by including invalid ones.\n"
    "5. **Empathetic Arabic Comments**: For each valid selected recipe, write a warm, encouraging comment in Arabic. Use natural, grammatically correct Modern Standard Arabic or a warm, widely understood colloquial tone — avoid awkward literal phrasing. Acknowledge what they have, explain why it's a logical choice, and suggest simple alternatives *only* for missing non-hero ingredients (like spices or secondary toppings).\n\n"
    "OUTPUT FORMAT:\n"
    "You must return ONLY a raw JSON array of objects. Do not wrap the JSON in markdown blocks (e.g., do not use ```json). Do not add any conversational text before or after the JSON.\n"
    "Each object must have strictly two keys:\n"
    "- 'recipe_Id': (integer) the ID of the recipe.\n"
    "- 'comment': (string) your empathetic Arabic comment.\n\n"
    "Example Output:\n"
    "مهم جدا فكرة وجود المكون الاساسي لن لم يكن موجوده لا تقترح الوصفة ابدا. مثال: إذا لم يكن لديك الدجاج، لا تقترح الكبسة ولا تقول استخدم العدس بدلا من الدجاج.  لكن بناء على نوع الوجبة التي اختارها المستخدم مثلا فطور غداء او عشاء قدم الاقتراحات على اساس انهك تعطي له افكار لوجبات يمكن ان يحضرها بناء على وجود مكونات قريبة من المكونات التي لديه مثلا عرفت ان المستخدم يريد وجبة فطور لديه بيض و زيت اقترح عليه الشكشوكة مثلا ولكن لا تقترح عليه سندويشه فلافل لانها ليس لها علاقة بالمكونات وبافكار انك تعطيه وصفات قريبة من المكونات التي لديه. مثال على مخرجاتك يجب ان تكون هكذا"
    '[{"recipe_Id": 12, "comment": "خيار ممتاز! تتوفر لديك الدجاج والأرز، وهما أساس الكبسة. ينقصك فقط قليل من البهارات ويمكنك استبدالها بما هو متوفر لديك. بالتوفيق في تحضيرها!"}]'
)
                    user_prompt = (
                        f"اختار المستخدم نوع الوجبة: {selected_type}. "
                        f"الحد الأقصى للوقت: {max_time} دقيقة. "
                        f"المكونات المتوفرة لدى المستخدم: {user_items}. "
                        f"إليك الوصفات المرشحة (كل وصفة تحتوي على المعرف، الاسم، المكونات، نوع الوجبة، والوقت الأقصى):\n\n{recipes_json}"
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
                            except Exception:
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
                        st.warning("🤔 لم يجد الذكاء الاصطناعي تطابقاً كاملاً، ولكن إليك بعض الاقتراحات بناءً على مكوناتك.")
                        user_meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                        def simple_score(row):
                            recipe_ings = re.split(r'[،,]', str(row["ingredients_Items"]))
                            recipe_meaningful = [i.strip() for i in recipe_ings if i.strip() not in PANTRY_ITEMS]
                            return len(set(user_meaningful) & set(recipe_meaningful))
                        candidates = candidates.copy()
                        candidates["score"] = candidates.apply(simple_score, axis=1)
                        candidates = candidates.sort_values("score", ascending=False)
                        def gen_comment(row):
                            recipe_ings = re.split(r'[،,]', str(row["ingredients_Items"]))
                            meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                            matched = set(meaningful) & set(recipe_ings)
                            if not meaningful:
                                return "لم تختر أي مكونات جوهرية."
                            pct = len(matched) / len(meaningful) * 100
                            return match_comment(pct)
                        candidates["comment"] = candidates.apply(gen_comment, axis=1)
                        results = candidates.head(5).copy()

                    # Ensure exactly 5
                    if len(results) < 5 and not candidates.empty:
                        used_ids = set(results["recipe_Id"].astype(str))
                        remaining = candidates[~candidates["recipe_Id"].astype(str).isin(used_ids)]
                        if not remaining.empty:
                            user_meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                            def simple_score(row):
                                recipe_ings = re.split(r'[،,]', str(row["ingredients_Items"]))
                                recipe_meaningful = [i.strip() for i in recipe_ings if i.strip() not in PANTRY_ITEMS]
                                return len(set(user_meaningful) & set(recipe_meaningful))
                            remaining = remaining.copy()
                            remaining["score"] = remaining.apply(simple_score, axis=1)
                            remaining = remaining.sort_values("score", ascending=False)
                            needed = 5 - len(results)
                            extra = remaining.head(needed)
                            def gen_comment(row):
                                recipe_ings = re.split(r'[،,]', str(row["ingredients_Items"]))
                                meaningful = [i for i in user_items if i not in PANTRY_ITEMS]
                                matched = set(meaningful) & set(recipe_ings)
                                if not meaningful:
                                    return "لم تختر أي مكونات جوهرية."
                                pct = len(matched) / len(meaningful) * 100
                                return match_comment(pct)
                            extra["comment"] = extra.apply(gen_comment, axis=1)
                            results = pd.concat([results, extra], ignore_index=True)

                    st.session_state.results = results
                    st.session_state.stage = "results"
                    st.balloons()
                    st.rerun()

                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}. يرجى المحاولة مرة أخرى أو تعديل المدخلات.")
                    st.stop()

    with col2:  # العمود الأيسر – زر الرجوع
        if st.button("⬅ رجوع", use_container_width=True, key="back_ingredients"):
            st.session_state.stage = "meal_type"
            st.rerun()

    if st.session_state.error_msg:
        st.warning(st.session_state.error_msg)

# ---------------------------------------------------------------------------
# STAGE 3: NO MATCH
# ---------------------------------------------------------------------------
elif st.session_state.stage == "no_match":
    render_steps("ingredients")
    st.warning("😕 لم يتم العثور على وصفات تطابق نوع الوجبة والوقت اللذين اخترتهما.")
    st.caption("جرّب تعديل نوع الوجبة أو الوقت المتاح، ثم حاول مجدداً.")
    if st.button("⬅ ابدأ من جديد", use_container_width=True):
        st.session_state.stage = "meal_type"
        st.rerun()

# ---------------------------------------------------------------------------
# STAGE 4: RESULTS (with Bar Chart)
# ---------------------------------------------------------------------------
elif st.session_state.stage == "results":
    render_steps("results")
    st.subheader("🏆 أفضل الوصفات المقترحة لك")
    results = st.session_state.results

    if results.empty:
        st.warning("لم يتم العثور على وصفات تطابق معاييرك. جرّب تعديل المكونات أو نوع الوجبة.")
        if st.button("⬅ جرّب مكونات مختلفة"):
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
                safe_show_image(recipe.get("pics"), width=140)
                st.markdown("</div><div style='flex:3;'>", unsafe_allow_html=True)
                st.markdown(f"### {recipe['recipe_Nme']}")
                st.caption(f"{recipe['meal_Type']} · {recipe['max_Time']} دقيقة")
                comment = recipe.get("comment", "")
                if comment:
                    st.info(f"💬 {comment}")
                ings = [i.strip() for i in re.split(r'[،,]', str(recipe["ingredients_Items"])) if i.strip()]
                tag_html = " ".join([f"<span class='ingredient-tag'>{i}</span>" for i in ings[:6]])
                st.markdown(tag_html, unsafe_allow_html=True)
                if len(ings) > 6:
                    st.caption(f"+{len(ings)-6} مكونات إضافية")

                if st.button("👨‍🍳 اختر هذه الوصفة", key=f"choose_{recipe['recipe_Id']}"):
                    st.session_state.selected_recipe = recipe
                    st.session_state.stage = "detail"
                    st.rerun()
                st.markdown("</div></div></div>", unsafe_allow_html=True)

        # ---- BAR CHART: مقارنة أوقات الطهي (محسّن) ----
        if len(results) >= 2:
            st.markdown("---")
            st.subheader("⏱️ مقارنة أوقات الطهي")

            # ترتيب البيانات تصاعدياً حسب الوقت
            sorted_data = results[["recipe_Nme", "max_Time"]].copy()
            sorted_data = sorted_data.sort_values("max_Time")

            # تدرج لوني مستوحى من ألوان التطبيق (برتقالي)
            cmap = plt.cm.Oranges
            norm = plt.Normalize(vmin=sorted_data["max_Time"].min(), vmax=sorted_data["max_Time"].max())
            colors = [cmap(norm(val)) for val in sorted_data["max_Time"]]

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(sorted_data["recipe_Nme"], sorted_data["max_Time"], color=colors)

            # إضافة قيم الوقت أعلى الأعمدة
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f'{height} دقيقة',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=10)

            ax.set_xlabel("الوصفة", fontsize=12)
            ax.set_ylabel("الوقت (دقيقة)", fontsize=12)
            ax.set_title("مقارنة أوقات الطهي", fontsize=14)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            st.pyplot(fig)

        if st.button("⬅ جرّب مكونات مختلفة", use_container_width=True):
            st.session_state.stage = "ingredients"
            st.rerun()

# ---------------------------------------------------------------------------
# STAGE 5: DETAIL (with Pie Chart)
# ---------------------------------------------------------------------------
elif st.session_state.stage == "detail":
    render_steps("results")
    recipe = st.session_state.selected_recipe
    user_items = st.session_state._last_user_items

    # Handle virtual recipes (from wizard)
    is_virtual = recipe.get("is_virtual", False)
    if is_virtual:
        st.info("🍽️ هذه الوصفة تم اقتراحها بواسطة المساعد الذكي، وهي ليست من قاعدة البيانات.")
        # For virtual recipes, we don't have a pics URL, so we show a placeholder.
        # Also, we set user_items to empty list if not available.
        if not user_items:
            user_items = []

    recipe_ingredients_display = ', '.join(
        [i.strip() for i in re.split(r'[،,]', str(recipe['ingredients_Items'])) if i.strip()]
    )

    st.markdown(f"""
        <div style="background:white; border-radius:20px; padding:1.5rem; box-shadow:0 8px 24px rgba(0,0,0,0.08);">
            <h2 style="color:#4a3728;">🍽️ {recipe['recipe_Nme']}</h2>
            <p><strong>نوع الوجبة:</strong> {recipe['meal_Type']}  |  <strong>الوقت اللازم:</strong> {recipe['max_Time']} دقيقة</p>
            <p><strong>المكونات:</strong> {recipe_ingredients_display}</p>
    """, unsafe_allow_html=True)

    comment = recipe.get("comment", "")
    if comment:
        st.info(f"💬 {comment}")

    safe_show_image(recipe.get("pics"), use_container_width=True)

    st.markdown("---")

    # ---- PIE CHART: جاهزية المكونات (only if we have user_items) ----
    if user_items:
        st.subheader("📊 مدى توفر المكونات")
        recipe_items = [i.strip() for i in re.split(r'[،,]', str(recipe["ingredients_Items"])) if i.strip()]
        missing = [i for i in recipe_items if i not in user_items and i not in PANTRY_ITEMS]

        total = len(recipe_items)
        available = total - len(missing)

        if total > 0:
            fig, ax = plt.subplots(figsize=(6, 4))
            colors = ['#8fb88e', '#e07c5e']
            if len(missing) == 0:
                sizes = [1, 0]
                labels = ['✅ جميع المكونات متوفرة', '']
                colors = ['#8fb88e', '#f0e3dc']
            else:
                sizes = [available, len(missing)]
                labels = [f'✅ متوفرة ({available})', f'❌ ناقصة ({len(missing)})']

            ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                colors=colors,
                startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2},
                textprops={'fontsize': 12}
            )
            ax.set_title("المكونات المتوفرة مقابل الناقصة", fontsize=14, fontweight='bold')
            st.pyplot(fig)

            if len(missing) == 0:
                st.success("🎉 تتوفر لديك جميع المكونات! لا حاجة للتسوق.")
            else:
                st.info(f"ℹ️ تتوفر لديك {available} من أصل {total} مكوّناً. تابع للأسفل لرؤية البدائل المقترحة أو قائمة المشتريات.")
        else:
            st.caption("لا توجد مكونات لعرضها.")
    else:
        st.info("📝 لم يتم تحديد مكونات محددة لهذه الوصفة المقترحة، ولكن يمكنك الاطلاع على خطوات التحضير أدناه.")

    st.markdown("---")

    # ---- FEATURE 1: INSTRUCTIONS (بالعربية) ----
    if st.button("📖 أرني طريقة التحضير"):
        with st.spinner("🧑‍🍳 الذكاء الاصطناعي يكتب لك خطوات التحضير..."):
            try:
                instruction_prompt = (
                    f"اكتب دليل طبخ خطوة بخطوة للوصفة '{recipe['recipe_Nme']}'. "
                    f"المكونات هي: {recipe['ingredients_Items']}. "
                    f"{f'المستخدم لديه بالفعل هذه المكونات: {user_items}.' if user_items else ''} "
                    f"إذا كان ينقصه شيء، اذكره باختصار. اجعل الدليل عملياً وسهل المتابعة، وباللغة العربية الفصحى الواضحة أو بلهجة مفهومة للجميع."
                )
                resp = client.chat.completions.create(
                    model="deepseek/deepseek-chat",
                    messages=[
                        {"role": "system", "content": "أنت مساعد طبخ مفيد. قدّم خطوات مرقّمة وواضحة بلغة عربية سليمة."},
                        {"role": "user", "content": instruction_prompt}
                    ],
                    max_tokens=800,
                    temperature=0.5,
                )
                st.session_state._instructions = resp.choices[0].message.content
                st.rerun()
            except Exception as e:
                st.error(f"تعذّر جلب خطوات التحضير: {e}")

    if st.session_state._instructions:
        with st.expander("📖 خطوات التحضير", expanded=True):
            st.write(st.session_state._instructions)
        if st.button("مسح خطوات التحضير"):
            st.session_state._instructions = ""
            st.rerun()

    st.markdown("---")

    # ---- FEATURE 2: SUBSTITUTIONS & SHOPPING LIST (only if we have missing items) ----
    if user_items:
        recipe_items = [i.strip() for i in re.split(r'[،,]', str(recipe["ingredients_Items"])) if i.strip()]
        missing = [i for i in recipe_items if i not in user_items and i not in PANTRY_ITEMS]

        if missing:
            if st.button("🔄 اقترح بدائل للمكونات الناقصة"):
                with st.spinner("🔍 جارٍ البحث عن بدائل مناسبة..."):
                    try:
                        sub_prompt = (
                            f"المستخدم يحضّر '{recipe['recipe_Nme']}'. "
                            f"المكونات الناقصة لديه هي: {missing}. "
                            f"اقترح بدائل شائعة وسهلة لكل مكون ناقص. "
                            f"الصيغة: 'المكوّن X ← استخدم Y بدلاً منه (السبب)'. اجعل الإجابة مختصرة وباللغة العربية."
                        )
                        resp = client.chat.completions.create(
                            model="deepseek/deepseek-chat",
                            messages=[
                                {"role": "system", "content": "أنت مساعد طبخ مفيد. قدّم بدائل عملية بلغة عربية سليمة."},
                                {"role": "user", "content": sub_prompt}
                            ],
                            max_tokens=400,
                            temperature=0.4,
                        )
                        st.session_state._subs = resp.choices[0].message.content
                        st.rerun()
                    except Exception as e:
                        st.error(f"تعذّر جلب البدائل: {e}")

            if st.session_state._subs:
                with st.expander("🔄 البدائل المقترحة", expanded=True):
                    st.write(st.session_state._subs)
                if st.button("مسح البدائل"):
                    st.session_state._subs = ""
                    st.rerun()

            if st.button("🛒 عرض قائمة المشتريات (المكونات الناقصة)"):
                st.session_state._shopping_list = missing
                st.rerun()

            if st.session_state._shopping_list:
                with st.expander("🛒 قائمة المشتريات", expanded=True):
                    for item in st.session_state._shopping_list:
                        st.write(f"- {item}")
                if st.button("مسح قائمة المشتريات"):
                    st.session_state._shopping_list = []
                    st.rerun()
        else:
            st.success("✅ تتوفر لديك جميع المكونات! لا حاجة للتسوق.")

    st.markdown("---")

    # ---- YOUTUBE TUTORIAL ----
    query = recipe["recipe_Nme"].replace(" ", "+")
    youtube_url = f"https://www.youtube.com/results?search_query=طريقة+طبخ+{query}"
    st.link_button("🎥 ابحث عن فيديو تعليمي على يوتيوب", youtube_url, use_container_width=True)

    # ---- BACK BUTTON ----
    if st.button("⬅ العودة إلى النتائج", use_container_width=True):
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
    st.warning("هذه الصفحة لم تعد مستخدمة. يرجى العودة.")
    if st.button("⬅ رجوع"):
        st.session_state.stage = "detail"
        st.rerun()

# ---------------------------------------------------------------------------
# STAGE 7: DONE
# ---------------------------------------------------------------------------
elif st.session_state.stage == "done":
    st.success("🎉 بالهناء والشفاء! عد إلينا في أي وقت للحصول على إلهام جديد في الطبخ.")
    if st.button("⬅ ابحث عن وصفة أخرى"):
        st.session_state.stage = "meal_type"
        st.rerun()

# لتشغيل التطبيق:
# streamlit run app.py
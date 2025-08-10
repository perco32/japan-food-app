from flask import Flask, render_template, abort, session, redirect, url_for, request
import gspread
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# --- データ読み込み ---
try:
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open("japan_food_app_data")
    
    foods_sheet = spreadsheet.worksheet("foods")
    ui_texts_sheet = spreadsheet.worksheet("ui_texts")
    
    foods_data = foods_sheet.get_all_records()
    ui_records = ui_texts_sheet.get_all_records()

    foods_by_id = {food['id']: food for food in foods_data}

    ui_texts = {}
    languages = ui_texts_sheet.row_values(1)[1:]
    for lang in languages:
        ui_texts[lang] = {record['key']: record[lang] for record in ui_records}

except Exception as e:
    print(f"Error loading Google Sheet: {e}")
    foods_data, foods_by_id, ui_texts = [], {}, {}

# --- 言語設定とグローバル変数 ---
@app.route('/set_language', methods=['POST'])
def set_language():
    lang = request.form.get('language')
    if lang in ui_texts:
        session['language'] = lang
    next_url = request.form.get('next', url_for('home'))
    return redirect(next_url)

@app.context_processor
def inject_globals():
    lang = session.get('language', 'ja')
    return dict(
        ui=ui_texts.get(lang, ui_texts.get('en', {})),
        current_lang=lang,
        ui_texts=ui_texts
    )

# --- ルート定義 ---
@app.route('/')
def home():
    # ★★★ この行を修正しました ★★★
    top_level_foods = [food for food in foods_data if food['parent_id'] and int(food['parent_id']) == 100]
    return render_template('index.html', foods=top_level_foods)

@app.route('/food/<int:food_id>')
def food_page(food_id):
    current_food = foods_by_id.get(food_id)
    if not current_food:
        abort(404)

    recipe_url_key = 'recipe_url_' + session.get('language', 'ja')

    if current_food.get(recipe_url_key):
        return redirect(current_food[recipe_url_key])
    
    # ★★★ この行を修正しました ★★★
    child_foods = [food for food in foods_data if food['parent_id'] and int(food['parent_id']) == food_id]
    
    return render_template('category_page.html', 
                           current_category=current_food,
                           child_categories=child_foods)
from flask import Flask, render_template, abort, session, redirect, url_for, request, jsonify
import gspread
import random
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# --- データ読み込みと前処理 ---
try:
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open("japan_food_app_data")
    
    categories_sheet = spreadsheet.worksheet("categories")
    dishes_sheet = spreadsheet.worksheet("dishes")
    ui_texts_sheet = spreadsheet.worksheet("ui_texts")
    
    categories_data = categories_sheet.get_all_records()
    dishes_data = dishes_sheet.get_all_records()
    ui_records = ui_texts_sheet.get_all_records()

    categories_by_id = {cat['category_id']: cat for cat in categories_data}
    dishes_by_id = {dish['dish_id']: dish for dish in dishes_data}

    ui_texts = {}
    languages = ui_texts_sheet.row_values(1)[1:]
    for lang in languages:
        ui_texts[lang] = {record['key']: record[lang] for record in ui_records}

except Exception as e:
    print(f"Error loading Google Sheet: {e}")
    categories_data, dishes_data, categories_by_id, dishes_by_id, ui_texts = [], [], {}, {}, {}

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
    top_level_categories = [cat for cat in categories_data if cat.get('parent_id') == 100]
    return render_template('index.html', categories=top_level_categories)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    found_dishes = []
    if query:
        lang = session.get('language', 'ja')
        tags_key = 'tags_' + lang
        
        found_dishes = [
            dish for dish in dishes_data 
            if query.lower() in dish.get(tags_key, '').lower()
        ]

    return render_template('search_results.html', 
                           query=query, 
                           dishes=found_dishes)

@app.route('/category/<int:category_id>')
def category_page(category_id):
    current_category = categories_by_id.get(category_id)
    if not current_category:
        abort(404)

    # ★★★ このロジックを修正 ★★★
    # 1. このカテゴリーを親として持つ「子カテゴリー」を探す
    child_categories = [cat for cat in categories_data if cat.get('parent_id') == category_id]
    
    # 2. このカテゴリーに直接属する「料理」を探す
    lang = session.get('language', 'ja')
    category_name_key = 'name_' + lang
    tags_key = 'tags_' + lang
    category_tag = current_category.get(category_name_key)
    
    dishes_in_category = []
    if category_tag:
        dishes_in_category = [
            dish for dish in dishes_data 
            if category_tag.lower() in dish.get(tags_key, '').lower()
        ]
        # さらに、その料理が他のサブカテゴリーに属していないことを確認
        dishes_in_category = [
            dish for dish in dishes_in_category
            if not any(tag in [c.get(category_name_key, '').lower() for c in child_categories] for tag in dish.get(tags_key, '').lower().split(', '))
        ]


    return render_template('category_page.html', 
                           current_category=current_category,
                           child_categories=child_categories,
                           dishes=dishes_in_category)

@app.route('/dish/<int:dish_id>')
def dish_detail(dish_id):
    dish = dishes_by_id.get(dish_id)
    if not dish:
        abort(404)
    
    lang = session.get('language', 'ja')
    tags_key = 'tags_' + lang
    dish_tags = [tag.strip() for tag in dish.get(tags_key, '').split(',')]
    parent_category = None
    
    # ★★★ 親カテゴリーを見つけるロジックを簡素化 ★★★
    # categories_dataから、この料理のタグに名前が一致する最初のカテゴリーを探す
    for cat in categories_data:
        if cat['name_ja'] in dish_tags or cat['name_en'] in dish_tags:
            # ただし、そのカテゴリーが子を持たない場合（最終階層）のみ親とする
            children_of_cat = [c for c in categories_data if c.get('parent_id') == cat['category_id']]
            if not children_of_cat:
                parent_category = cat
                break
            
    return render_template('dish_detail.html', 
                           dish=dish, 
                           parent_category=parent_category)


# --- APIルート定義 ---
@app.route('/api/restaurants/<int:dish_id>')
def get_restaurants(dish_id):
    dish_item = dishes_by_id.get(dish_id)
    
    lang = session.get('language', 'ja')
    restaurants_key = 'restaurants_' + lang
    
    restaurant_string = dish_item.get(restaurants_key)

    if not dish_item or not restaurant_string:
        return jsonify([])

    restaurant_list = [r.strip() for r in restaurant_string.split(';')]
    
    return jsonify(restaurant_list)
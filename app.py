# app.py

from flask import Flask, render_template, abort
import gspread

app = Flask(__name__)

# --- Googleスプレッドシートからデータを読み込む設定 ---
try:
    gc = gspread.service_account(filename='credentials.json')
    spreadsheet = gc.open("japan_food_app_data")
    worksheet = spreadsheet.sheet1
    # get_all_records()は、各行を辞書形式でリストに変換してくれる便利な関数
    dishes_data = worksheet.get_all_records()
except Exception as e:
    # もし認証やシートの読み込みでエラーが出た場合、空のリストにしておく
    print(f"Error loading Google Sheet: {e}")
    dishes_data = []
# ----------------------------------------------------

# カテゴリー名と画像のURLをマッピングする
category_images = {
    "Noodles": "https://images.unsplash.com/photo-1569718212165-d80b6a78f4b4?w=800",
    "Rice Dishes": "https://images.unsplash.com/photo-1596263952538-3151b721ac30?w=800",
    "Fried Dishes": "https://images.unsplash.com/photo-1628522791328-9a3e284432a5?w=800",
    "Grilled Dishes": "https://images.unsplash.com/photo-1598532437233-415b13517595?w=800",
    "Hot Pot / Simmered": "https://images.unsplash.com/photo-1631093512435-ac99a4c04909?w=800",
}

# --- ルート設定 ---

# ホームページ（料理一覧）
@app.route('/')
def home():
    # 全データの中から、category_largeの値だけを取り出す
    all_large_categories = [dish['category_large'] for dish in dishes_data]
    
    # 重複をなくしてユニークなリストにする
    # (例: ['Rice Dishes', 'Noodles', 'Fried Dishes', ...])
    unique_large_categories = sorted(list(set(all_large_categories)))

    # カテゴリーリストと全料理リストの両方をHTMLに渡す
    return render_template('index.html', 
                           dishes=dishes_data, 
                           categories=unique_large_categories,
                           images=category_images)

# カテゴリーページ（大分類）
@app.route('/category/<string:category_name>')
def category_page(category_name):
    # 大分類名で料理をフィルタリングする
    filtered_dishes = [dish for dish in dishes_data if dish['category_large'] == category_name]
    
    # --- このセクションを追加 ---
    # フィルタリングされたリストから、ユニークな中分類のリストを取得する
    all_medium_categories = [dish['category_medium'] for dish in filtered_dishes]
    unique_medium_categories = sorted(list(set(all_medium_categories)))
    # --- 追加セクションここまで ---

    # 中分類のリストをテンプレートに渡す
    return render_template('category_page.html', 
                           category_name=category_name, 
                           dishes=filtered_dishes,
                           medium_categories=unique_medium_categories) # これを追加

# 中分類ページ
@app.route('/category/<string:large_cat>/<string:medium_cat>')
def medium_category_page(large_cat, medium_cat):
    # 大分類と中分類の両方でフィルタリングする
    filtered_dishes = [
        dish for dish in dishes_data 
        if dish['category_large'] == large_cat and dish['category_medium'] == medium_cat
    ]
    
    # --- このセクションを追加 ---
    # フィルタリングされたリストから、ユニークな小分類のリストを取得する
    all_small_categories = [dish['category_small'] for dish in filtered_dishes]
    unique_small_categories = sorted(list(set(all_small_categories)))
    # --- 追加セクションここまで ---
    
    # 小分類のリストをテンプレートに渡す
    return render_template('medium_category_page.html', 
                           large_cat=large_cat,
                           medium_cat=medium_cat,
                           dishes=filtered_dishes,
                           small_categories=unique_small_categories) # これを追加

# 小分類ページ
@app.route('/category/<string:large_cat>/<string:medium_cat>/<string:small_cat>')
def small_category_page(large_cat, medium_cat, small_cat):
    # 大・中・小すべてのカテゴリーでフィルタリング
    filtered_dishes = [
        dish for dish in dishes_data 
        if dish['category_large'] == large_cat and \
           dish['category_medium'] == medium_cat and \
           dish['category_small'] == small_cat
    ]
    
    return render_template('small_category_page.html', 
                           large_cat=large_cat,
                           medium_cat=medium_cat,
                           small_cat=small_cat,
                           dishes=filtered_dishes)

# 料理詳細ページ
# <int:dish_id>の部分が、URLのIDを整数として受け取ることを意味する
@app.route('/dish/<int:dish_id>')
def dish_detail(dish_id):
    # スプレッドシートから読み込んだデータの中から、
    # URLのIDと一致するIDを持つ料理を探す
    found_dish = None
    for dish in dishes_data:
        if dish['id'] == dish_id:
            found_dish = dish
            break
    
    # もし一致する料理が見つからなかった場合
    if found_dish is None:
        # 404 Not Foundエラーを返す
        abort(404)
        
    # 見つかった料理のデータをdish_detail.htmlに渡して表示
    return render_template('dish_detail.html', dish=found_dish)
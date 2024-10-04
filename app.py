from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
import pytesseract
from PIL import Image
import requests
import sqlite3
import random
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 設定上傳目錄
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化資料庫
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS idioms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idiom TEXT,
            explanation TEXT,
            link TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 步驟一: 上傳圖片
@app.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('未找到檔案部分')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('沒有選擇檔案')
            return redirect(request.url)
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            return redirect(url_for('scan_image', file_path=file.filename))
    return render_template('upload.html')

# 步驟二、三: 掃描圖片並找出最大文字
@app.route('/scan/<file_path>', methods=['GET'])
def scan_image(file_path):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], file_path)
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='chi_tra')  # 使用繁體中文識別
        text_lines = [line for line in text.splitlines() if line.strip()]
        
        if not text_lines:
            flash('未掃描到任何文字')
            return redirect(url_for('upload_image'))
        
        max_text = max(text_lines, key=len)
        return render_template('scan.html', text_lines=text_lines, max_text=max_text)

    except Exception as e:
        flash(f'掃描圖片時發生錯誤: {str(e)}')
        return redirect(url_for('upload_image'))

# 步驟四: 列出掃描到的文字並提供全選功能
@app.route('/select', methods=['POST'])
def select_text():
    selected_texts = request.form.getlist('selected_texts')
    if not selected_texts:
        flash('沒有選擇任何文字')
        return redirect(url_for('upload_image'))
    
    return render_template('select.html', selected_texts=selected_texts)

# 步驟五: 傳送成語到教育部網站並回傳解釋
@app.route('/get_idiom', methods=['POST'])
def get_idiom():
    selected_texts = request.form.getlist('selected_texts')
    explanations = {}

    for text in selected_texts:
        try:
            # 真實請求教育部成語詞典查詢 API
            response = requests.get(f'https://dict.idioms.moe.edu.tw/idiomList.jsp?idiom={text}')
            if response.status_code == 200:
                explanation = extract_explanation_from_response(response.text)
                explanations[text] = explanation
            else:
                explanations[text] = "找不到解釋"
        except Exception as e:
            explanations[text] = f"請求發生錯誤: {str(e)}"
    
    return render_template('results.html', explanations=explanations)

def extract_explanation_from_response(response_text):
    # 真實提取解釋的過程
    # 可根據實際情況進行正則表達式或其他解析
    return "模擬解析到的解釋"

# 步驟六: 生成專屬連結並儲存到 SQLite 數據庫
@app.route('/generate_link', methods=['POST'])
def generate_link():
    selected_texts = request.form.getlist('selected_texts')
    explanations = request.form.getlist('explanations')
    
    # 隨機產生三個解釋或成語
    random_explanations = random.sample(explanations, 3)
    random_texts = random.sample(selected_texts, 3)
    
    try:
        # 存入資料庫
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        idiom = random.choice(selected_texts)
        explanation = random.choice(explanations)
        link = f"/card/{idiom}"
        c.execute('INSERT INTO idioms (idiom, explanation, link) VALUES (?, ?, ?)', (idiom, explanation, link))
        conn.commit()
        conn.close()

        return jsonify({'link': link})

    except Exception as e:
        flash(f'資料儲存錯誤: {str(e)}')
        return redirect(url_for('upload_image'))

# 生成成語小卡頁面
@app.route('/card/<idiom>', methods=['GET'])
def idiom_card(idiom):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT * FROM idioms WHERE idiom = ?', (idiom,))
    idiom_data = c.fetchone()
    conn.close()

    if idiom_data:
        return render_template('card.html', idiom=idiom_data[1], explanation=idiom_data[2])
    else:
        return "成語未找到", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000,debug=True)

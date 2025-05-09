from flask import Flask, request, jsonify
import sqlite3
import base64
import app

app = Flask(__name__)


def home():
    return "مرحبًا بك في تطبيق تسجيل الصوت"
@app.route('/')
@app.route('/record', methods=['POST'])
def record():
    if request.method == 'POST':
        audio_data = request.form.get('audio_data')
        voice_db = float(request.form.get('voice_db'))

        # إذا كانت درجة الصوت أعلى من الحد المعين، قم بتخزين الصوت في قاعدة البيانات
        if voice_db >= 10.0:
            audio_bytes = base64.b64decode(audio_data)

            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO audio_records (audio) VALUES (?)', (audio_bytes,))
            conn.commit()
            conn.close()

            return jsonify({"message": "تم تسجيل الصوت بنجاح"})
        else:
            return jsonify({"message": "درجة الصوت منخفضة جدًا ليتم تسجيلها"})



@app.route('/get_audio_records', methods=['GET'])
def get_audio_records():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT audio FROM audio_records')
    records = cursor.fetchall()
    conn.close()

    audio_records = []
    for record in records:
        audio_records.append({'audio': record[0]})

    return jsonify(audio_records)


if __name__ == '__main__':
    app.run(debug=True)

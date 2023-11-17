from flask import Flask,render_template,request,redirect,url_for,flash,jsonify,session,copy_current_request_context, render_template, make_response, Response
from flask_socketio import SocketIO, emit, disconnect
from threading import Lock
import sqlite3 as sql
import cv2

import json,locale, datetime

from random import choice, randint
from datetime import datetime, timedelta, date
from yolo_frame import video_detection
import mimetypes

mimetypes.add_type("application/javascript", ".js", True)

async_mode = None

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
# thread_lock = Lock()

locale.setlocale(locale.LC_NUMERIC, 'IND')

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html",sync_mode=socketio.async_mode)

@app.route('/fetchIndex/<string:sampah>', methods=['GET'])
def fetchIndex(sampah):
    con=sql.connect("sampah.db")

    qDistinctSampah = con.cursor().execute("select count(*), sampah from sampah group by sampah ORDER BY CASE sampah WHEN 'Bungkus Plastik' then 0 WHEN 'Kotak Karton' then 1 WHEN 'Botol Plastik' then 2 WHEN 'Kaleng' then 3 WHEN 'Styrofoam' then 4 END")
    dataTotalSampah = qDistinctSampah.fetchall()

    qDistinctAll = con.cursor().execute("select count(*) from sampah")
    totalSampah = qDistinctAll.fetchone()

    dataTotalSampah.append(totalSampah)
    
    if sampah == "tahun":
        whereString = "where strftime('%Y', tanggal) = strftime('%Y', 'now')"
    elif sampah == "bulan":
        whereString = "where strftime('%m', tanggal) = strftime('%m', 'now') AND strftime('%Y', tanggal) = strftime('%Y', 'now')"
    elif sampah == "hari":
        whereString = "where date(tanggal) = date(date('now'),'+1 day')"

    qGrafikSampah = con.cursor().execute("select count(*), sampah from sampah "+whereString+" group by sampah ORDER BY CASE sampah WHEN 'Bungkus Plastik' then 0 WHEN 'Kotak Karton' then 1 WHEN 'Botol Plastik' then 2 WHEN 'Kaleng' then 3 WHEN 'Styrofoam' then 4 END")
    dataGrafikSampah = qGrafikSampah.fetchall()

    message = {
            'totalPerSampah':[locale.format_string("%.*f", (0,data[0]), True) for data in dataTotalSampah],
            'grafikSampah':[data[0] for data in dataGrafikSampah]
    }

    return jsonify(message)

@socketio.on('socketEventIndex', namespace='/indexSocket')
def socketIndex():
    emit('indexSocketResponse', { 'totalPerSampah':0, 'grafikSampah':0 })

@app.route("/data")
def data():
    return render_template("data.html",sync_mode=socketio.async_mode)

@app.route('/fetchData', methods=['POST'])
def fetchData():
    con=sql.connect("sampah.db")

    currentPage = int(request.form['currentPage'])
    limitPage = int(request.form['limitPage'])

    statusFilter = int(request.form['statusFilter'])

    whereString = "";
    if statusFilter == 1:
        if len(request.form['filterJenisSampah'].replace("(", "").replace(")", "")) != 0:
            whereString = f"WHERE sampah IN {request.form['filterJenisSampah']}"
    elif statusFilter == 2:
        whereString = f"WHERE date(tanggal) BETWEEN {request.form['filterDateBetween']}"
    
    if int(request.form['statusPrint']) == 0:
        limitString = f"LIMIT {limitPage} OFFSET {((currentPage-1)*limitPage)}"
    else:
        limitString = ""

    qDataSampah = con.cursor().execute("select sampah, strftime('%d-%m-%Y %H:%M:%S',tanggal) from sampah "+whereString+" ORDER BY tanggal desc "+limitString).fetchall()
    qTotalDataSampah = con.cursor().execute("select count(*) from sampah "+whereString).fetchone()

    totalPages = qTotalDataSampah[0] // limitPage + (qTotalDataSampah[0] % limitPage > 0)

    startPage = max(1, min(currentPage - 2, totalPages - 4))
    endPage = min(totalPages, max(currentPage + 2, 5))
    pages = list(range(startPage, endPage + 1))

    pagination = ([{"value": '<i class="fa fa-angle-double-left"></i>',"disabled":True if currentPage == 1 else False,'to': 1},
             {"value": '<i class="fa fa-angle-left"></i>',"disabled":True if currentPage == 1 else False,'to': (currentPage-1) if currentPage != 1 else 1}] + 
             [{'value': page, 'active': page == currentPage,'to': page} for page in pages] + 
             [{"value": '<i class="fa fa-angle-right"></i>',"disabled":True if currentPage == totalPages else False,'to': currentPage+1},
              {"value": '<i class="fa fa-angle-double-right"></i>',"disabled":True if currentPage == totalPages else False,'to': totalPages}])

    message = {
        "data" : qDataSampah,
        "total" : qTotalDataSampah[0],
        "pagination" : pagination
    }

    return jsonify(message)

@socketio.on('socketEventData', namespace='/dataSocket')
def socketData():
    emit('dataSocketResponse', { 'data':0, 'total':0, 'pagination':0 })

@app.route("/kamera")
def kamera():
    return render_template("kamera.html")

@socketio.on('socketEventKamera', namespace='/kameraSocket')
def socketKamera():
    emit('kameraSocketResponse', { 'class':0 })

# camera = cv2.VideoCapture(0)
def gen_frames():  
    yolo_output = video_detection() 
    for detection_, class_name in yolo_output:
        socketio.emit('kameraSocketResponse', { 'class':class_name }, namespace="/kameraSocket")        
        ref,buffer=cv2.imencode('.jpg',detection_)
        frame=buffer.tobytes()
        yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame +b'\r\n') 

@app.route('/videoStream')
def videoStream():
    #Video streaming route. Put this in the src attribute of an img tag
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    # return "success"

def random_date(start, end):
    return start + timedelta(
        seconds=randint(0, int((end - start).total_seconds())))

@app.route("/dummySampah",methods=['GET'])
def dummySampah():
    # Make a PDF straight from HTML in a string.

    # jenis_sampah = ['Bungkus Plastik', 'Kotak Karton', 'Botol Plastik', 'Kaleng', 'Styrofoam']
    # start = datetime(2022, 1, 1, 0, 0, 0) 
    # end = datetime(2023, 11, 14, 23, 59, 59)
    # with app.app_context():
    #     con=sql.connect("sampah.db")
    #     cur=con.cursor()
    #     for _ in range(1000):            
    #         cur.execute('INSERT INTO sampah (sampah,tanggal) VALUES (?,?)', (choice(jenis_sampah),random_date(start, end)))
    #     con.commit()
    # socketio.emit('indexSocketResponse', {"status":"refreshed"}, namespace="/indexSocket")
    # socketio.emit('dataSocketResponse', {"status":"refreshed"}, namespace="/dataSocket")
    return "success"


if __name__=='__main__':
    socketio.run(app, debug=True)


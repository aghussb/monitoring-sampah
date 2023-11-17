import sqlite3 as sql

#connect to SQLite
con = sql.connect('sampah.db')

#Create a Connection
cur = con.cursor()

#Drop sampah table if already exsist.
cur.execute("DROP TABLE IF EXISTS sampah")

#Create sampah table  in db_web database
sql ='''CREATE TABLE "sampah" (
	"uid"	INTEGER PRIMARY KEY AUTOINCREMENT,
	"sampah"	TEXT,
	"tanggal"	DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
)'''
cur.execute(sql)

#commit changes
con.commit()

#close the connection
con.close()
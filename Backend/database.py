import mysql.connector 
from mysql.connector import errorcode
import sys


def datbase_connection():
    try:
        mydb=mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="Deevia@123",
            database="jsw_intrusion")
        return mydb

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            sys.exit("Username/Password Error!")
        elif err.errno==errorcode.ER_BAD_DB_ERROR:
            sys.exit("Database does not exist")
        else :
            sys.exit(err)
    else:
        print("[!] Connection Established Succesfully With DataBase")
        


def getQuery(my_cursor, start_date=None, end_date=None):
    try:
        # q = f"SELECT * FROM jsw_intrusion.detect_intrusion where jsw_intrusion.detect_intrusion.date_time >= '{start_date}' AND jsw_intrusion.detect_intrusion.date_time <= '{end_date}';"
        q = f"SELECT * FROM jsw_intrusion.detect_intrusion where jsw_intrusion.detect_intrusion.date_time >= '{start_date}' AND jsw_intrusion.detect_intrusion.date_time <= '{end_date}' LIMIT 150000;"
        my_cursor.execute(q) 
        result = my_cursor.fetchall()
        if not result:
            print("Database not found") 
        # print("Database output: ", result)
        return result
        
    except mysql.connector.Error as err:
            print(err)


def getTotalData(self, start_date=None, end_date=None):
        try:
            q = f"SELECT count(*) FROM jsw_intrusion.detect_intrusion where jsw_intrusion.detect_intrusion.date_time >= '{start_date}' AND jsw_intrusion.detect_intrusion.date_time <= '{end_date}';"
            self.my_cursor.execute(q) 
            result = self.my_cursor.fetchall()
            if not result:
                print("Database not found") 
            # print("Database output: ", result)
            return result
        except:
            print("Unable to read data from database")
            print("Trying to reconnect database...")
            self.connect_db()
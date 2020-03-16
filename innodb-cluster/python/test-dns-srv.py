import mysql.connector
import time




def connection_source():
  query = ("select host FROM information_schema.PROCESSLIST WHERE id=CONNECTION_ID();")
  mysql_query(query)

def group_replication():
  query = ("SELECT *, if(member_host=@@hostname, 'HERE','') AS LOCAL FROM performance_schema.replication_group_members")
  mysql_query(query)

def mysql_query(query):
  try:
    #  cnx = mysql.connector.connect(user='root', password='mysql', host='mysql-router-1', port=6446,)
      cnx = mysql.connector.connect(user='root', password='mysql', host='database-router-rw.service.consul', dns_srv=True, connection_timeout=10)
#      cnx = mysql.connector.connect(user='root', password='mysql', host='database-router-rw.service.consul', dns_srv=True)
      cursor = cnx.cursor()

      cursor.execute(query)
      for (hostname) in cursor:
        print (hostname)
      cursor.close()
      cnx.close()
  except mysql.connector.Error as e:
      print("Error code:", e.errno)        # error number
      print("SQLSTATE value:", e.sqlstate) # SQLSTATE value
      print("Error message:", e.msg)       # error message
      print("Error:", e)                   # errno, sqlstate, msg values
  except Exception as e:
      print("Unexpected error:", e)

connection_source()
group_replication()

while True:
    start_time = time.time()
    connection_source()
    elapsed_time = time.time() - start_time
    print("Time taken: ", elapsed_time)
#    group_replication()
    time.sleep(1)

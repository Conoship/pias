import sqlite3


def get_local_conn():
    return sqlite3.connect("localhost.db")

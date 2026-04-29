import sqlite3


def get_local_conn():
    return sqlite3.connect("localhost.db")


def create_layout_tables(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ship (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ship_version (
                id INTEGER PRIMARY KEY,
                ship_id INTEGER NOT NULL,
                design_name TEXT NOT NULL,
                version TEXT NOT NULL,
                subversion TEXT NOT NULL,
                ship_run TEXT NOT NULL,
                FOREIGN KEY (ship_id) REFERENCES ship(id) ON DELETE CASCADE,
                UNIQUE (ship_id, design_name, version, subversion, ship_run)
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_category (
                id INTEGER PRIMARY KEY,
                design_content_id_number INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compartment (
                id INTEGER PRIMARY KEY,
                ship_version_id INTEGER NOT NULL,
                xml_comparment_id INTEGER,
                xml_compartment_guid TEXT,
                name TEXT NOT NULL,
                selected_for_output INTEGER NOT NULL,
                design_content_id_number INTEGER,
                FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE,
                FOREIGN KEY (design_content_id_number) REFERENCES content_category(design_content_id_number) ON DELETE SET NULL
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcompartment (
                id INTEGER PRIMARY KEY,
                compartment_id INTEGER NOT NULL,
                shape_guid TEXT,
                subcompartment_guid TEXT,
                sign INTEGER,
                permeability_for_damage_stability REAL,
                is_pipe INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (compartment_id) REFERENCES compartment(id) ON DELETE CASCADE
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcompartment_shape (
                id INTEGER PRIMARY KEY,
                ship_version_id INTEGER NOT NULL,
                shape_guid TEXT NOT NULL,
                side TEXT,
                FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frustum_point (
                id INTEGER PRIMARY KEY,
                subcompartment_shape_id INTEGER NOT NULL,
                aftfwd_and_num TEXT,
                L REAL,
                B REAL,
                H REAL,
                FOREIGN KEY (subcompartment_shape_id) REFERENCES subcompartment_shape(id) ON DELETE CASCADE
            )
            """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opening (
                id INTEGER PRIMARY KEY,
                ship_version_id INTEGER NOT NULL,
                compartment_id INTEGER,
                description TEXT NOT NULL,
                opening_type TEXT,
                L REAL,
                B REAL,
                H REAL,
                FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE,
                FOREIGN KEY (compartment_id) REFERENCES compartment(id) ON DELETE SET NULL
            )
            """)
        conn.commit()
    except Exception as e:
        print(e)


if __name__ == "__main__":
    conn = get_local_conn()
    create_layout_tables(conn)
    conn.close()
    print("Tables created successfully.")
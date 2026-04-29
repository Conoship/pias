import sqlite3


def get_local_conn():
    conn = sqlite3.connect("localhost.db")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_layout_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()

    try:
        # ------------------------------------------------------------------
        # SHIP & DESIGN
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ship (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ship_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_id INTEGER NOT NULL,
                design_name TEXT NOT NULL,
                version TEXT NOT NULL,
                subversion TEXT NOT NULL,
                ship_run TEXT NOT NULL,
                FOREIGN KEY (ship_id)
                    REFERENCES ship(id)
                    ON DELETE CASCADE,
                UNIQUE (
                    ship_id,
                    design_name,
                    version,
                    subversion
                )
            )
        """)

        # ------------------------------------------------------------------
        # MAIN DIMENSIONS
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS main_dimensions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,
                lpp REAL,
                loa REAL,
                breadth REAL,
                depth REAL,
                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------------------------------
        # CONTENT CATEGORY
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                design_content_id_number INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL
            )
        """)

        # ------------------------------------------------------------------
        # COMPARTMENTS
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compartment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,
                xml_comparment_id INTEGER,
                xml_compartment_guid TEXT,
                name TEXT NOT NULL,
                selected_for_output INTEGER NOT NULL,
                design_content_id_number INTEGER,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (design_content_id_number)
                    REFERENCES content_category(design_content_id_number)
                    ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcompartment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compartment_id INTEGER NOT NULL,
                shape_guid TEXT,
                subcompartment_guid TEXT,
                sign INTEGER,
                permeability_for_damage_stability REAL,
                is_pipe INTEGER NOT NULL DEFAULT 0,

                FOREIGN KEY (compartment_id)
                    REFERENCES compartment(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcompartment_shape (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,
                shape_guid TEXT NOT NULL,
                side TEXT,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frustum_point (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subcompartment_shape_id INTEGER NOT NULL,
                aftfwd_and_num TEXT,
                L REAL,
                B REAL,
                H REAL,

                FOREIGN KEY (subcompartment_shape_id)
                    REFERENCES subcompartment_shape(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------------------------------
        # OPENINGS
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opening (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,
                compartment_id INTEGER,

                description TEXT NOT NULL,

                length REAL,
                breadth REAL,
                height REAL,

                opening_type TEXT,
                connected_compartment TEXT,

                L REAL,
                B REAL,
                H REAL,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (compartment_id)
                    REFERENCES compartment(id)
                    ON DELETE SET NULL
            )
        """)

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Error creating layout tables: {e}")


def create_stability_tables(conn: sqlite3.Connection):
    cursor = conn.cursor()

    try:
        # ------------------------------------------------------------------
        # TRIM / GM
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trim_gm (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,
                condition_name TEXT NOT NULL,

                draft REAL,
                trim REAL,
                vcg REAL,
                mg REAL,
                displacement REAL,

                attained_index REAL,
                required_index REAL,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE,

                UNIQUE (ship_version_id, condition_name)
            )
        """)

        # ------------------------------------------------------------------
        # PROBDAM CASE
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS probdam_case (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,

                side TEXT,
                damage_case TEXT NOT NULL,

                aft_boundary REAL,
                fwd_boundary REAL,
                inside_boundary REAL,
                upper_boundary REAL,

                pi_tlight REAL,
                si_tlight REAL,

                pi_tpartial REAL,
                si_tpartial REAL,

                pi_tdeepest REAL,
                si_tdeepest REAL,

                ai REAL,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------------------------------
        # PROBDAM TOTAL
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS probdam_total (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,

                side TEXT,

                total_pi_tlight REAL,
                total_pi_tpartial REAL,
                total_pi_tdeepest REAL,

                total_ai REAL,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------------------------------
        # PROBDAM CONCLUSION
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS probdam_conclusion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,

                subdivision_length REAL,
                required_index REAL,
                attained_index REAL,

                complies INTEGER NOT NULL,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------------------------------
        # NUMINT CASE
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS numint_case (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,

                damage_case TEXT NOT NULL,

                pi_tlight REAL,
                si_tlight REAL,

                pi_tpartial REAL,
                si_tpartial REAL,

                pi_tdeepest REAL,
                si_tdeepest REAL,

                ai REAL,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------------------------------
        # NUMINT CONCLUSION
        # ------------------------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS numint_conclusion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ship_version_id INTEGER NOT NULL,

                subdivision_length REAL,
                required_index REAL,
                attained_index REAL,

                complies INTEGER NOT NULL,

                step_accuracy INTEGER,
                penetration_reference TEXT,

                FOREIGN KEY (ship_version_id)
                    REFERENCES ship_version(id)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Error creating stability tables: {e}")


def create_indexes(conn: sqlite3.Connection):
    cursor = conn.cursor()

    try:
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_ship_version_ship_id ON ship_version(ship_id)",

            "CREATE INDEX IF NOT EXISTS idx_main_dim_ship_version_id ON main_dimensions(ship_version_id)",

            "CREATE INDEX IF NOT EXISTS idx_compartment_ship_version_id ON compartment(ship_version_id)",
            "CREATE INDEX IF NOT EXISTS idx_compartment_design_content_id ON compartment(design_content_id_number)",

            "CREATE INDEX IF NOT EXISTS idx_subcompartment_compartment_id ON subcompartment(compartment_id)",

            "CREATE INDEX IF NOT EXISTS idx_subcompartment_shape_ship_version_id ON subcompartment_shape(ship_version_id)",

            "CREATE INDEX IF NOT EXISTS idx_frustum_point_subcompartment_shape_id ON frustum_point(subcompartment_shape_id)",

            "CREATE INDEX IF NOT EXISTS idx_opening_ship_version_id ON opening(ship_version_id)",
            "CREATE INDEX IF NOT EXISTS idx_opening_compartment_id ON opening(compartment_id)",

            "CREATE INDEX IF NOT EXISTS idx_probdam_case_ship_version_id ON probdam_case(ship_version_id)",
            "CREATE INDEX IF NOT EXISTS idx_probdam_total_ship_version_id ON probdam_total(ship_version_id)",
            "CREATE INDEX IF NOT EXISTS idx_probdam_conclusion_ship_version_id ON probdam_conclusion(ship_version_id)",

            "CREATE INDEX IF NOT EXISTS idx_trim_gm_ship_version_id ON trim_gm(ship_version_id)",

            "CREATE INDEX IF NOT EXISTS idx_numint_case_ship_version_id ON numint_case(ship_version_id)",
            "CREATE INDEX IF NOT EXISTS idx_numint_conclusion_ship_version_id ON numint_conclusion(ship_version_id)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"Error creating indexes: {e}")


def create_all_tables(conn: sqlite3.Connection):
    create_layout_tables(conn)
    create_stability_tables(conn)
    create_indexes(conn)


if __name__ == "__main__":
    conn = get_local_conn()

    create_all_tables(conn)

    conn.close()

    print("All SQLite tables and indexes created successfully.")

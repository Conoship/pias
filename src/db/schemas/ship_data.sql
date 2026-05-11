/* SHIP & DESIGN */
-- taken from file name
CREATE TABLE IF NOT EXISTS ship (id SERIAL PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ship_version (
  id SERIAL PRIMARY KEY,
  ship_id INTEGER NOT NULL,
  design_name TEXT NOT NULL,
  version TEXT NOT NULL,
  subversion TEXT NOT NULL,
  ship_run TEXT NOT NULL FOREIGN KEY (ship_id) REFERENCES ship(id) ON DELETE CASCADE,
  UNIQUE (ship_id, design_name, version, subversion)
);
/* MAIN DIMENSIONS */
CREATE TABLE IF NOT EXISTS main_dimensions (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  lpp REAL,
  loa REAL,
  breadth REAL,
  depth REAL,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS trim_gm (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  condition_name TEXT NOT NULL,
  draft REAL,
  trim REAL,
  vcg REAL,
  mg REAL,
  displacement REAL,
  attained_index REAL,
  required_index REAL,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE,
  UNIQUE (ship_version_id, condition_name)
);
/* LAYOUT */
-- taken from <ship>.fromLayout.xml
CREATE TABLE IF NOT EXISTS content_category (
  id SERIAL PRIMARY KEY,
  design_content_id_number INTEGER NOT NULL UNIQUE,
  name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compartment (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  xml_comparment_id INTEGER,
  xml_compartment_guid TEXT,
  name TEXT NOT NULL,
  selected_for_output BOOLEAN NOT NULL,
  design_content_id_number INTEGER,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE,
  FOREIGN KEY (design_content_id_number) REFERENCES content_category(design_content_id_number) ON DELETE
  SET NULL
);
CREATE TABLE IF NOT EXISTS subcompartment (
  id SERIAL PRIMARY KEY,
  compartment_id INTEGER NOT NULL,
  shape_guid TEXT,
  subcompartment_guid TEXT,
  sign INTEGER,
  permeability_for_damage_stability REAL,
  is_pipe BOOLEAN NOT NULL DEFAULT FALSE,
  FOREIGN KEY (compartment_id) REFERENCES compartment(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS subcompartment_shape (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  shape_guid TEXT NOT NULL,
  side TEXT,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS frustum_point (
  id SERIAL PRIMARY KEY,
  subcompartment_shape_id INTEGER NOT NULL,
  aftfwd_and_num TEXT,
  L REAL,
  B REAL,
  H REAL,
  FOREIGN KEY (subcompartment_shape_id) REFERENCES subcompartment_shape(id) ON DELETE CASCADE
);
/* OPENINGS */
-- taken from <ship>_openings.pdf
CREATE TABLE IF NOT EXISTS opening (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  compartment_id INTEGER,
  description TEXT NOT NULL,
  length REAL,
  breadth REAL,
  height REAL,
  opening_type TEXT,
  connected_compartment TEXT,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE,
  FOREIGN KEY (compartment_id) REFERENCES compartment(id) ON DELETE
  SET NULL
);
/* DAMAGE STABILITY */
-- taken from <ship>_probdam.pdf
-- probdam damage case
CREATE TABLE IF NOT EXISTS probdam_case(
  id SERIAL PRIMARY KEY,
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
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id)
);
CREATE TABLE IF NOT EXISTS probdam_total (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  side TEXT,
  total_pi_tlight REAL,
  total_pi_tpartial REAL,
  total_pi_tdeepest REAL,
  total_ai REAL,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id)
);
CREATE TABLE IF NOT EXISTS probdam_conclusion (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  subdivision_length REAL,
  required_index REAL,
  attained_index REAL,
  complies BOOLEAN NOT NULL,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id)
);
CREATE TABLE IF NOT EXISTS numint_case (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  damage_case TEXT NOT NULL,
  pi_tlight REAL,
  si_tlight REAL,
  pi_tpartial REAL,
  si_tpartial REAL,
  pi_tdeepest REAL,
  si_tdeepest REAL,
  ai REAL,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS numint_conclusion (
  id SERIAL PRIMARY KEY,
  ship_version_id INTEGER NOT NULL,
  subdivision_length REAL,
  required_index REAL,
  attained_index REAL,
  complies BOOLEAN NOT NULL,
  step_accuracy INTEGER,
  penetration_reference TEXT,
  FOREIGN KEY (ship_version_id) REFERENCES ship_version(id) ON DELETE CASCADE
);
ALTER TABLE opening
ADD COLUMN L REAL,
  ADD COLUMN B REAL,
  ADD COLUMN H REAL;
-------------------------------INDEXES----------------------------------
CREATE INDEX idx_ship_version_ship_id ON ship_version(ship_id);
CREATE INDEX idx_main_dim_ship_version_id ON main_dimensions(ship_version_id);
CREATE INDEX idx_compartment_ship_version_id ON compartment(ship_version_id);
CREATE INDEX idx_compartment_design_content_id ON compartment(design_content_id_number);
CREATE INDEX idx_subcompartment_compartment_id ON subcompartment(compartment_id);
CREATE INDEX idx_subcompartment_shape_ship_version_id ON subcompartment_shape(ship_version_id);
CREATE INDEX idx_frustum_point_subcompartment_shape_id ON frustum_point(subcompartment_shape_id);
CREATE INDEX idx_opening_ship_version_id ON opening(ship_version_id);
CREATE INDEX idx_opening_compartment_id ON opening(compartment_id);
CREATE INDEX idx_probdam_case_ship_version_id ON probdam_case(ship_version_id);
CREATE INDEX idx_probdam_total_ship_version_id ON probdam_total(ship_version_id);
CREATE INDEX idx_probdam_conclusion_ship_version_id ON probdam_conclusion(ship_version_id);
CREATE INDEX idx_trim_gm_ship_version_id ON trim_gm(ship_version_id);
CREATE INDEX idx_numint_case_ship_version_id ON numint_case(ship_version_id);
CREATE INDEX idx_numint_conclusion_ship_version_id ON numint_conclusion(ship_version_id);
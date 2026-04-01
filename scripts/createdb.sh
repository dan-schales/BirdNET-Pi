#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf
sqlite3 $HOME/BirdNET-Pi/scripts/birds.db << EOF
DROP TABLE IF EXISTS detections;
CREATE TABLE IF NOT EXISTS detections (
  Date DATE,
  Time TIME,
  Sci_Name VARCHAR(100) NOT NULL,
  Com_Name VARCHAR(100) NOT NULL,
  Confidence FLOAT,
  Lat FLOAT,
  Lon FLOAT,
  Cutoff FLOAT,
  Week INT,
  Sens FLOAT,
  Overlap FLOAT,
  File_Name VARCHAR(100) NOT NULL);
CREATE INDEX "detections_Com_Name" ON "detections" ("Com_Name");
CREATE INDEX "detections_Sci_Name" ON "detections" ("Sci_Name");
CREATE INDEX "detections_Date_Time" ON "detections" ("Date" DESC, "Time" DESC);
CREATE INDEX "detections_species_agg" ON "detections" ("Sci_Name", "Date", "Confidence", "Com_Name");
CREATE INDEX "detections_date_species" ON "detections" ("Date", "Sci_Name", "Com_Name", "Confidence", "Time");
EOF
chown $USER:$USER $HOME/BirdNET-Pi/scripts/birds.db
chmod g+w $HOME/BirdNET-Pi/scripts/birds.db

#This file manages the PostgreSQL connection

# psycopg2 is the library that lets Python talk to PostgreSQL
import psycopg2
import json
import logging
from config import DB_CONFIG

logger = logging.getLogger(__name__)
class DatabaseClient:


    def __init__(self):
        # self.connection will hold open database connection
        self.connection = None
        # Open the database connection
        self._connect()

    def _connect(self):
        '''
        Opens the PostgreSQL connection and stores it in self.connection
        '''
        try:
            # opens the connection to PostgreSQL.
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to PostgreSQL successfully")   

        except psycopg2.OperationalError as e:  # OperationalError means we could not reach the database

            logger.error(f"Could not connect to PostgreSQL: {e}")
            # self.connection stays None
            # The producer will continue but DB saves will be skipped

    def save_traffic_record(self, traffic_record, location_name):
        '''
        Saves one traffic record into the raw_events table
        '''
        if self.connection is None:
            logger.warning("No database connection : skipping save")
            return False

        sql = """
            INSERT INTO raw_events (
                request_time,
                requested_lat,
                requested_lon,
                location_name,
                frc,
                current_speed,
                free_flow_speed,
                current_travel_time,
                free_flow_travel_time,
                confidence,
                road_closure,
                raw_payload
            )
            VALUES (
                %(request_time)s,
                %(requested_lat)s,
                %(requested_lon)s,
                %(location_name)s,
                %(frc)s,
                %(current_speed)s,
                %(free_flow_speed)s,
                %(current_travel_time)s,
                %(free_flow_travel_time)s,
                %(confidence)s,
                %(road_closure)s,
                %(raw_payload)s
            )
        """

        data = {
            **traffic_record,
            "location_name": location_name,
            "raw_payload": json.dumps(traffic_record["raw_payload"]),
        }

        try:
            # cursor is the object we use to run SQL commands
            cursor = self.connection.cursor()
            # Execute the insert with our data
            cursor.execute(sql, data)
            # saves the change to the database
            self.connection.commit()
            cursor.close()
            logger.info(f"Saved to database: {location_name}")

            return True

        except Exception as e:
            logger.error(f"Failed to save {location_name} to database: {e}")
            # Rollback cancels the failed insert and resets the connection 
            self.connection.rollback()

            return False
    
    def save_weather_record(self, weather_record):
        """
        Saves one weather snapshot into the weather_events table.
        """
        if self.connection is None:
            logger.warning("No database connection skipping weather save")
            return False

        sql = """
            INSERT INTO weather_events (
                recorded_at,
                temperature,
                feels_like,
                humidity,
                weather_main,
                weather_desc,
                wind_speed,
                rain_mm,
                raw_payload
            )
            VALUES (
                %(recorded_at)s,
                %(temperature)s,
                %(feels_like)s,
                %(humidity)s,
                %(weather_main)s,
                %(weather_desc)s,
                %(wind_speed)s,
                %(rain_mm)s,
                %(raw_payload)s
            )
        """
        data = {
            **weather_record,
            "raw_payload": json.dumps(weather_record["raw_payload"]),
        }

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, data)
            self.connection.commit()
            cursor.close()
            logger.info("Weather record saved to database")
            return True

        except Exception as e:
            logger.error(f"Failed to save weather record: {e}")
            self.connection.rollback()
            return False

    def save_incident_records(self, incidents):
        """
        Saves a list of incident records to the traffic_incidents table.
        Called once per round with all incidents from the Cairo bounding box.
        """
        if self.connection is None:
            logger.warning("No database connection — skipping incidents save")
            return 0

        sql = """
            INSERT INTO traffic_incidents (
                fetched_at, incident_id, incident_type, icon_category,
                magnitude, description, road_from, road_to,
                road_numbers, delay_seconds, length_meters,
                lat, lon, start_time, end_time, raw_geometry
            ) VALUES (
                %(fetched_at)s, %(incident_id)s, %(incident_type)s, %(icon_category)s,
                %(magnitude)s, %(description)s, %(road_from)s, %(road_to)s,
                %(road_numbers)s, %(delay_seconds)s, %(length_meters)s,
                %(lat)s, %(lon)s, %(start_time)s, %(end_time)s, %(raw_geometry)s
            )
        """

        saved_count = 0
        for incident in incidents:
            try:
                data = {
                    **incident,
                    "raw_geometry": json.dumps(incident.get("raw_geometry", {})),
                }
                cursor = self.connection.cursor()
                cursor.execute(sql, data)
                self.connection.commit()
                cursor.close()
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save incident {incident.get('incident_id', '?')}: {e}")
                self.connection.rollback()

        if saved_count > 0:
            logger.info(f"Saved {saved_count}/{len(incidents)} incidents to database")
        return saved_count


    def is_connected(self):
        '''
        Checks if the database connection is still opened and reconnect if not to avoid missing data
        '''
        if self.connection is None:
            return False

        try:
            # SELECT 1 is a simple query that tests if the database connection is alive
            # Like a ping to see if the other side is still there
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True

        except Exception:
            # Any error here means the connection is dead
            return False

    def reconnect(self):
        '''
        Closes the old broken connection and opens a fresh one
        '''
        logger.warning("Database connection lost. Reconnecting..")
        # Try to close the old connection and ignore errors if it’s already dead.
        try:
            if self.connection is not None:
                self.connection.close()
        except Exception:
            pass

        # Reset to None before trying again
        self.connection = None
        # Open a fresh connection
        self._connect()
      
    def close(self):
        '''
        Closes the connection when the producer stops
        '''
        if self.connection is not None:
            self.connection.close()
            logger.info("Database connection closed.")

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

    def save_record(self, record, location_name):
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
            **record,
            "location_name": location_name,
            "raw_payload": json.dumps(record["raw_payload"]),
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

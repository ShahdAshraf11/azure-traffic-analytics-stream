# ============================================================
#  db_client.py
#  This file talks to the PostgreSQL database.
#
#  We wrote it as a CLASS because it needs to REMEMBER
#  the database connection between every save call.
#
#  Without a class, we would have to pass 'connection'
#  into every function — messy and repetitive.
#  With a class, we open the connection ONCE in __init__
#  and every method uses it automatically through 'self'.
#
#  HOW TO USE THIS FILE IN producer.py:
#
#    from db_client import DatabaseClient
#
#    db = DatabaseClient()        # opens connection once
#    db.save_record(record, name) # saves a record
#    db.is_connected()            # checks if still alive
#    db.close()                   # closes when done
# ============================================================


# --- Import the libraries we need ---------------------------

# psycopg2 is the library that lets Python talk to PostgreSQL
import psycopg2

# json lets us convert a Python dictionary to a JSON string
# We need this because the raw_payload column stores JSON
import json

# logging saves messages to our log file and terminal
import logging

# Import our database settings from config.py
# DB_CONFIG is a dictionary with host, port, dbname, user, password
from config import DB_CONFIG


# Create a logger for this file
# __name__ will be 'db_client' so log messages are labelled clearly
logger = logging.getLogger(__name__)


# ============================================================
#  CLASS: DatabaseClient
# ============================================================
# A class is a blueprint for creating objects.
# When you write:   db = DatabaseClient()
# Python creates an "instance" of this class called db.
# That instance has its own connection stored inside it.
#
# Every method (function inside a class) has 'self' as the
# first parameter. 'self' means "this specific instance."
# So self.connection means "the connection belonging to THIS db object."
# ============================================================

class DatabaseClient:


    # --------------------------------------------------------
    #  __init__  (the constructor)
    # --------------------------------------------------------
    # __init__ is a special method that runs AUTOMATICALLY
    # the moment you create an instance:
    #   db = DatabaseClient()   <- __init__ runs here
    #
    # Its job: open the database connection and store it
    # in self.connection so every other method can use it.
    # --------------------------------------------------------

    def __init__(self):

        # self.connection will hold our open database connection.
        # We set it to None first as a safe starting value.
        # If the connection attempt fails it stays None and other
        # methods will check for None before trying to use it.
        self.connection = None

        # Now actually open the connection by calling our
        # private _connect() helper method defined below.
        # The underscore _ at the start of the name means
        # "this is private — only used inside this class."
        self._connect()


    # --------------------------------------------------------
    #  _connect  (private helper)
    # --------------------------------------------------------
    # Opens the PostgreSQL connection and stores it in self.connection.
    # We made this a separate method so we can REUSE it when
    # reconnecting after a dropped connection — just call
    # self._connect() again without repeating all this code.
    # --------------------------------------------------------

    def _connect(self):

        try:
            # psycopg2.connect() opens the connection to PostgreSQL.
            # **DB_CONFIG "unpacks" the dictionary.
            # It is the same as writing:
            #   psycopg2.connect(host='localhost', port=5432, ...)
            # The ** is just a shorter way to pass many arguments at once.
            self.connection = psycopg2.connect(**DB_CONFIG)

            logger.info('Connected to PostgreSQL successfully.')

        except psycopg2.OperationalError as e:
            # OperationalError means we could not reach the database.
            # Common reasons:
            #   - Docker is not running
            #   - Wrong password or database name in .env
            #   - TimescaleDB container has not started yet
            logger.error(f'Could not connect to PostgreSQL: {e}')
            logger.error('Is Docker running? Try: docker compose up -d')

            # self.connection stays None
            # The producer will continue but DB saves will be skipped


    # --------------------------------------------------------
    #  save_record
    # --------------------------------------------------------
    # Saves ONE traffic record into the raw_events table.
    #
    # Parameters:
    #   record        = dictionary of traffic data from api_client.py
    #   location_name = the road name e.g. "Tahrir Square"
    #
    # Returns True if saved successfully, False if it failed.
    # --------------------------------------------------------

    def save_record(self, record, location_name):

        # If connection is None we never connected successfully.
        # Skip the save and return False immediately.
        if self.connection is None:
            logger.warning('No database connection — skipping save.')
            return False

        # This is the SQL INSERT statement.
        # It tells PostgreSQL to insert a new row into raw_events.
        # The %(name)s parts are PLACEHOLDERS — psycopg2 replaces them
        # with real values safely. This prevents SQL injection attacks.
        # Never build SQL by joining strings like:
        #   "INSERT INTO ... VALUES (" + speed + ")"  <- DANGEROUS
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

        # Build the data dictionary that fills the %(name)s placeholders.
        # {**record} copies all key-value pairs from record into a new dict.
        # We then add location_name and convert raw_payload to a JSON string.
        # Why JSON string? PostgreSQL JSONB column needs it as text first —
        # psycopg2 sends the string and PostgreSQL stores it as JSONB.
        data = {
            **record,
            'location_name': location_name,
            'raw_payload'  : json.dumps(record['raw_payload']),
        }

        try:
            # A cursor is the object we use to run SQL commands.
            # Think of it like a pen — create it, write with it, close it.
            cursor = self.connection.cursor()

            # Execute the INSERT with our data dictionary.
            # psycopg2 safely fills in the %(name)s placeholders.
            cursor.execute(sql, data)

            # commit() saves the change permanently to the database.
            # Without commit() the INSERT is temporary and disappears
            # when the connection closes. Like pressing Save in Word.
            self.connection.commit()

            # Close the cursor — we are done with this write
            cursor.close()

            logger.info(f'Saved to database: {location_name}')
            return True

        except Exception as e:
            logger.error(f'Failed to save {location_name} to database: {e}')

            # rollback() cancels the failed INSERT and resets the connection
            # to a clean usable state. Without this, the connection gets
            # stuck in a broken transaction and all future inserts fail too.
            self.connection.rollback()

            return False


    # --------------------------------------------------------
    #  is_connected
    # --------------------------------------------------------
    # Checks if the database connection is still alive.
    #
    # Why do we need this?
    # The producer runs for hours. The connection can drop during
    # that time — Docker restarts, PostgreSQL timeout, network blip.
    # We call this after each round. If it returns False we reconnect
    # before the next round so we never miss saving data.
    #
    # Returns True if alive, False if dead.
    # --------------------------------------------------------

    def is_connected(self):

        # If connection was never opened it is definitely not alive
        if self.connection is None:
            return False

        try:
            # SELECT 1 is the simplest SQL command possible.
            # It does not read any real data — it just checks
            # if the connection can execute anything at all.
            # Like a ping to see if the other side is still there.
            cursor = self.connection.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            return True

        except Exception:
            # Any error here means the connection is dead
            return False


    # --------------------------------------------------------
    #  reconnect
    # --------------------------------------------------------
    # Closes the old broken connection and opens a fresh one.
    # Called in producer.py when is_connected() returns False.
    # --------------------------------------------------------

    def reconnect(self):

        logger.warning('Database connection lost. Reconnecting...')

        # Try to close the old broken connection.
        # Wrapped in try/except because calling close() on a
        # dead connection might raise an error — we just ignore it.
        try:
            if self.connection is not None:
                self.connection.close()
        except Exception:
            pass

        # Reset to None before trying again
        self.connection = None

        # Open a fresh connection
        self._connect()


    # --------------------------------------------------------
    #  close
    # --------------------------------------------------------
    # Closes the connection cleanly when the producer stops.
    # Called in the finally block of producer.py.
    # --------------------------------------------------------

    def close(self):

        if self.connection is not None:
            self.connection.close()
            logger.info('Database connection closed.')

# Traffic Analytics Streaming Project — Setup Guide

This guide explains how to set up the development environment required to run the **Traffic Analytics Streaming Pipeline**.

The system collects traffic data from the **TomTom API**, streams it through **Kafka**, and stores it in **TimescaleDB** for analysis and visualisation..

-----------------------------------------------------------------------------------

# Project Architecture

TomTom API

    ↓
Kafka Producer

    ↓
Kafka Topic
    ↓

Kafka Consumer
    ↓

TimescaleDB (PostgreSQL extension for time-series data)
    ↓

Power BI / Alerts / Airflow


------------------------------------------------------------------------------------

# Prerequisites

Before running the project, install the following software:

* **Git** – https://git-scm.com/downloads
* **Docker Desktop** – https://www.docker.com/products/docker-desktop/
* **WSL2 (Windows Subsystem for Linux)**
* **Ubuntu 22.04 for WSL** – install from Microsoft Store
* **Python 3.10+**

Recommended tools:

* **VS Code** – https://code.visualstudio.com/
* **Docker Desktop UI**

-----------------------------------------------------------------------------------

# Step 1 — Clone the Repository

Clone the project from GitHub:

    git clone https://github.com/ShahdAshraf11/azure-traffic-analytics-stream.git
    cd traffic_analytics_stream_project

If you already created the project locally, initialize Git:

    git init


-----------------------------------------------------------------------------------

# Step 2 — Verify WSL Installation

Open **PowerShell** and run:

    wsl -l -v


Expected output:

    NAME            STATE           VERSION
    Ubuntu-22.04    Stopped         2


Important:

* **VERSION must be 2**

If it is not version 2:

    wsl --set-version Ubuntu-22.04 2


--------------------------------------------------------------------------------------

# Step 3 — Verify Docker Installation

Check Docker is installed correctly:

    docker --version

Check Docker engine status:

    docker info

Expected output must contain:

    OSType: linux

If you see:

   - OSType: windows --> You must switch Docker to Linux containers.
                                    ↓

                        To Switch Docker to Linux Containers:

                        1. Look at the **bottom-right system tray**
                        2. Find the **Docker whale icon**
                        3. Right-click the icon.
                        4. Select:

                            **Switch to Linux containers** and Docker will restart automatically.



# Step 4 — Enable WSL Integration

Open Docker Desktop.
    ↓

Go to: Settings → Resources → WSL Integration
    ↓

Enable the following distribution: Ubuntu-22.04
    ↓

Click Apply & Restart

-------------------------------------------------------------------------------

# Step 5 — Create Environment Variables

Create file:

    - touch .env

    -Edit `.env` and fill your credentials.

    Code:

    ```
    TOMTOM_API_KEY=your_api_key_here → Get one from (https://developer.tomtom.com) sign up and copy the key.
    TOMTOM_API_URL=https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json
    TOMTOM_REFRESH_INTERVAL=300 → 300 seconds = 5 minutes (This respects the **TomTomfree API limit (2500 calls/day)**)

    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_DB=traffic_db
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=postgres

    KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    KAFKA_TOPIC=traffic-data


    ```
----------------------------------------------------------------------

# Step 6 — Set Up Python Environment

- python -m venv venv
- venv\Scripts\activate
- pip install -r requirements.txt

**Important**:

    Every time you open a new terminal to work on this project, activate the environment first.

    Otherwise you may get:

    ```
    ModuleNotFoundError
    ```


------------------------------------------------------------------------------------------
# Step 7 — Start the Infrastructure

Navigate to the infrastructure folder:

    - cd infrastructure

    -Start all containers:

        docker compose up -d


Docker will download and start the following services:

* Zookeeper
* Kafka
* TimescaleDB (PostgreSQL)
--------------------------------------------------------------------------------
# Step 8 — Verify Containers Are Running

Run:
    - docker ps

    Expected output should contain containers similar to:

        zookeeper
        kafka
        postgres

        Example:
        CONTAINER ID     IMAGE                               STATUS
        xxx         confluentinc/cp-zookeeper                 Up
        xxx         confluentinc/cp-kafka                     Up
        xxx         timescale/timescaledb                     Up

----------------------------------------------------------------------------------
# Step 9 — Verify PostgreSQL Database

Connect to PostgreSQL using:

    - docker exec -it infrastructure-postgres-1 psql -U postgres -d traffic_db


Check tables:

    - \dt


    You should see:
        ```
        raw_events
        ```

-------------------------------------------------------------------
# Step 10 — Verify Kafka and PostgreSQL with Test Scripts

**Make sure the virtual environment is activated and you are in the project root directory**

## Test PostgreSQL:
    Open **two terminal tabs**.

    Terminal 1: python test_insert.py

    Terminal 2: python test_postgres.py
``
    **Expected Output**

        test_insert.py:

            Inserted test row with TomTom-like data

        test_postgres.py:

            Number of rows in raw_events: 1

Test Kafka:
    Start the Consumer

        Open a terminal and run: python test_kafka_consumer.py

    Output : Waiting for messages..

    Send a Test Message

        Open another terminal and run:

            python test_kafka_producer.py

        Example output:

            Message sent to test-topic

    Expected Result
        The consumer should receive the message: Received: {'message': 'hello from producer'}
# Step 11 — Stop the Infrastructure

To stop containers:

    docker compose down

To stop and remove volumes:

    docker compose down -v

Or Do this from Docker Desktop

# Project Folder Structure

```
traffic_analytics_stream_project/
│
├── .github/                  # GitHub workflows (CI/CD) – future use
├── infrastructure/            # Docker and infrastructure files
│   └── docker-compose.yml
│
├── sql/                       # Database schema definitions
│   └── schema.sql
│
├── data_generator/             # Producer script (calls TomTom API)
│   └── (producer.py, etc.)
│
├── stream_processor/           # Kafka consumer script
│   └── (consumer.py, etc.)
│
├── alerts/                     # Alerting script
│   └── (alert.py, etc.)
│
├── notebooks/                  # for EDA
│
├── models/                      # Trained ML models (.joblib files)
│
├── dags/                        # Airflow DAGs (batch orchestration)
│
├── logs/                        # Log files from all components
│
├── .env                         # Template for environment variables
├── .gitignore                   # Git ignore rules
├── .pre-commit-config.yaml      # Pre‑commit hooks configuration
├── requirements.txt             # Python dependencies
├── README.md                    # Project overview (short)
└── SETUP.md                     # This setup guide

```

------------------------------------------------------------------------------------------------

# Common Problems

## Docker Engine Not Running

Error example:

    "error during connect: dockerDesktopWindowsEngine"

Solution:

    Start **Docker Desktop** and wait until it says:

        - Docker Engine is running


## Port Already in Use

Example error:

    port 5432 already allocated

Solution:
    Find the process:

    - netstat -ano | findstr 5432
    - Stop the conflicting service or change the port in `docker-compose.yml` .

---------------------------------------------------------------------------------------------

# Development Workflow

Typical workflow :

    open Docker desktop first
            ↓
    activate the environment
            ↓
    Start infrastructure:
        - cd infrastructure
        - docker compose up -d

            ↓
    Run producer script:

        python data_generator/tomtom_producer.py

            ↓
    Run consumer script:

        python stream_processor/kafka_consumer.py


    Check database data.


# Useful Commands

List running containers:

    docker ps

View container logs:

    docker logs kafka

Stop containers:

    docker compose down


Restart containers:

    docker compose restart


# Notes for Team Members

* Do **not commit `.env` files**
* Do **not commit generated data**
* Always pull latest changes before starting work

    command : git pull

* Run pre-commit install after cloning to enable automatic code formatting and linting.--> Ignore it for now

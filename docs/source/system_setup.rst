System Setup
============



Prerequisite
------------

Before using the Structural Color Printing (SCP) system, users should have a working knowledge of the following technologies and tools:

- **Docker**: A platform for developing, running, and managing containerized applications. Learn more at the `official Docker documentation <https://docs.docker.com/get-started/>`_.

  To use Docker, ensure the Docker daemon is installed and running on your platform:

  - `Docker Desktop for Windows <https://docs.docker.com/desktop/install/windows-install/>`_
  - `Docker Desktop for macOS <https://docs.docker.com/desktop/install/mac-install/>`_
  - `Docker Engine on Linux <https://docs.docker.com/engine/install/>`_

  Common Docker commands:

  .. code-block:: bash

     # Build a Docker image from a Dockerfile
     docker build -t my-image-name .

     # List all Docker images
     docker images

     # Run a container from an image
     docker run -p 8000:8000 my-image-name

     # Remove a stopped container
     docker rm <container_id>

     # Remove an image
     docker rmi my-image-name

- **Docker Compose**: A tool for defining and managing multi-container Docker applications using a `docker-compose.yml` file. Learn more at the `Docker Compose documentation <https://docs.docker.com/compose/>`_.

  Common Docker Compose commands:

  .. code-block:: bash

     # Start services defined in docker-compose.yml
     docker-compose up

     # Start in detached mode (background)
     docker-compose up -d

     # Stop all running services
     docker-compose down

     # Stop and remove volumes (use with caution)
     docker-compose down -v

     # Rebuild containers if changes were made
     docker-compose up --build

     # View logs from all services
     docker-compose logs -f

- **MongoDB**: A NoSQL document-oriented database for storing structured and semi-structured data. Introduction available at the `MongoDB manual <https://www.mongodb.com/docs/manual/introduction/>`_.

- **RabbitMQ**: A message broker that facilitates communication between services using messaging queues. Visit the `RabbitMQ Getting Started Guide <https://www.rabbitmq.com/getstarted.html>`_.

Familiarity with these tools is essential for deploying and managing the SCP system and its supporting infrastructure.


Running the System
----------------------
The Structural Color Printing (SCP) system has been pre-configured and deployed on a macOS laptop located in the Polyprint Lab. The adaptor component is running on a separate Dell laptop, which is physically connected to the 3D printer in the same lab.

Follow the steps below to set up and run the SCP system on a new machine or reinitialize it:

1. **Clone the SCP Code Repository**

   First, clone the SCP source code from the GitHub repository:

   .. code-block:: bash

      git clone https://github.com/your-org/scp.git
      cd scp

2. **Navigate to the Docker Directory and Start Services**

   Use Docker Compose to start the required services:

   .. code-block:: bash

      cd docker
      docker-compose up -d

3. **Create an Admin User in Clowder**

   After Clowder is running, create an admin user using the following command:

   .. code-block:: bash

      docker run --rm -it \
        --network clowder_clowder \
        -e "ADMIN=true" \
        -e "PASSWORD=testing0909" \
        -e "EMAIL_ADDRESS=admin@test.com" \
        -e "MONGO_URI=mongodb://mongo:27017/clowder" \
        clowder/init

4. **Restart Docker Compose**

   Restart the services to ensure that the new configuration takes effect:

   .. code-block:: bash

      docker-compose down
      docker-compose up -d

5. **Configure the Adaptor**

   First, you need to install polychemprint3.
   Then, you need to identify the IP address of the host machine where RabbitMQ is running. This IP must be accessible from the machine connected to the 3D printer.

   - On Linux/macOS, run:

     .. code-block:: bash


Q & A
----------------------
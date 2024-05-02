# RemCord Token Exchange Server - Now in Rust!

This repository has been completely revamped to host a Rust-based server, focusing on safety, performance, and scalability. The server now utilizes Rust's powerful type system and ownership model to ensure high levels of security and efficiency. Additionally, we have integrated load-balancing capabilities to handle high volumes of requests seamlessly.

## Features

- **Rust Implementation**: The server is fully implemented in Rust, offering enhanced safety and performance.
- **Safety and Security**: Leveraging Rust's ownership model and type checking to improve security protocols.
- **Load Balancing**: Integrated load-balancing functionality to efficiently manage high request volumes.
- **Docker and Kubernetes Support**: Includes configurations for deploying the server using Docker and Kubernetes, ensuring easy scalability and management.

## Getting Started

To get started with deploying and maintaining the Rust server, follow the instructions below:

### Building the Server

1. Ensure you have Rust and Cargo installed on your system.
2. Clone the repository and navigate to the project directory.
3. Build the project using Cargo:
   ```
   cargo build --release
   ```

### Deploying with Docker

1. Build the Docker container:
   ```
   docker build -t remcord-exchange-server .
   ```
2. Run the container:
   ```
   docker run -d -p 8000:8000 remcord-exchange-server
   ```

### Deploying with Kubernetes

1. Apply the Kubernetes deployment and service configurations:
   ```
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```
2. Monitor the deployment status:
   ```
   kubectl get deployments
   kubectl get services
   ```

For more detailed instructions and configurations, refer to the `k8s` directory.

## License

```txt
MIT License © Nathan Solis
```

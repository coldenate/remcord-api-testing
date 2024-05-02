# Use the official Rust image as a builder stage
FROM rust:1.62 as builder

# Create a new empty shell project
RUN USER=root cargo new --bin remcord-exchange-server
WORKDIR /remcord-exchange-server

# Copy our manifests
COPY ./Cargo.lock ./Cargo.lock
COPY ./Cargo.toml ./Cargo.toml

# Build only the dependencies to cache them
RUN cargo build --release
RUN rm src/*.rs

# Copy the source and build the application
COPY ./src ./src
RUN rm ./target/release/deps/remcord_exchange_server*
RUN cargo build --release

# Use the official Debian slim image for the runtime stage
FROM debian:buster-slim

# Copy the binary from the builder stage
COPY --from=builder /remcord-exchange-server/target/release/remcord-exchange-server .

# Set the binary as the entrypoint of the container
ENTRYPOINT ["./remcord-exchange-server"]
